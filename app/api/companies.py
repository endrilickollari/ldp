from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User, Company, UserType
from app.schemas.user import Company as CompanySchema, User as UserSchema
from app.services.user_service import UserService
from typing import List

router = APIRouter()

@router.get("/users", response_model=List[UserSchema])
def get_company_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all users in the current user's company (enterprise users only)"""
    if current_user.user_type != UserType.ENTERPRISE or current_user.company_id is None:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only enterprise users can view company users"
        )
    
    user_service = UserService(db)
    users = user_service.get_company_users(current_user.company_id)  # type: ignore
    return users

@router.get("/{company_id}", response_model=CompanySchema)
def get_company(
    company_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get company information (enterprise users only)"""
    if current_user.user_type != UserType.ENTERPRISE:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only enterprise users can view company information"
        )
    
    # Ensure user can only access their own company
    if current_user.company_id != company_id:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own company information"
        )
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    return company
