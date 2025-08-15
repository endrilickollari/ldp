from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import PlanType

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    plan_type: PlanType
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserInDB(User):
    hashed_password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: User

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    plan_type: Optional[PlanType] = None

# API Key Schemas
class APIKeyBase(BaseModel):
    key_name: str

class APIKeyCreate(APIKeyBase):
    pass

class APIKey(APIKeyBase):
    id: int
    api_key: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Plan Schemas
class PlanLimitsBase(BaseModel):
    plan_type: PlanType
    monthly_documents: int
    max_file_size_mb: float
    priority_processing: bool
    support_level: str
    price_usd: float

class PlanLimits(PlanLimitsBase):
    id: int
    
    class Config:
        from_attributes = True

# Usage Schemas
class UsageStatsBase(BaseModel):
    documents_processed: int
    current_month_usage: int
    remaining_documents: int
    plan_limit: int

class UsageStats(UsageStatsBase):
    pass
