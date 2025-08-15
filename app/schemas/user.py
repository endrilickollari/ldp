from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional, Any, Dict
from datetime import datetime
from app.models.user import PlanType, UserType

# Company Schemas
class CompanyBase(BaseModel):
    name: str
    domain: str
    description: Optional[str] = None
    website: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    user_type: UserType = UserType.SOLO

class UserCreate(UserBase):
    password: str
    company_name: Optional[str] = None  # For enterprise users
    company_domain: Optional[str] = None  # For enterprise users
    
    @model_validator(mode='after')
    def validate_enterprise_fields(self) -> 'UserCreate':
        if self.user_type == UserType.ENTERPRISE:
            if not self.company_name or not self.company_domain:
                raise ValueError('Company name and domain are required for enterprise users')
            
            # Check if email domain matches company domain
            email_domain = self.email.split('@')[1]
            if email_domain != self.company_domain:
                raise ValueError('Email domain must match company domain for enterprise users')
        
        return self

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    plan_type: PlanType
    company_id: Optional[int] = None
    company: Optional[Company] = None
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
    user_type: Optional[UserType] = None

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
