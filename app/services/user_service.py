from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from calendar import monthrange
from app.models.user import User, PlanLimits, UsageLog, PlanType
from app.schemas.user import UsageStats
from typing import Dict, Any, Optional, Tuple

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_plan_limits(self, plan_type: PlanType) -> Dict[str, Any]:
        """Get plan limits for a given plan type"""
        plan_configs = {
            PlanType.FREE: {
                "monthly_documents": 10,
                "max_file_size_mb": 5.0,
                "priority_processing": False,
                "support_level": "Community",
                "price_usd": 0.0,
                "tokens_per_month": 50000
            },
            PlanType.PREMIUM: {
                "monthly_documents": 100,
                "max_file_size_mb": 25.0,
                "priority_processing": True,
                "support_level": "Email Support",
                "price_usd": 29.99,
                "tokens_per_month": 500000
            },
            PlanType.EXTRA_PREMIUM: {
                "monthly_documents": 500,
                "max_file_size_mb": 100.0,
                "priority_processing": True,
                "support_level": "Priority Support + Phone",
                "price_usd": 99.99,
                "tokens_per_month": 2000000
            }
        }
        return plan_configs.get(plan_type, plan_configs[PlanType.FREE])
    
    def get_current_month_usage(self, user_id: int) -> int:
        """Get current month's document processing count for a user"""
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)
        end_of_month = datetime(now.year, now.month, monthrange(now.year, now.month)[1], 23, 59, 59)
        
        usage_count = self.db.query(UsageLog).filter(
            UsageLog.user_id == user_id,
            UsageLog.created_at >= start_of_month,
            UsageLog.created_at <= end_of_month,
            UsageLog.success == True
        ).count()
        
        return usage_count
    
    def get_usage_stats(self, user: User) -> UsageStats:
        """Get usage statistics for a user"""
        plan_limits = self.get_plan_limits(user.plan_type)  # type: ignore
        current_usage = self.get_current_month_usage(user.id)  # type: ignore
        monthly_limit = plan_limits["monthly_documents"]
        
        # Total documents processed (all time)
        total_processed = self.db.query(UsageLog).filter(
            UsageLog.user_id == user.id,
            UsageLog.success == True
        ).count()
        
        return UsageStats(
            documents_processed=total_processed,
            current_month_usage=current_usage,
            remaining_documents=max(0, monthly_limit - current_usage),
            plan_limit=monthly_limit
        )
    
    def can_process_document(self, user: User, file_size_mb: float) -> tuple[bool, str]:
        """Check if user can process a document based on their plan"""
        plan_limits = self.get_plan_limits(user.plan_type)  # type: ignore
        current_usage = self.get_current_month_usage(user.id)  # type: ignore
        
        # Check monthly limit
        if current_usage >= plan_limits["monthly_documents"]:
            return False, f"Monthly limit of {plan_limits['monthly_documents']} documents exceeded"
        
        # Check file size limit
        if file_size_mb > plan_limits["max_file_size_mb"]:
            return False, f"File size exceeds {plan_limits['max_file_size_mb']}MB limit for {user.plan_type.value} plan"
        
        return True, "OK"
    
    def log_usage(
        self,
        user_id: int,
        api_key_id: Optional[int] = None,
        job_id: str = "",
        filename: str = "",
        file_size_bytes: int = 0,
        processing_time: Optional[float] = None,
        tokens_used: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> UsageLog:
        """Log API usage for billing and analytics"""
        
        usage_log = UsageLog(
            user_id=user_id,
            api_key_id=api_key_id,
            job_id=job_id,
            document_filename=filename,
            file_size_bytes=file_size_bytes,
            processing_time_seconds=processing_time,
            tokens_used=tokens_used,
            success=success,
            error_message=error_message
        )
        
        self.db.add(usage_log)
        self.db.commit()
        self.db.refresh(usage_log)
        
        return usage_log
    
    def upgrade_user_plan(self, user_id: int, new_plan: PlanType) -> User:
        """Upgrade user's plan"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.plan_type = new_plan  # type: ignore
        self.db.commit()
        self.db.refresh(user)
        
        return user
