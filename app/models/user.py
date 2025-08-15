from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from enum import Enum as PyEnum
from datetime import datetime

class PlanType(str, PyEnum):
    FREE = "free"
    PREMIUM = "premium" 
    EXTRA_PREMIUM = "extra_premium"

class UserType(str, PyEnum):
    SOLO = "solo"
    ENTERPRISE = "enterprise"

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    domain = Column(String, unique=True, index=True, nullable=False)  # Company email domain
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    user_type = Column(Enum(UserType), default=UserType.SOLO)
    plan_type = Column(Enum(PlanType), default=PlanType.FREE)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    
class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class PlanLimits(Base):
    __tablename__ = "plan_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_type = Column(Enum(PlanType), unique=True, nullable=False)
    monthly_documents = Column(Integer, nullable=False)
    max_file_size_mb = Column(Float, nullable=False)
    priority_processing = Column(Boolean, default=False)
    support_level = Column(String, nullable=False)
    price_usd = Column(Float, nullable=False)

class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    job_id = Column(String, nullable=False)
    document_filename = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    processing_time_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)  # For tracking LLM usage
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")
    api_key = relationship("APIKey")
