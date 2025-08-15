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
def get_available_plans(current_user: User = Depends(get_current_active_user)):
    """Get all available plans with their features and pricing"""
    
    # Get base plan configurations
    free_limits = UserService.get_plan_limits(PlanType.FREE, current_user.user_type)  # type: ignore
    premium_limits = UserService.get_plan_limits(PlanType.PREMIUM, current_user.user_type)  # type: ignore
    extra_premium_limits = UserService.get_plan_limits(PlanType.EXTRA_PREMIUM, current_user.user_type)  # type: ignore
    
    user_type_suffix = " (Enterprise Enhanced)" if current_user.user_type.value == "enterprise" else ""  # type: ignore
    
    return {
        "free": {
            "name": f"Free Plan{user_type_suffix}",
            **free_limits,
            "features": [
                f"{free_limits['monthly_documents']} documents per month",
                f"{free_limits['max_file_size_mb']}MB max file size",
                "Community support",
                "Standard processing speed",
                "Basic document types (PDF, Excel, Images)"
            ]
        },
        "premium": {
            "name": f"Premium Plan{user_type_suffix}", 
            **premium_limits,
            "features": [
                f"{premium_limits['monthly_documents']} documents per month",
                f"{premium_limits['max_file_size_mb']}MB max file size", 
                "Priority processing queue",
                premium_limits['support_level'],
                "All document types supported",
                "Advanced AI analysis",
                "API access"
            ]
        },
        "extra_premium": {
            "name": f"Extra Premium Plan{user_type_suffix}",
            **extra_premium_limits,
            "features": [
                f"{extra_premium_limits['monthly_documents']} documents per month",
                f"{extra_premium_limits['max_file_size_mb']}MB max file size",
                "Highest priority processing",
                extra_premium_limits['support_level'],
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
    plan_limits = UserService.get_plan_limits(current_user.plan_type, current_user.user_type)  # type: ignore
    usage_stats = user_service.get_usage_stats(current_user)
    
    return {
        "user_type": current_user.user_type.value,  # type: ignore
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
