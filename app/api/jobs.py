from fastapi import APIRouter, File, UploadFile, HTTPException, status, Request
from celery.result import AsyncResult
import uuid

from workers.celery_app import celery_app
from app.schemas.job import JobCreateResponse, JobStatusResponse

router = APIRouter()

@router.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(request: Request, file: UploadFile = File(...)):
    job_id = uuid.uuid4()
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    task = celery_app.send_task('workers.tasks.process_document', 
                               args=[file_content, file.filename], 
                               task_id=str(job_id))

    status_url = str(request.url_for("get_job_status", job_id=str(job_id)))
    return {"job_id": job_id, "status": "queued", "status_url": status_url}

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    task_result = AsyncResult(job_id, app=celery_app)
    
    response_data = {
        "job_id": uuid.UUID(job_id),
        "status": task_result.status,
    }

    if task_result.status == "PROGRESS":
        response_data.update(task_result.info)
    elif task_result.status == "SUCCESS":
        response_data.update(task_result.result)
    elif task_result.status == "FAILURE":
        response_data["result"] = str(task_result.info)

    return response_data
