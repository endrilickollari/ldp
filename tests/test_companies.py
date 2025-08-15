"""
Tests for company management endpoints
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import client
from app.models.user import User, Company, UserType


class TestCompanyEndpoints:
    """Test company management functionality"""

    def test_get_company_users_enterprise_user(self, db_session, auth_headers_enterprise, enterprise_user):
        """Test getting company users for enterprise user"""
        # Add another user to the same company
        second_user = User(
            email="manager@testcorp.com",
            username="manager_testcorp",
            full_name="Manager User",
            hashed_password="hashedpassword",
            user_type=UserType.ENTERPRISE,
            company_id=enterprise_user.company_id,
            is_active=True
        )
        db_session.add(second_user)
        db_session.commit()
        
        response = client.get("/v1/companies/users", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Check both users are returned
        emails = [user["email"] for user in data]
        assert "admin@testcorp.com" in emails
        assert "manager@testcorp.com" in emails
        
        # Check user data structure
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "username" in user
            assert "full_name" in user
            assert "user_type" in user
            assert "company_id" in user
            assert user["user_type"] == "enterprise"

    def test_get_company_users_single_user(self, db_session, auth_headers_enterprise):
        """Test getting company users when only one user exists"""
        response = client.get("/v1/companies/users", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "admin@testcorp.com"

    def test_get_company_users_solo_user_forbidden(self, db_session, auth_headers_solo):
        """Test that solo users can't access company users endpoint"""
        response = client.get("/v1/companies/users", headers=auth_headers_solo)
        
        assert response.status_code == 403
        assert "Only enterprise users can view company users" in response.json()["detail"]

    def test_get_company_users_unauthorized(self, db_session):
        """Test getting company users without authentication fails"""
        response = client.get("/v1/companies/users")

        assert response.status_code == 401

    def test_get_company_info_success(self, db_session, auth_headers_enterprise, enterprise_user):
        """Test getting company information successfully"""
        company_id = enterprise_user.company_id
        
        response = client.get(f"/v1/companies/{company_id}", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == company_id
        assert data["name"] == "Test Corp"
        assert data["domain"] == "testcorp.com"
        assert data["description"] == "Test company"
        assert data["is_active"] is True

    def test_get_company_info_solo_user_forbidden(self, db_session, auth_headers_solo, enterprise_user):
        """Test that solo users can't access company info endpoint"""
        company_id = enterprise_user.company_id
        
        response = client.get(f"/v1/companies/{company_id}", headers=auth_headers_solo)
        
        assert response.status_code == 403
        assert "Only enterprise users can view company information" in response.json()["detail"]

    def test_get_company_info_wrong_company(self, db_session, auth_headers_enterprise):
        """Test that enterprise user can't access other company's info"""
        # Create another company
        other_company = Company(
            name="Other Corp",
            domain="othercorp.com",
            description="Other company",
            is_active=True
        )
        db_session.add(other_company)
        db_session.commit()
        db_session.refresh(other_company)
        
        response = client.get(f"/v1/companies/{other_company.id}", 
                            headers=auth_headers_enterprise)
        
        assert response.status_code == 403
        assert "You can only access your own company information" in response.json()["detail"]

    def test_get_company_info_not_found(self, db_session, auth_headers_enterprise):
        """Test getting info for non-existent company"""
        response = client.get("/v1/companies/99999", headers=auth_headers_enterprise)

        assert response.status_code == 403  # User can't access other companies
        assert "You can only access your own company information" in response.json()["detail"]

    def test_get_company_info_unauthorized(self, db_session):
        """Test getting company info without authentication fails"""
        response = client.get("/v1/companies/1")

        assert response.status_code == 401

    def test_company_user_isolation(self, db_session, enterprise_user_data):
        """Test that users from different companies can't see each other"""
        # Register first enterprise user (creates first company)
        response1 = client.post("/v1/auth/register", json=enterprise_user_data)
        assert response1.status_code == 201
        
        # Register second enterprise user with different company
        user_data_2 = {
            "email": "admin@othercorp.com",
            "username": "admin_other",
            "full_name": "Other Admin",
            "password": "password456",
            "user_type": "enterprise",
            "company_name": "Other Corporation",
            "company_domain": "othercorp.com"
        }
        response2 = client.post("/v1/auth/register", json=user_data_2)
        assert response2.status_code == 201
        
        # Login first user
        login_response1 = client.post("/v1/auth/login", data={
            "username": enterprise_user_data["email"],
            "password": enterprise_user_data["password"]
        })
        token1 = login_response1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        # Login second user
        login_response2 = client.post("/v1/auth/login", data={
            "username": user_data_2["email"],
            "password": user_data_2["password"]
        })
        token2 = login_response2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Each user should only see their own company users
        users1_response = client.get("/v1/companies/users", headers=headers1)
        users1 = users1_response.json()
        assert len(users1) == 1
        assert users1[0]["email"] == enterprise_user_data["email"]
        
        users2_response = client.get("/v1/companies/users", headers=headers2)
        users2 = users2_response.json()
        assert len(users2) == 1
        assert users2[0]["email"] == user_data_2["email"]
        
        # Verify companies are different
        assert response1.json()["company_id"] != response2.json()["company_id"]
