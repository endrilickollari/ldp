from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User, License
from app.schemas.user import (
    LicenseCreate, 
    LicensePurchase, 
    License as LicenseSchema,
    LicenseStatusResponse
)
from app.services.deployment_license_service import DeploymentAwareLicenseService
from app.core.config import settings, DeploymentMode

router = APIRouter()

@router.get("/pricing", response_model=Dict[str, Any])
def get_license_pricing():
    """Get pricing for all available license types and durations (deployment-aware)"""
    pricing = DeploymentAwareLicenseService.get_license_pricing()
    
    deployment_info = {
        "deployment_mode": settings.DEPLOYMENT_MODE.value,
        "is_saas": settings.DEPLOYMENT_MODE == DeploymentMode.SAAS,
        "is_self_hosted": settings.DEPLOYMENT_MODE == DeploymentMode.SELF_HOSTED
    }
    
    # Different feature sets based on deployment mode
    if settings.DEPLOYMENT_MODE == DeploymentMode.SAAS:
        features_by_plan = {
            "premium": [
                "500 documents per month",
                "100MB max file size",
                "Priority processing queue",
                "Email support",
                "All document types supported",
                "Advanced AI analysis",
                "API access",
                "Cloud-hosted - no setup required"
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
                "Dedicated account manager",
                "Priority cloud resources"
            ]
        }
        duration_benefits = {
            "monthly": "Pay monthly, cancel anytime",
            "six_months": "Save 16% compared to monthly",
            "yearly": "Save 33% compared to monthly"
        }
    else:
        features_by_plan = {
            "premium": [
                "Unlimited documents per month",
                "500MB max file size",
                "Full control over your data",
                "On-premises deployment",
                "Email support",
                "All document types supported",
                "Advanced AI analysis",
                "Full API access",
                "No data leaves your infrastructure"
            ],
            "extra_premium": [
                "Unlimited documents per month", 
                "2GB max file size",
                "Full control over your data",
                "On-premises deployment",
                "Priority support with SLA",
                "All document types supported",
                "Advanced AI analysis with custom models",
                "Full API access with webhooks",
                "White-label options",
                "Custom integrations support",
                "Source code access (Enterprise+)"
            ]
        }
        duration_benefits = {
            "monthly": "Monthly license validation",
            "six_months": "Save 16% - 6 month validation cycle", 
            "yearly": "Save 33% - yearly validation cycle",
            "lifetime": "One-time payment - perpetual license"
        }
    
    return {
        "pricing": pricing,
        "currency": "USD",
        "deployment_info": deployment_info,
        "features_by_plan": features_by_plan,
        "duration_benefits": duration_benefits,
        "notes": {
            "saas": "SaaS pricing - subscription-based, cloud-hosted",
            "self_hosted": "Self-hosted pricing - higher cost but full control and unlimited usage"
        } if settings.DEPLOYMENT_MODE == DeploymentMode.SELF_HOSTED else {
            "saas": "Cloud-hosted service - no setup required, automatic updates"
        }
    }

@router.get("/deployment-info")
def get_deployment_info(db: Session = Depends(get_db)):
    """Get deployment mode and configuration information"""
    license_service = DeploymentAwareLicenseService(db)
    return license_service.get_deployment_info()

@router.post("/purchase", response_model=LicenseSchema, status_code=status.HTTP_201_CREATED)
async def purchase_license(
    license_data: LicensePurchase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Purchase a new license (deployment-aware)"""
    
    license_service = DeploymentAwareLicenseService(db)
    
    # Additional validation for self-hosted mode
    if license_service.is_self_hosted_mode():
        if not settings.INSTANCE_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Instance not properly configured. Please contact administrator."
            )
    
    # Check if user already has an active license of the same or higher tier
    current_license_status = await license_service.check_license_validity(current_user)
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
    """Activate a license after payment confirmation (admin/webhook endpoint)"""
    
    license_obj = db.query(License).filter(
        License.license_key == license_key,
        License.status == "pending"
    ).first()
    
    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found or already activated"
        )
    
    if payment_confirmed:
        from datetime import datetime
        setattr(license_obj, "status", "active")
        setattr(license_obj, "activated_at", datetime.utcnow())
        
        # Update user's plan type
        user = db.query(User).filter(User.id == license_obj.user_id).first()
        if user:
            setattr(user, "plan_type", license_obj.plan_type)
        
        db.commit()
        db.refresh(license_obj)
    
    return license_obj

@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's license status (deployment-aware)"""
    
    license_service = DeploymentAwareLicenseService(db)
    return await license_service.check_license_validity(current_user)

@router.get("/my-licenses", response_model=List[LicenseSchema])
def get_my_licenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all licenses for the current user"""
    
    return db.query(License).filter(
        License.user_id == current_user.id
    ).order_by(License.created_at.desc()).all()

@router.get("/validate/{license_key}")
async def validate_license_key(
    license_key: str,
    instance_id: Optional[str] = None,
    instance_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Validate a license key - used by self-hosted instances to validate with central server"""
    
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
    
    # Log the validation request (for analytics/monitoring)
    validation_info = {
        "instance_id": instance_id,
        "instance_name": instance_name,
        "validated_at": datetime.utcnow().isoformat(),
        "user_id": license_obj.user_id
    }
    
    return {
        "valid": True,
        "plan_type": license_obj.plan_type,
        "duration": license_obj.duration,
        "expires_at": getattr(license_obj, "expires_at").isoformat() if getattr(license_obj, "expires_at") else None,
        "user_id": license_obj.user_id,
        "validation_info": validation_info
    }

@router.post("/suspend/{license_key}", response_model=LicenseSchema)
def suspend_license(
    license_key: str,
    reason: str = "Administrative suspension",
    db: Session = Depends(get_db)
):
    """Suspend a license (admin endpoint)"""
    
    license_obj = db.query(License).filter(
        License.license_key == license_key,
        License.status == "active"
    ).first()
    
    if not license_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active license not found"
        )
    
    from datetime import datetime
    setattr(license_obj, "status", "suspended")
    setattr(license_obj, "suspended_at", datetime.utcnow())
    
    if reason:
        import json
        extra_data_str = getattr(license_obj, "extra_data") or "{}"
        extra_data = json.loads(extra_data_str)
        extra_data["suspension_reason"] = reason
        extra_data["suspended_at"] = datetime.utcnow().isoformat()
        setattr(license_obj, "extra_data", json.dumps(extra_data))
    
    db.commit()
    db.refresh(license_obj)
    
    return license_obj
