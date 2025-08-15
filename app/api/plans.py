from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User, PlanType
from app.schemas.user import UsageStats
from app.services.user_service import UserService
from typing import Dict, Any

router = APIRouter()

@router.get("/plans", response_model=Dict[str, Any])
def get_available_plans():
    """Get all available plans with their features and pricing"""
    return {
        "free": {
            "name": "Free Plan",
            "monthly_documents": 10,
            "max_file_size_mb": 5.0,
            "priority_processing": False,
            "support_level": "Community",
            "price_usd": 0.0,
            "tokens_per_month": 50000,
            "features": [
                "10 documents per month",
                "5MB max file size",
                "Community support",
                "Standard processing speed",
                "Basic document types (PDF, Excel, Images)"
            ]
        },
        "premium": {
            "name": "Premium Plan", 
            "monthly_documents": 100,
            "max_file_size_mb": 25.0,
            "priority_processing": True,
            "support_level": "Email Support",
            "price_usd": 29.99,
            "tokens_per_month": 500000,
            "features": [
                "100 documents per month",
                "25MB max file size", 
                "Priority processing queue",
                "Email support",
                "All document types supported",
                "Advanced AI analysis",
                "API access"
            ]
        },
        "extra_premium": {
            "name": "Extra Premium Plan",
            "monthly_documents": 500,
            "max_file_size_mb": 100.0,
            "priority_processing": True,
            "support_level": "Priority Support + Phone",
            "price_usd": 99.99,
            "tokens_per_month": 2000000,
            "features": [
                "500 documents per month",
                "100MB max file size",
                "Highest priority processing",
                "Phone + Email support", 
                "All document types supported",
                "Advanced AI analysis",
                "Full API access",
                "Custom integrations support",
                "Dedicated account manager"
            ]
        }
    }

@router.get("/usage", response_model=UsageStats)
def get_usage_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's usage statistics"""
    user_service = UserService(db)
    return user_service.get_usage_stats(current_user)

@router.get("/current-plan")
def get_current_plan(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's plan details"""
    user_service = UserService(db)
    plan_limits = user_service.get_plan_limits(current_user.plan_type)  # type: ignore
    usage_stats = user_service.get_usage_stats(current_user)
    
    return {
        "current_plan": current_user.plan_type.value,
        "plan_details": plan_limits,
        "usage": usage_stats
    }

@router.post("/upgrade/{plan_type}")
def upgrade_plan(
    plan_type: PlanType,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upgrade user's plan (in a real app, this would integrate with payment processing)"""
    
    # Validate plan upgrade path
    plan_hierarchy = {
        PlanType.FREE: 0,
        PlanType.PREMIUM: 1,
        PlanType.EXTRA_PREMIUM: 2
    }
    
    current_level = plan_hierarchy.get(current_user.plan_type, 0)  # type: ignore
    target_level = plan_hierarchy.get(plan_type, 0)
    
    if target_level <= current_level:
        return {
            "message": "You are already on this plan or a higher tier",
            "current_plan": current_user.plan_type.value
        }
    
    # In a real implementation, you would:
    # 1. Redirect to payment processor (Stripe, PayPal, etc.)
    # 2. Verify payment completion
    # 3. Then upgrade the plan
    
    user_service = UserService(db)
    updated_user = user_service.upgrade_user_plan(current_user.id, plan_type)  # type: ignore
    
    return {
        "message": f"Successfully upgraded to {plan_type.value} plan",
        "new_plan": updated_user.plan_type.value,
        "note": "In production, this would require payment processing"
    }
