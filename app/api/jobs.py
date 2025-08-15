from fastapi import APIRouter, File, UploadFile, HTTPException, status, Request, Depends
from celery.result import AsyncResult
import uuid
import time
from datetime import datetime

from workers.celery_app import celery_app
from app.schemas.job import JobCreateResponse, JobStatusResponse
from app.core.dependencies import get_user_from_api_key
from app.services.user_service import UserService
from app.database import get_db
from sqlalchemy.orm import Session
from app.models.user import User, APIKey
from typing import Optional, Tuple

router = APIRouter()

@router.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: Request, 
    file: UploadFile = File(...),
    auth_data: Tuple[User, Optional[APIKey]] = Depends(get_user_from_api_key),
    db: Session = Depends(get_db)
):
    """Create a new document processing job (requires authentication)"""
    user, api_key = auth_data
    job_id = uuid.uuid4()
    user_service = UserService(db)
    file_content = b""
    
    try:
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)  # Convert to MB
        
        # Check if user can process this document
        can_process, message = user_service.can_process_document(user, file_size_mb)
        if not can_process:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message
            )
        
        # Log the usage attempt
        usage_log = user_service.log_usage(
            user_id=user.id,  # type: ignore
            api_key_id=api_key.id if api_key else None,  # type: ignore
            job_id=str(job_id),
            filename=file.filename or "unknown",
            file_size_bytes=len(file_content),
            success=False  # Will be updated when job completes
        )
        
        # Add user context to task
        task_metadata = {
            'user_id': user.id,  # type: ignore
            'plan_type': user.plan_type.value,
            'usage_log_id': usage_log.id
        }
        
        task = celery_app.send_task(
            'workers.tasks.process_document', 
            args=[file_content, file.filename, task_metadata], 
            task_id=str(job_id)
        )
        
    except Exception as e:
        # Log failed usage
        user_service.log_usage(
            user_id=user.id,  # type: ignore
            api_key_id=api_key.id if api_key else None,  # type: ignore
            job_id=str(job_id),
            filename=file.filename or "unknown",
            file_size_bytes=len(file_content) if file_content else 0,
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")

    status_url = str(request.url_for("get_job_status", job_id=str(job_id)))
    return {"job_id": str(job_id), "status": "queued", "status_url": status_url}

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    auth_data: Tuple[User, Optional[APIKey]] = Depends(get_user_from_api_key),
    db: Session = Depends(get_db)
):
    """Get job status (requires authentication)"""
    user, api_key = auth_data
    
    # Validate job_id is a valid UUID
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    task_result = AsyncResult(job_id, app=celery_app)
    
    # Update API key last used timestamp
    if api_key:
        api_key.last_used_at = datetime.utcnow()  # type: ignore
        db.commit()
    
    response_data = {
        "job_id": job_id,  # Return as string instead of UUID
        "status": task_result.status,
    }

    if task_result.status == "PROGRESS":
        response_data.update(task_result.info)
    elif task_result.status == "SUCCESS":
        response_data.update(task_result.result)
    elif task_result.status == "FAILURE":
        response_data["result"] = str(task_result.info)

    return response_data
