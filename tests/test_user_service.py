"""
Tests for user service functionality
"""

import pytest
from datetime import datetime, timedelta
from app.services.user_service import UserService
from app.models.user import User, Company, UserType, PlanType, UsageLog
from tests.conftest import TestingSessionLocal


class TestUserService:
    """Test UserService class functionality"""

    def test_get_plan_limits_solo_user(self, db_session):
        """Test getting plan limits for solo users"""
        limits = UserService.get_plan_limits(PlanType.PREMIUM, UserType.SOLO)
        
        assert limits["monthly_documents"] == 100
        assert limits["max_file_size_mb"] == 25.0
        assert limits["priority_processing"] is True
        assert limits["support_level"] == "Email Support"
        assert limits["price_usd"] == 29.99
        assert limits["tokens_per_month"] == 500000

    def test_get_plan_limits_enterprise_user(self, db_session):
        """Test getting enhanced plan limits for enterprise users"""
        limits = UserService.get_plan_limits(PlanType.PREMIUM, UserType.ENTERPRISE)
        
        # Enhanced limits (2x documents, 2x file size, 1.5x tokens)
        assert limits["monthly_documents"] == 200  # 2x of 100
        assert limits["max_file_size_mb"] == 50.0  # 2x of 25.0
        assert limits["priority_processing"] is True
        assert limits["support_level"] == "Enterprise Email Support"
        assert limits["price_usd"] == 29.99  # Price same
        assert limits["tokens_per_month"] == 750000  # 1.5x of 500000

    def test_get_plan_limits_all_plan_types(self, db_session):
        """Test that all plan types have proper limits"""
        plan_types = [PlanType.FREE, PlanType.PREMIUM, PlanType.EXTRA_PREMIUM]
        
        for plan_type in plan_types:
            solo_limits = UserService.get_plan_limits(plan_type, UserType.SOLO)
            enterprise_limits = UserService.get_plan_limits(plan_type, UserType.ENTERPRISE)
            
            # Enterprise should have enhanced limits
            assert enterprise_limits["monthly_documents"] == solo_limits["monthly_documents"] * 2
            assert enterprise_limits["max_file_size_mb"] == solo_limits["max_file_size_mb"] * 2
            assert enterprise_limits["tokens_per_month"] == int(solo_limits["tokens_per_month"] * 1.5)
            assert "Enterprise" in enterprise_limits["support_level"]

    def test_get_current_month_usage_no_usage(self, db_session, solo_user):
        """Test getting current month usage when user has no usage"""
        user_service = UserService(db_session)
        usage = user_service.get_current_month_usage(solo_user.id)
        
        assert usage == 0

    def test_get_current_month_usage_with_usage(self, db_session, solo_user):
        """Test getting current month usage with some usage logs"""
        # Add usage logs for current month
        current_month_logs = [
            UsageLog(
                user_id=solo_user.id,
                job_id="job1",
                document_filename="doc1.pdf",
                file_size_bytes=1000,
                success=True
            ),
            UsageLog(
                user_id=solo_user.id,
                job_id="job2",
                document_filename="doc2.pdf",
                file_size_bytes=2000,
                success=True
            ),
            UsageLog(
                user_id=solo_user.id,
                job_id="job3",
                document_filename="doc3.pdf",
                file_size_bytes=1500,
                success=False  # Should not count
            )
        ]
        
        for log in current_month_logs:
            db_session.add(log)
        db_session.commit()
        
        user_service = UserService(db_session)
        usage = user_service.get_current_month_usage(solo_user.id)
        
        assert usage == 2  # Only successful ones

    def test_get_current_month_usage_different_months(self, db_session, solo_user):
        """Test that usage from different months doesn't count"""
        # Add usage log from previous month
        last_month = datetime.utcnow() - timedelta(days=35)
        old_log = UsageLog(
            user_id=solo_user.id,
            job_id="old_job",
            document_filename="old_doc.pdf",
            file_size_bytes=1000,
            success=True,
            created_at=last_month
        )
        db_session.add(old_log)
        
        # Add current month log
        current_log = UsageLog(
            user_id=solo_user.id,
            job_id="current_job",
            document_filename="current_doc.pdf",
            file_size_bytes=1000,
            success=True
        )
        db_session.add(current_log)
        db_session.commit()
        
        user_service = UserService(db_session)
        usage = user_service.get_current_month_usage(solo_user.id)
        
        assert usage == 1  # Only current month

    def test_get_usage_stats_no_usage(self, db_session, solo_user):
        """Test getting usage stats when user has no usage"""
        user_service = UserService(db_session)
        stats = user_service.get_usage_stats(solo_user)
        
        assert stats.documents_processed == 0
        assert stats.current_month_usage == 0
        assert stats.remaining_documents == 10  # Free plan limit
        assert stats.plan_limit == 10

    def test_get_usage_stats_with_usage(self, db_session, solo_user):
        """Test getting usage stats with some usage"""
        # Add various usage logs
        usage_logs = [
            # Current month successful
            UsageLog(user_id=solo_user.id, job_id="job1", document_filename="doc1.pdf", 
                    file_size_bytes=1000, success=True),
            UsageLog(user_id=solo_user.id, job_id="job2", document_filename="doc2.pdf", 
                    file_size_bytes=2000, success=True),
            # Current month failed
            UsageLog(user_id=solo_user.id, job_id="job3", document_filename="doc3.pdf", 
                    file_size_bytes=1500, success=False),
            # Old successful (should count in total but not current month)
            UsageLog(user_id=solo_user.id, job_id="old_job", document_filename="old_doc.pdf", 
                    file_size_bytes=1000, success=True,
                    created_at=datetime.utcnow() - timedelta(days=35))
        ]
        
        for log in usage_logs:
            db_session.add(log)
        db_session.commit()
        
        user_service = UserService(db_session)
        stats = user_service.get_usage_stats(solo_user)
        
        assert stats.documents_processed == 3  # All successful (including old)
        assert stats.current_month_usage == 2  # Current month successful only
        assert stats.remaining_documents == 8  # 10 - 2
        assert stats.plan_limit == 10

    def test_get_usage_stats_enterprise_user(self, db_session, enterprise_user):
        """Test getting usage stats for enterprise user (enhanced limits)"""
        user_service = UserService(db_session)
        stats = user_service.get_usage_stats(enterprise_user)
        
        # Enterprise premium plan should have enhanced limits
        assert stats.plan_limit == 200  # Enhanced premium limit
        assert stats.remaining_documents == 200  # No usage yet

    def test_can_process_document_within_limits(self, db_session, solo_user):
        """Test can_process_document when within all limits"""
        user_service = UserService(db_session)
        
        can_process, message = user_service.can_process_document(solo_user, 3.0)  # 3MB file
        
        assert can_process is True
        assert message == "OK"

    def test_can_process_document_file_size_exceeded(self, db_session, solo_user):
        """Test can_process_document when file size exceeds limit"""
        user_service = UserService(db_session)
        
        can_process, message = user_service.can_process_document(solo_user, 10.0)  # 10MB file (> 5MB limit)
        
        assert can_process is False
        assert "File size exceeds" in message
        assert "5.0MB limit" in message

    def test_can_process_document_monthly_limit_exceeded(self, db_session, solo_user):
        """Test can_process_document when monthly limit is exceeded"""
        # Add usage logs to exceed monthly limit (10 for free plan)
        for i in range(10):
            log = UsageLog(
                user_id=solo_user.id,
                job_id=f"job{i}",
                document_filename=f"doc{i}.pdf",
                file_size_bytes=1000,
                success=True
            )
            db_session.add(log)
        db_session.commit()
        
        user_service = UserService(db_session)
        can_process, message = user_service.can_process_document(solo_user, 1.0)
        
        assert can_process is False
        assert "Monthly limit of 10 documents exceeded" in message

    def test_can_process_document_enterprise_enhanced_limits(self, db_session, enterprise_user):
        """Test that enterprise users have enhanced limits"""
        user_service = UserService(db_session)
        
        # File size that would exceed solo limit but within enterprise limit
        can_process, message = user_service.can_process_document(enterprise_user, 30.0)  # 30MB
        
        assert can_process is True  # Should work for enterprise (50MB limit)
        assert message == "OK"

    def test_log_usage_success(self, db_session, solo_user):
        """Test logging successful usage"""
        user_service = UserService(db_session)
        
        usage_log = user_service.log_usage(
            user_id=solo_user.id,
            job_id="test_job",
            filename="test.pdf",
            file_size_bytes=1024,
            processing_time=5.5,
            tokens_used=1000,
            success=True
        )
        
        assert usage_log.id is not None
        assert usage_log.user_id == solo_user.id
        assert getattr(usage_log, 'job_id') == "test_job"
        assert getattr(usage_log, 'document_filename') == "test.pdf"
        assert getattr(usage_log, 'file_size_bytes') == 1024
        assert getattr(usage_log, 'processing_time_seconds') == 5.5
        assert getattr(usage_log, 'tokens_used') == 1000
        assert bool(usage_log.success) is True
        assert usage_log.error_message is None

    def test_log_usage_failure(self, db_session, solo_user):
        """Test logging failed usage"""
        user_service = UserService(db_session)
        
        usage_log = user_service.log_usage(
            user_id=solo_user.id,
            job_id="failed_job",
            filename="corrupt.pdf",
            file_size_bytes=512,
            success=False,
            error_message="File is corrupted"
        )
        
        assert bool(usage_log.success) is False
        assert getattr(usage_log, 'error_message') == "File is corrupted"
        assert usage_log.processing_time_seconds is None
        assert usage_log.tokens_used is None

    def test_upgrade_user_plan_success(self, db_session, solo_user):
        """Test successful plan upgrade"""
        user_service = UserService(db_session)
        
        updated_user = user_service.upgrade_user_plan(solo_user.id, PlanType.PREMIUM)
        
        assert getattr(updated_user, 'plan_type') == PlanType.PREMIUM
        
        # Verify in database
        db_user = db_session.query(User).filter(User.id == solo_user.id).first()
        assert bool(db_user.plan_type == PlanType.PREMIUM) is True

    def test_upgrade_user_plan_nonexistent_user(self, db_session):
        """Test upgrading plan for non-existent user"""
        user_service = UserService(db_session)
        
        with pytest.raises(ValueError, match="User not found"):
            user_service.upgrade_user_plan(99999, PlanType.PREMIUM)

    def test_get_company_users(self, db_session, enterprise_user):
        """Test getting all users for a company"""
        # Add another user to the same company
        second_user = User(
            email="manager@testcorp.com",
            username="manager",
            full_name="Manager User",
            hashed_password="hashedpassword",
            user_type=UserType.ENTERPRISE,
            company_id=enterprise_user.company_id,
            is_active=True
        )
        db_session.add(second_user)
        db_session.commit()
        
        user_service = UserService(db_session)
        company_users = user_service.get_company_users(enterprise_user.company_id)
        
        assert len(company_users) == 2
        emails = [user.email for user in company_users]
        assert "admin@testcorp.com" in emails
        assert "manager@testcorp.com" in emails

    def test_get_company_by_domain_exists(self, db_session, enterprise_user):
        """Test getting company by domain when it exists"""
        user_service = UserService(db_session)
        company = user_service.get_company_by_domain("testcorp.com")
        
        assert company is not None
        assert getattr(company, 'name') == "Test Corp"
        assert getattr(company, 'domain') == "testcorp.com"

    def test_get_company_by_domain_not_exists(self, db_session):
        """Test getting company by domain when it doesn't exist"""
        user_service = UserService(db_session)
        company = user_service.get_company_by_domain("nonexistent.com")
        
        assert company is None
        assert company is None

    def test_create_company(self, db_session):
        """Test creating a new company"""
        user_service = UserService(db_session)
        
        company = user_service.create_company(
            name="New Corp",
            domain="newcorp.com",
            description="A new company",
            website="https://newcorp.com"
        )
        
        assert company.id is not None
        assert str(company.name) == "New Corp"
        assert str(company.domain) == "newcorp.com"
        assert str(company.description) == "A new company"
        assert str(company.website) == "https://newcorp.com"
        assert bool(company.is_active) is True
        
        # Verify in database
        db_company = db_session.query(Company).filter(Company.id == company.id).first()
        assert db_company is not None
        assert str(db_company.name) == "New Corp"
