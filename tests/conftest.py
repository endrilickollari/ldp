"""
Test configuration and fixtures
"""

import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db, Base
from app.main import app
from app.models.user import User, Company, PlanType, UserType, APIKey, PlanLimits, UsageLog
from app.core.auth import get_password_hash

# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Set up test database"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed plan limits
    db = TestingSessionLocal()
    try:
        # Check if plan limits already exist
        existing_plans = db.query(PlanLimits).count()
        if existing_plans == 0:
            plan_configs = [
                PlanLimits(
                    plan_type=PlanType.FREE,
                    monthly_documents=10,
                    max_file_size_mb=5.0,
                    priority_processing=False,
                    support_level="Community",
                    price_usd=0.0
                ),
                PlanLimits(
                    plan_type=PlanType.PREMIUM,
                    monthly_documents=100,
                    max_file_size_mb=25.0,
                    priority_processing=True,
                    support_level="Email Support",
                    price_usd=29.99
                ),
                PlanLimits(
                    plan_type=PlanType.EXTRA_PREMIUM,
                    monthly_documents=500,
                    max_file_size_mb=100.0,
                    priority_processing=True,
                    support_level="Priority Support + Phone",
                    price_usd=99.99
                )
            ]
            
            for plan in plan_configs:
                db.add(plan)
            
            db.commit()
    finally:
        db.close()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    # Clear all data before each test
    db = TestingSessionLocal()
    try:
        # Delete all data but keep plan limits
        db.query(UsageLog).delete()
        db.query(APIKey).delete()
        db.query(User).delete()
        db.query(Company).delete()
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture
def solo_user_data():
    """Sample solo user data"""
    return {
        "email": "john@gmail.com",
        "username": "john_doe",
        "full_name": "John Doe",
        "password": "secure_password_123",
        "user_type": "solo"
    }


@pytest.fixture
def enterprise_user_data():
    """Sample enterprise user data"""
    return {
        "email": "sarah@acmecorp.com",
        "username": "sarah_smith",
        "full_name": "Sarah Smith",
        "password": "secure_password_456",
        "user_type": "enterprise",
        "company_name": "ACME Corporation",
        "company_domain": "acmecorp.com"
    }


@pytest.fixture
def solo_user(db_session):
    """Create a solo user for testing"""
    user = User(
        email="testuser@gmail.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        user_type=UserType.SOLO,
        plan_type=PlanType.FREE,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def enterprise_user(db_session):
    """Create an enterprise user and company for testing"""
    # Create company first
    company = Company(
        name="Test Corp",
        domain="testcorp.com",
        description="Test company",
        is_active=True
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    
    # Create user
    user = User(
        email="admin@testcorp.com",
        username="admin_testcorp",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword"),
        user_type=UserType.ENTERPRISE,
        plan_type=PlanType.PREMIUM,
        company_id=company.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def solo_user_token(solo_user):
    """Get authentication token for solo user"""
    response = client.post("/v1/auth/login", data={
        "username": "testuser@gmail.com",
        "password": "testpassword"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def enterprise_user_token(enterprise_user):
    """Get authentication token for enterprise user"""
    response = client.post("/v1/auth/login", data={
        "username": "admin@testcorp.com",
        "password": "adminpassword"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers_solo(solo_user_token):
    """Authorization headers for solo user"""
    return {"Authorization": f"Bearer {solo_user_token}"}


@pytest.fixture
def auth_headers_enterprise(enterprise_user_token):
    """Authorization headers for enterprise user"""
    return {"Authorization": f"Bearer {enterprise_user_token}"}
