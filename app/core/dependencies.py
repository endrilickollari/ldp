from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.auth import verify_token
from app.models.user import User, APIKey
from app.schemas.user import TokenData
from typing import Optional, Tuple
import secrets

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise credentials_exception
    
    email = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not bool(current_user.is_active):  # type: ignore
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_user_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tuple[User, Optional[APIKey]]:
    """Get user from API key or JWT token"""
    token = credentials.credentials
    
    # First try to get user from JWT token
    payload = verify_token(token)
    if payload:
        email = payload.get("sub")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user and bool(user.is_active):  # type: ignore
                return user, None
    
    # If not JWT, try API key
    api_key = db.query(APIKey).filter(APIKey.api_key == token).filter(APIKey.is_active == True).first()
    if api_key:
        user = db.query(User).filter(User.id == api_key.user_id).filter(User.is_active == True).first()
        if user:
            return user, api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ldp_{secrets.token_urlsafe(32)}"
