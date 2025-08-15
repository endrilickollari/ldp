"""
Tests for authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import client


class TestUserRegistration:
    """Test user registration functionality"""

    def test_register_solo_user_success(self, db_session, solo_user_data):
        """Test successful solo user registration"""
        response = client.post("/v1/auth/register", json=solo_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == solo_user_data["email"]
        assert data["username"] == solo_user_data["username"]
        assert data["user_type"] == "solo"
        assert data["company_id"] is None
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_enterprise_user_success(self, db_session, enterprise_user_data):
        """Test successful enterprise user registration"""
        response = client.post("/v1/auth/register", json=enterprise_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == enterprise_user_data["email"]
        assert data["username"] == enterprise_user_data["username"]
        assert data["user_type"] == "enterprise"
        assert data["company_id"] is not None
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, db_session, solo_user_data):
        """Test registration with duplicate email fails"""
        # Register first user
        client.post("/v1/auth/register", json=solo_user_data)
        
        # Try to register with same email
        response = client.post("/v1/auth/register", json=solo_user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_duplicate_username(self, db_session, solo_user_data):
        """Test registration with duplicate username fails"""
        # Register first user
        client.post("/v1/auth/register", json=solo_user_data)
        
        # Try to register with same username but different email
        duplicate_data = solo_user_data.copy()
        duplicate_data["email"] = "different@gmail.com"
        response = client.post("/v1/auth/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_enterprise_user_missing_company_info(self, db_session):
        """Test enterprise user registration without company info fails"""
        user_data = {
            "email": "user@company.com",
            "username": "enterprise_user",
            "full_name": "Enterprise User",
            "password": "password123",
            "user_type": "enterprise"
            # Missing company_name and company_domain
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 422

    def test_enterprise_user_email_domain_mismatch(self, db_session):
        """Test enterprise user with mismatched email domain fails"""
        user_data = {
            "email": "user@wrongdomain.com",
            "username": "enterprise_user",
            "full_name": "Enterprise User",
            "password": "password123",
            "user_type": "enterprise",
            "company_name": "Test Company",
            "company_domain": "testcompany.com"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 422

    def test_enterprise_users_same_company(self, db_session, enterprise_user_data):
        """Test multiple enterprise users can join same company"""
        # Register first user
        response1 = client.post("/v1/auth/register", json=enterprise_user_data)
        assert response1.status_code == 201
        company_id_1 = response1.json()["company_id"]
        
        # Register second user from same company
        user_data_2 = {
            "email": "mike@acmecorp.com",
            "username": "mike_jones",
            "full_name": "Mike Jones",
            "password": "password456",
            "user_type": "enterprise",
            "company_name": "ACME Corporation",
            "company_domain": "acmecorp.com"
        }
        
        response2 = client.post("/v1/auth/register", json=user_data_2)
        assert response2.status_code == 201
        company_id_2 = response2.json()["company_id"]
        
        # Both users should have same company_id
        assert company_id_1 == company_id_2


class TestUserLogin:
    """Test user login functionality"""

    def test_login_solo_user_success(self, db_session, solo_user):
        """Test successful solo user login"""
        response = client.post("/v1/auth/login", data={
            "username": "testuser@gmail.com",
            "password": "testpassword"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user"]["email"] == "testuser@gmail.com"
        assert data["user"]["user_type"] == "solo"

    def test_login_enterprise_user_success(self, db_session, enterprise_user):
        """Test successful enterprise user login"""
        response = client.post("/v1/auth/login", data={
            "username": "admin@testcorp.com",
            "password": "adminpassword"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@testcorp.com"
        assert data["user"]["user_type"] == "enterprise"

    def test_login_with_username(self, db_session, solo_user):
        """Test login using username instead of email"""
        response = client.post("/v1/auth/login", data={
            "username": "testuser",
            "password": "testpassword"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, db_session, solo_user):
        """Test login with wrong password fails"""
        response = client.post("/v1/auth/login", data={
            "username": "testuser@gmail.com",
            "password": "wrongpassword"
        })

        assert response.status_code == 401
        assert "Incorrect email/username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, db_session):
        """Test login with nonexistent user fails"""
        response = client.post("/v1/auth/login", data={
            "username": "nonexistent@example.com",
            "password": "anypassword"
        })

        assert response.status_code == 401
        assert "Incorrect email/username or password" in response.json()["detail"]

    def test_login_inactive_user(self, db_session, solo_user):
        """Test login with inactive user fails"""
        # Make user inactive
        solo_user.is_active = False
        db_session.commit()
        
        response = client.post("/v1/auth/login", data={
            "username": "testuser@gmail.com",
            "password": "testpassword"
        })
        
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]


class TestUserProfile:
    """Test user profile endpoints"""

    def test_get_current_user_solo(self, db_session, auth_headers_solo):
        """Test getting current user info for solo user"""
        response = client.get("/v1/auth/me", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@gmail.com"
        assert data["user_type"] == "solo"
        assert data["company_id"] is None

    def test_get_current_user_enterprise(self, db_session, auth_headers_enterprise):
        """Test getting current user info for enterprise user"""
        response = client.get("/v1/auth/me", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@testcorp.com"
        assert data["user_type"] == "enterprise"
        assert data["company_id"] is not None

    def test_get_current_user_unauthorized(self, db_session):
        """Test getting current user without authentication fails"""
        response = client.get("/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, db_session):
        """Test getting current user with invalid token fails"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/v1/auth/me", headers=headers)

        assert response.status_code == 401
class TestCompanyInfo:
    """Test company information endpoints"""

    def test_get_company_info_enterprise_user(self, db_session, auth_headers_enterprise):
        """Test getting company info for enterprise user"""
        response = client.get("/v1/auth/company", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Corp"
        assert data["domain"] == "testcorp.com"
        assert data["description"] == "Test company"

    def test_get_company_info_solo_user(self, db_session, auth_headers_solo):
        """Test getting company info for solo user fails"""
        response = client.get("/v1/auth/company", headers=auth_headers_solo)
        
        assert response.status_code == 400
        assert "not associated with a company" in response.json()["detail"]

    def test_get_company_info_unauthorized(self, db_session):
        """Test getting company info without authentication fails"""
        response = client.get("/v1/auth/company")

        assert response.status_code == 401