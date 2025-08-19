from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User, License
from app.schemas.user import (
    LicenseCreate, 
    LicensePurchase, 
    License as LicenseSchema,
    LicenseStatusResponse
)
from app.services.license_service import LicenseService

router = APIRouter()

@router.get("/pricing", response_model=Dict[str, Any])
def get_license_pricing():
    """Get pricing for all available license types and durations"""
    pricing = LicenseService.get_license_pricing()
    
    return {
        "pricing": pricing,
        "currency": "USD",
        "features_by_plan": {
            "premium": [
                "500 documents per month",
                "100MB max file size",
                "Priority processing queue",
                "Email support",
                "All document types supported",
                "Advanced AI analysis",
                "API access"
            ],
            "extra_premium": [
                "2000 documents per month", 
                "500MB max file size",
                "Highest priority processing",
                "24/7 priority support",
                "All document types supported",
                "Advanced AI analysis",
                "Full API access",
                "Custom integrations support",
                "Dedicated account manager"
            ]
        },
        "duration_benefits": {
            "monthly": "Pay monthly, cancel anytime",
            "six_months": "Save 16% compared to monthly",
            "yearly": "Save 33% compared to monthly", 
            "lifetime": "One-time payment, use forever"
        }
    }

@router.post("/purchase", response_model=LicenseSchema, status_code=status.HTTP_201_CREATED)
def purchase_license(
    license_data: LicensePurchase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Purchase a new license (creates pending license awaiting payment confirmation)"""
    
    license_service = LicenseService(db)
    
    # Check if user already has an active license of the same or higher tier
    current_license_status = license_service.check_license_validity(current_user)
    if current_license_status.has_valid_license:
        active_license = current_license_status.current_license
        if active_license and active_license.plan_type == license_data.plan_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have an active {license_data.plan_type.value} license"
            )
    
    try:
        new_license = license_service.create_license(current_user, license_data)
        return new_license
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create license: {str(e)}"
        )

@router.post("/activate/{license_key}", response_model=LicenseSchema)
def activate_license(
    license_key: str,
    payment_confirmed: bool = True,
    db: Session = Depends(get_db)
):
    """Activate a license after payment confirmation (admin endpoint)"""
    
    license_service = LicenseService(db)
    activated_license = license_service.activate_license(license_key, payment_confirmed)
    
    if not activated_license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found or already activated"
        )
    
    return activated_license

@router.get("/status", response_model=LicenseStatusResponse)
def get_license_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's license status"""
    
    license_service = LicenseService(db)
    return license_service.check_license_validity(current_user)

@router.get("/my-licenses", response_model=List[LicenseSchema])
def get_my_licenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all licenses for the current user"""
    
    license_service = LicenseService(db)
    return license_service.get_user_licenses(getattr(current_user, "id"))

@router.post("/suspend/{license_key}", response_model=LicenseSchema)
def suspend_license(
    license_key: str,
    reason: str = "Administrative suspension",
    db: Session = Depends(get_db)
):
    """Suspend a license (admin endpoint)"""
    
    license_service = LicenseService(db)
    suspended_license = license_service.suspend_license(license_key, reason)
    
    if not suspended_license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active license not found"
        )
    
    return suspended_license

@router.get("/validate/{license_key}")
def validate_license_key(
    license_key: str,
    db: Session = Depends(get_db)
):
    """Validate a license key (public endpoint for checking validity)"""
    
    license_service = LicenseService(db)
    license_obj = db.query(License).filter(License.license_key == license_key).first()
    
    if not license_obj:
        return {"valid": False, "reason": "License key not found"}
    
    if getattr(license_obj, "status") != "active":
        return {
            "valid": False, 
            "reason": f"License is {getattr(license_obj, 'status')}",
            "status": getattr(license_obj, "status")
        }
    
    # Check expiration
    from datetime import datetime
    expires_at = getattr(license_obj, "expires_at")
    if expires_at and expires_at < datetime.utcnow():
        return {
            "valid": False,
            "reason": "License has expired",
            "expired_at": expires_at.isoformat()
        }
    
    return {
        "valid": True,
        "plan_type": license_obj.plan_type,
        "expires_at": getattr(license_obj, "expires_at").isoformat() if getattr(license_obj, "expires_at") else None,
        "user_id": license_obj.user_id
    }
