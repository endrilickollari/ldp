"""
Test API parameter validation for multi-page features
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.models.user import APIKey
from tests.conftest import client


class TestMultiPageAPIValidation:
    """Test API validation for multi-page parameters"""

    def test_create_job_valid_page_parameters(self, db_session, auth_headers_solo):
        """Test job creation with valid page parameters"""
        # Create a dummy file
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        with patch('workers.celery_app.celery_app.send_task') as mock_send_task:
            mock_send_task.return_value.id = "test-job-id"
            
            response = client.post(
                "/v1/jobs",
                headers=auth_headers_solo,
                files={"file": test_file},
                data={
                    "page_start": "2",
                    "page_end": "5",
                    "output_format": "per_page"
                }
            )
            
            assert response.status_code == 202
            result = response.json()
            assert "job_id" in result
            assert result["status"] == "queued"

    def test_create_job_invalid_page_start_negative(self, auth_headers_solo):
        """Test job creation with negative page_start"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        response = client.post(
            "/v1/jobs",
            headers=auth_headers_solo,
            files={"file": test_file},
            data={
                "page_start": "0",  # Invalid: must be >= 1
                "page_end": "5"
            }
        )
        
        assert response.status_code == 400
        assert "page_start must be >= 1" in response.json()["detail"]

    def test_create_job_invalid_page_end_negative(self, auth_headers_solo):
        """Test job creation with negative page_end"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        response = client.post(
            "/v1/jobs",
            headers=auth_headers_solo,
            files={"file": test_file},
            data={
                "page_start": "2",
                "page_end": "-1"  # Invalid: must be >= 1
            }
        )
        
        assert response.status_code == 400
        assert "page_end must be >= 1" in response.json()["detail"]

    def test_create_job_invalid_page_range_order(self, auth_headers_solo):
        """Test job creation with page_start > page_end"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        response = client.post(
            "/v1/jobs",
            headers=auth_headers_solo,
            files={"file": test_file},
            data={
                "page_start": "10",
                "page_end": "5"  # Invalid: page_start > page_end
            }
        )
        
        assert response.status_code == 400
        assert "page_start must be <= page_end" in response.json()["detail"]

    def test_create_job_invalid_output_format(self, auth_headers_solo):
        """Test job creation with invalid output_format"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        response = client.post(
            "/v1/jobs",
            headers=auth_headers_solo,
            files={"file": test_file},
            data={
                "output_format": "invalid_format"  # Invalid: must be 'combined' or 'per_page'
            }
        )
        
        assert response.status_code == 400
        assert "output_format must be 'combined' or 'per_page'" in response.json()["detail"]

    def test_create_job_page_start_only(self, auth_headers_solo):
        """Test job creation with only page_start specified"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        with patch('workers.celery_app.celery_app.send_task') as mock_send_task:
            mock_send_task.return_value.id = "test-job-id"
            
            response = client.post(
                "/v1/jobs",
                headers=auth_headers_solo,
                files={"file": test_file},
                data={
                    "page_start": "3"  # Only start specified - should process from page 3 to end
                }
            )
            
            assert response.status_code == 202
            result = response.json()
            assert "job_id" in result

    def test_create_job_page_end_only(self, auth_headers_solo):
        """Test job creation with only page_end specified"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        with patch('workers.celery_app.celery_app.send_task') as mock_send_task:
            mock_send_task.return_value.id = "test-job-id"
            
            response = client.post(
                "/v1/jobs",
                headers=auth_headers_solo,
                files={"file": test_file},
                data={
                    "page_end": "5"  # Only end specified - should process from page 1 to 5
                }
            )
            
            assert response.status_code == 202
            result = response.json()
            assert "job_id" in result

    def test_create_job_default_values(self, auth_headers_solo):
        """Test job creation with default parameter values"""
        test_file = ("test.pdf", b"dummy pdf content", "application/pdf")
        
        with patch('workers.celery_app.celery_app.send_task') as mock_send_task:
            mock_send_task.return_value.id = "test-job-id"
            
            # Don't specify any page parameters - should use defaults
            response = client.post(
                "/v1/jobs",
                headers=auth_headers_solo,
                files={"file": test_file}
            )
            
            assert response.status_code == 202
            result = response.json()
            assert "job_id" in result
            assert result["status"] == "queued"
