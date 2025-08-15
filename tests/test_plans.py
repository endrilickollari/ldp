"""
Tests for plans and usage endpoints
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import client
from app.models.user import PlanType, UsageLog


class TestPlansEndpoints:
    """Test plan management functionality"""

    def test_get_available_plans_solo_user(self, db_session, auth_headers_solo):
        """Test getting available plans for solo user"""
        response = client.get("/v1/plans/plans", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all plan types are present
        assert "free" in data
        assert "premium" in data
        assert "extra_premium" in data
        
        # Check solo user limits (standard)
        assert data["free"]["monthly_documents"] == 10
        assert data["free"]["max_file_size_mb"] == 5.0
        assert data["premium"]["monthly_documents"] == 100
        assert data["premium"]["max_file_size_mb"] == 25.0
        assert data["extra_premium"]["monthly_documents"] == 500
        assert data["extra_premium"]["max_file_size_mb"] == 100.0
        
        # Plan names should not have enterprise suffix
        assert "(Enterprise Enhanced)" not in data["free"]["name"]
        assert "(Enterprise Enhanced)" not in data["premium"]["name"]
        assert "(Enterprise Enhanced)" not in data["extra_premium"]["name"]

    def test_get_available_plans_enterprise_user(self, db_session, auth_headers_enterprise):
        """Test getting available plans for enterprise user"""
        response = client.get("/v1/plans/plans", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all plan types are present
        assert "free" in data
        assert "premium" in data
        assert "extra_premium" in data
        
        # Check enterprise user limits (enhanced - 2x documents, 2x file size)
        assert data["free"]["monthly_documents"] == 20  # 2x of 10
        assert data["free"]["max_file_size_mb"] == 10.0  # 2x of 5.0
        assert data["premium"]["monthly_documents"] == 200  # 2x of 100
        assert data["premium"]["max_file_size_mb"] == 50.0  # 2x of 25.0
        assert data["extra_premium"]["monthly_documents"] == 1000  # 2x of 500
        assert data["extra_premium"]["max_file_size_mb"] == 200.0  # 2x of 100.0
        
        # Plan names should have enterprise suffix
        assert "(Enterprise Enhanced)" in data["free"]["name"]
        assert "(Enterprise Enhanced)" in data["premium"]["name"]
        assert "(Enterprise Enhanced)" in data["extra_premium"]["name"]
        
        # Enhanced support levels
        assert "Enterprise" in data["free"]["support_level"]
        assert "Enterprise" in data["premium"]["support_level"]
        assert "Enterprise" in data["extra_premium"]["support_level"]

    def test_get_available_plans_unauthorized(self, db_session):
        """Test getting available plans without authentication fails"""
        response = client.get("/v1/plans/plans")
        
        assert response.status_code == 401

    def test_get_current_plan_solo_user(self, db_session, auth_headers_solo, solo_user):
        """Test getting current plan for solo user"""
        response = client.get("/v1/plans/current-plan", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_type"] == "solo"
        assert data["current_plan"] == "free"
        assert "plan_details" in data
        assert "usage" in data
        
        # Check plan details match solo limits
        plan_details = data["plan_details"]
        assert plan_details["monthly_documents"] == 10
        assert plan_details["max_file_size_mb"] == 5.0
        
        # Check usage stats structure
        usage = data["usage"]
        assert "documents_processed" in usage
        assert "current_month_usage" in usage
        assert "remaining_documents" in usage
        assert "plan_limit" in usage

    def test_get_current_plan_enterprise_user(self, db_session, auth_headers_enterprise, enterprise_user):
        """Test getting current plan for enterprise user"""
        response = client.get("/v1/plans/current-plan", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_type"] == "enterprise"
        assert data["current_plan"] == "premium"  # Enterprise user is on premium
        assert "plan_details" in data
        assert "usage" in data
        
        # Check plan details match enterprise limits
        plan_details = data["plan_details"]
        assert plan_details["monthly_documents"] == 200  # Enhanced limit
        assert plan_details["max_file_size_mb"] == 50.0  # Enhanced limit
        assert "Enterprise" in plan_details["support_level"]

    def test_get_current_plan_unauthorized(self, db_session):
        """Test getting current plan without authentication fails"""
        response = client.get("/v1/plans/current-plan")
        
        assert response.status_code == 401

    def test_get_usage_stats_no_usage(self, db_session, auth_headers_solo):
        """Test getting usage stats when user has no usage"""
        response = client.get("/v1/plans/usage", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["documents_processed"] == 0
        assert data["current_month_usage"] == 0
        assert data["remaining_documents"] == 10  # Full free plan limit
        assert data["plan_limit"] == 10

    def test_get_usage_stats_with_usage(self, db_session, auth_headers_solo, solo_user):
        """Test getting usage stats when user has some usage"""
        # Add some usage logs
        from datetime import datetime
        
        usage_logs = [
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
                success=False  # Failed, shouldn't count
            )
        ]
        
        for log in usage_logs:
            db_session.add(log)
        db_session.commit()
        
        response = client.get("/v1/plans/usage", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["documents_processed"] == 2  # Only successful ones
        assert data["current_month_usage"] == 2  # Current month usage
        assert data["remaining_documents"] == 8  # 10 - 2
        assert data["plan_limit"] == 10

    def test_get_usage_stats_enterprise_enhanced_limits(self, db_session, auth_headers_enterprise, enterprise_user):
        """Test that usage stats reflect enhanced enterprise limits"""
        response = client.get("/v1/plans/usage", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        
        # Enterprise premium plan should have 200 documents limit
        assert data["plan_limit"] == 200
        assert data["remaining_documents"] == 200  # No usage yet

    def test_get_usage_stats_unauthorized(self, db_session):
        """Test getting usage stats without authentication fails"""
        response = client.get("/v1/plans/usage")
        
        assert response.status_code == 401

    def test_upgrade_plan_success(self, db_session, auth_headers_solo):
        """Test successful plan upgrade"""
        response = client.post("/v1/plans/upgrade/premium", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "Successfully upgraded to premium plan" in data["message"]
        assert data["new_plan"] == "premium"
        assert "payment processing" in data["note"]  # Note about production implementation

    def test_upgrade_plan_same_level(self, db_session, auth_headers_solo):
        """Test upgrading to same plan level"""
        response = client.post("/v1/plans/upgrade/free", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "already on this plan" in data["message"]
        assert data["current_plan"] == "free"

    def test_upgrade_plan_downgrade_attempt(self, db_session, auth_headers_enterprise):
        """Test attempting to downgrade plan"""
        # Enterprise user is on premium, try to go to free
        response = client.post("/v1/plans/upgrade/free", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "already on this plan or a higher tier" in data["message"]
        assert data["current_plan"] == "premium"

    def test_upgrade_plan_to_extra_premium(self, db_session, auth_headers_solo):
        """Test upgrading to extra premium plan"""
        response = client.post("/v1/plans/upgrade/extra_premium", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "Successfully upgraded to extra_premium plan" in data["message"]
        assert data["new_plan"] == "extra_premium"

    def test_upgrade_plan_unauthorized(self, db_session):
        """Test upgrading plan without authentication fails"""
        response = client.post("/v1/plans/upgrade/premium")
        
        assert response.status_code == 401

    def test_upgrade_plan_invalid_plan_type(self, db_session, auth_headers_solo):
        """Test upgrading to invalid plan type fails"""
        response = client.post("/v1/plans/upgrade/invalid_plan", headers=auth_headers_solo)
        
        # This should fail with 422 due to enum validation
        assert response.status_code == 422


class TestPlanLimitsLogic:
    """Test plan limits calculation logic"""

    def test_plan_limits_calculation_solo_vs_enterprise(self, db_session):
        """Test that plan limits are calculated differently for solo vs enterprise users"""
        from app.services.user_service import UserService
        from app.models.user import UserType, PlanType
        
        # Test solo user limits
        solo_limits = UserService.get_plan_limits(PlanType.PREMIUM, UserType.SOLO)
        assert solo_limits["monthly_documents"] == 100
        assert solo_limits["max_file_size_mb"] == 25.0
        assert solo_limits["tokens_per_month"] == 500000
        
        # Test enterprise user limits (should be enhanced)
        enterprise_limits = UserService.get_plan_limits(PlanType.PREMIUM, UserType.ENTERPRISE)
        assert enterprise_limits["monthly_documents"] == 200  # 2x
        assert enterprise_limits["max_file_size_mb"] == 50.0  # 2x
        assert enterprise_limits["tokens_per_month"] == 750000  # 1.5x
        assert "Enterprise" in enterprise_limits["support_level"]

    def test_plan_features_structure(self, db_session, auth_headers_solo):
        """Test that plan features are properly structured"""
        response = client.get("/v1/plans/plans", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        
        for plan_name, plan_data in data.items():
            # Check required fields
            required_fields = [
                "name", "monthly_documents", "max_file_size_mb",
                "priority_processing", "support_level", "price_usd",
                "tokens_per_month", "features"
            ]
            
            for field in required_fields:
                assert field in plan_data, f"Field {field} missing from {plan_name} plan"
            
            # Check features is a list
            assert isinstance(plan_data["features"], list)
            assert len(plan_data["features"]) > 0
