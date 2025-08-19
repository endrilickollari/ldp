from pydantic_settings import BaseSettings
from enum import Enum

class DeploymentMode(str, Enum):
    SELF_HOSTED = "self_hosted"
    SAAS = "saas"

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"  # Default fallback
    
    # External APIs
    GOOGLE_API_KEY: str = ""
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Email settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Deployment Configuration
    DEPLOYMENT_MODE: DeploymentMode = DeploymentMode.SELF_HOSTED
    
    # License Server Configuration (for self-hosted deployments)
    LICENSE_SERVER_URL: str = "https://api.yourdomain.com"  # Your central license server
    LICENSE_VALIDATION_ENDPOINT: str = "/v1/licenses/validate"
    INSTANCE_ID: str = ""  # Unique identifier for self-hosted instances
    
    # SaaS Configuration
    ENABLE_USER_REGISTRATION: bool = True
    ALLOW_FREE_TIER: bool = False  # For SaaS, you might want to disable free tier
    MAX_FREE_DOCUMENTS: int = 5  # Documents per month for free tier in SaaS mode
    
    # License Configuration
    REQUIRE_LICENSE_VALIDATION: bool = True  # Can be disabled for development
    LICENSE_CACHE_TTL: int = 300  # Cache license validation for 5 minutes
    
    # Instance Information (for self-hosted tracking)
    INSTANCE_NAME: str = "Self-Hosted Instance"
    ORGANIZATION_NAME: str = ""
    ADMIN_EMAIL: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
