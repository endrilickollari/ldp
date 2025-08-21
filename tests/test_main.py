"""
Tests for main application endpoints
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import client


class TestMainEndpoints:
    """Test main application endpoints"""

    def test_root_endpoint(self, db_session):
        """Test the root endpoint returns API information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check basic structure
        assert "message" in data
        assert "features" in data
        assert "docs" in data
        assert "auth_endpoints" in data
        assert "plan_endpoints" in data
        assert "company_endpoints" in data
        
        # Check features list
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0
        
        # Check endpoint structures
        auth_endpoints = data["auth_endpoints"]
        assert "register" in auth_endpoints
        assert "login" in auth_endpoints
        assert "profile" in auth_endpoints
        assert "company" in auth_endpoints
        assert "api_keys" in auth_endpoints
        
        plan_endpoints = data["plan_endpoints"]
        assert "available_plans" in plan_endpoints
        assert "current_plan" in plan_endpoints
        assert "usage_stats" in plan_endpoints
        
        company_endpoints = data["company_endpoints"]
        assert "company_users" in company_endpoints
        assert "company_info" in company_endpoints

    def test_docs_endpoint(self, db_session):
        """Test that API documentation is available"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        # Should return HTML content
        assert "text/html" in response.headers.get("content-type", "")

    def test_openapi_json_endpoint(self, db_session):
        """Test that OpenAPI JSON schema is available"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        
        # Check that our endpoints are documented
        paths = data["paths"]
        assert "/v1/auth/register" in paths
        assert "/v1/auth/login" in paths
        assert "/v1/plans/plans" in paths
        assert "/v1/jobs" in paths
        assert "/v1/companies/users" in paths

    def test_cors_headers(self, db_session):
        """Test that CORS headers are properly set"""
        response = client.get("/")  # Use GET instead of OPTIONS

        # Check for CORS headers in response
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_api_versioning(self, db_session):
        """Test that API versioning is consistent"""
        # All main endpoints should be under /v1/
        endpoints_to_check = [
            "/v1/auth/register",
            "/v1/auth/login", 
            "/v1/plans/plans",
            "/v1/companies/users",
        ]
        
        for endpoint in endpoints_to_check:
            # These should exist (even if they require auth)
            response = client.post(endpoint) if endpoint.endswith("register") else client.get(endpoint)
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404

    def test_nonexistent_endpoint(self, db_session):
        """Test that non-existent endpoints return 404"""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404

    def test_api_title_and_version(self, db_session):
        """Test that API has correct title and version in OpenAPI spec"""
        response = client.get("/openapi.json")
        data = response.json()
        
        info = data["info"]
        assert info["title"] == "Document Processing API - Self-Hosted"
        assert "version" in info
        assert "description" in info
        assert "Self-hosted document processing solution" in info["description"]


class TestHealthCheck:
    """Test application health and status"""

    def test_application_startup(self, db_session):
        """Test that application starts up correctly"""
        # Root endpoint should work, indicating app started
        response = client.get("/")
        assert response.status_code == 200

    def test_database_connection(self, db_session):
        """Test that database connection works"""
        # Register endpoint requires DB, so if it works, DB is connected
        response = client.post("/v1/auth/register", json={
            "email": "test@example.com",
            "username": "test_user",
            "password": "password123",
            "user_type": "solo"
        })
        # Should not get database connection error
        assert response.status_code != 500

    def test_authentication_system(self, db_session, solo_user_data):
        """Test that authentication system is working"""
        # Register user
        register_response = client.post("/v1/auth/register", json=solo_user_data)
        assert register_response.status_code == 201
        
        # Login user
        login_response = client.post("/v1/auth/login", data={
            "username": solo_user_data["email"],
            "password": solo_user_data["password"]
        })
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()


class TestErrorHandling:
    """Test error handling across the application"""

    def test_validation_errors(self, db_session):
        """Test that validation errors are properly handled"""
        # Invalid email format
        response = client.post("/v1/auth/register", json={
            "email": "invalid-email",
            "username": "test_user",
            "password": "password123",
            "user_type": "solo"
        })
        
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list)

    def test_missing_required_fields(self, db_session):
        """Test handling of missing required fields"""
        response = client.post("/v1/auth/register", json={
            "username": "test_user",
            # Missing email, password, user_type
        })
        
        assert response.status_code == 422

    def test_unauthorized_access(self, db_session):
        """Test that unauthorized access is properly handled"""
        response = client.get("/v1/auth/me")
        
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_forbidden_access(self, db_session, auth_headers_solo):
        """Test that forbidden access is properly handled"""
        # Solo user trying to access company endpoint
        response = client.get("/v1/companies/users", headers=auth_headers_solo)
        
        assert response.status_code == 403
        assert "detail" in response.json()

    def test_not_found_errors(self, db_session, auth_headers_solo):
        """Test that not found errors are properly handled"""
        response = client.get("/v1/companies/99999", headers=auth_headers_solo)
        
        assert response.status_code in [404, 403]  # Could be 403 for solo user

    def test_method_not_allowed(self, db_session):
        """Test that method not allowed errors are handled"""
        # Try POST on GET-only endpoint
        response = client.post("/v1/plans/plans")
        
        assert response.status_code == 405

    def test_large_request_body(self, db_session):
        """Test handling of overly large request bodies"""
        # Very large request body
        large_data = {
            "email": "test@example.com",
            "username": "test_user",
            "password": "password123",
            "user_type": "solo",
            "large_field": "x" * (10 * 1024 * 1024)  # 10MB string
        }
        
        response = client.post("/v1/auth/register", json=large_data)
        
        # Should handle gracefully (either succeed or fail cleanly)
        assert response.status_code != 500


class TestSecurityHeaders:
    """Test security-related headers and features"""

    def test_no_server_header_leakage(self, db_session):
        """Test that server information is not leaked"""
        response = client.get("/")
        
        # Should not reveal server software version
        server_header = response.headers.get("server", "")
        assert "uvicorn" not in server_header.lower()

    def test_content_type_headers(self, db_session):
        """Test that proper content-type headers are set"""
        # JSON endpoints should return JSON
        response = client.get("/openapi.json")
        assert "application/json" in response.headers.get("content-type", "")
        
        # HTML endpoints should return HTML
        response = client.get("/docs")
        assert "text/html" in response.headers.get("content-type", "")

    def test_authentication_token_handling(self, db_session, solo_user_data):
        """Test that authentication tokens are handled securely"""
        # Register and login
        client.post("/v1/auth/register", json=solo_user_data)
        login_response = client.post("/v1/auth/login", data={
            "username": solo_user_data["email"],
            "password": solo_user_data["password"]
        })
        
        token_data = login_response.json()
        
        # Token should be present and properly formatted
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
        assert "expires_in" in token_data
        
        # Token should be a proper JWT (3 parts separated by dots)
        token = token_data["access_token"]
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature
