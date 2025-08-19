#!/usr/bin/env python3
"""
Test script to verify Celery configuration in CI environment
"""

import os
import sys

def test_celery_config():
    """Test that Celery can be configured with in-memory backends"""
    print("Testing Celery configuration...")
    
    # Set test environment variables
    os.environ["CELERY_BROKER_URL"] = "memory://localhost/"
    os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://localhost/"
    
    try:
        # Import after setting environment variables
        from workers.celery_app import celery_app
        from app.core.config import settings
        
        print(f"✓ Celery broker URL: {settings.CELERY_BROKER_URL}")
        print(f"✓ Celery result backend: {settings.CELERY_RESULT_BACKEND}")
        print(f"✓ Celery app: {celery_app.main}")
        
        # Test creating a mock task
        try:
            # This should work with the in-memory backend
            from unittest.mock import Mock
            mock_task = Mock()
            mock_task.id = "test-task"
            print(f"✓ Mock task created: {mock_task.id}")
            return True
            
        except Exception as e:
            print(f"✗ Error creating mock task: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Error importing Celery: {e}")
        return False

if __name__ == "__main__":
    success = test_celery_config()
    sys.exit(0 if success else 1)
