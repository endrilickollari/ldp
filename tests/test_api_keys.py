"""
Tests for API key management endpoints
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import client
from app.models.user import APIKey


class TestAPIKeyManagement:
    """Test API key management functionality"""

    def test_create_api_key_solo_user(self, db_session, auth_headers_solo):
        """Test creating API key for solo user"""
        api_key_data = {"key_name": "Test API Key"}
        
        response = client.post("/v1/auth/api-keys", 
                             json=api_key_data, 
                             headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        assert data["key_name"] == "Test API Key"
        assert "api_key" in data
        assert data["is_active"] is True
        assert len(data["api_key"]) > 20  # Should be a proper API key

    def test_create_api_key_enterprise_user(self, db_session, auth_headers_enterprise):
        """Test creating API key for enterprise user"""
        api_key_data = {"key_name": "Enterprise API Key"}
        
        response = client.post("/v1/auth/api-keys", 
                             json=api_key_data, 
                             headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert data["key_name"] == "Enterprise API Key"
        assert "api_key" in data
        assert data["is_active"] is True

    def test_create_api_key_unauthorized(self, db_session):
        """Test that creating API key without authentication fails"""
        data = {"name": "Test Key"}
        
        response = client.post("/v1/auth/api-keys", json=data)
        
        assert response.status_code == 401

    def test_create_multiple_api_keys(self, db_session, auth_headers_solo):
        """Test creating multiple API keys"""
        # Create first API key
        response1 = client.post("/v1/auth/api-keys", 
                               json={"key_name": "Key 1"}, 
                               headers=auth_headers_solo)
        assert response1.status_code == 200
        
        # Create second API key
        response2 = client.post("/v1/auth/api-keys", 
                               json={"key_name": "Key 2"}, 
                               headers=auth_headers_solo)
        assert response2.status_code == 200
        
        # Keys should be different
        assert response1.json()["api_key"] != response2.json()["api_key"]

    def test_create_api_key_limit_exceeded(self, db_session, auth_headers_solo, solo_user):
        """Test API key creation limit (5 keys max)"""
        # Create 5 API keys (should be fine)
        for i in range(5):
            response = client.post("/v1/auth/api-keys", 
                                 json={"key_name": f"Key {i+1}"}, 
                                 headers=auth_headers_solo)
            assert response.status_code == 200
        
        # Try to create 6th key (should fail)
        response = client.post("/v1/auth/api-keys", 
                             json={"key_name": "Key 6"}, 
                             headers=auth_headers_solo)
        
        assert response.status_code == 400
        assert "Maximum of 5 active API keys" in response.json()["detail"]

    def test_list_api_keys_solo_user(self, db_session, auth_headers_solo):
        """Test listing API keys for solo user"""
        # Create a couple of API keys first
        client.post("/v1/auth/api-keys", 
                   json={"key_name": "Key 1"}, 
                   headers=auth_headers_solo)
        client.post("/v1/auth/api-keys", 
                   json={"key_name": "Key 2"}, 
                   headers=auth_headers_solo)
        
        response = client.get("/v1/auth/api-keys", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("key_name" in key for key in data)
        assert all("api_key" in key for key in data)
        assert all("is_active" in key for key in data)

    def test_list_api_keys_enterprise_user(self, db_session, auth_headers_enterprise):
        """Test listing API keys for enterprise user"""
        # Create an API key first
        client.post("/v1/auth/api-keys", 
                   json={"key_name": "Enterprise Key"}, 
                   headers=auth_headers_enterprise)
        
        response = client.get("/v1/auth/api-keys", headers=auth_headers_enterprise)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key_name"] == "Enterprise Key"

    def test_list_api_keys_empty(self, db_session, auth_headers_solo):
        """Test listing API keys when user has none"""
        response = client.get("/v1/auth/api-keys", headers=auth_headers_solo)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_list_api_keys_unauthorized(self, db_session):
        """Test listing API keys without authentication fails"""
        response = client.get("/v1/auth/api-keys")
        
        assert response.status_code == 401

    def test_revoke_api_key_success(self, db_session, auth_headers_solo):
        """Test revoking API key successfully"""
        # Create an API key first
        create_response = client.post("/v1/auth/api-keys", 
                                    json={"key_name": "Test Key"}, 
                                    headers=auth_headers_solo)
        key_id = create_response.json()["id"]
        
        # Revoke the key
        response = client.delete(f"/v1/auth/api-keys/{key_id}", 
                               headers=auth_headers_solo)
        
        assert response.status_code == 200
        assert "revoked successfully" in response.json()["message"]
        
        # Verify key is marked as inactive
        list_response = client.get("/v1/auth/api-keys", headers=auth_headers_solo)
        keys = list_response.json()
        revoked_key = next((k for k in keys if k["id"] == key_id), None)
        assert revoked_key is not None
        assert revoked_key["is_active"] is False

    def test_revoke_api_key_not_found(self, db_session, auth_headers_solo):
        """Test revoking non-existent API key fails"""
        response = client.delete("/v1/auth/api-keys/99999", 
                               headers=auth_headers_solo)
        
        assert response.status_code == 404
        assert "API key not found" in response.json()["detail"]

    def test_revoke_other_users_api_key(self, db_session, auth_headers_solo, auth_headers_enterprise):
        """Test that user can't revoke another user's API key"""
        # Create API key for enterprise user
        create_response = client.post("/v1/auth/api-keys", 
                                    json={"key_name": "Enterprise Key"}, 
                                    headers=auth_headers_enterprise)
        key_id = create_response.json()["id"]
        
        # Try to revoke with solo user credentials
        response = client.delete(f"/v1/auth/api-keys/{key_id}", 
                               headers=auth_headers_solo)
        
        assert response.status_code == 404
        assert "API key not found" in response.json()["detail"]

    def test_revoke_api_key_unauthorized(self, db_session):
        """Test revoking API key without authentication fails"""
        response = client.delete("/v1/auth/api-keys/1")
        
        assert response.status_code == 401
