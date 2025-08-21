from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.auth import verify_token
from app.models.user import User, APIKey
from app.schemas.user import TokenData
from typing import Optional, Tuple
import secrets

security = HTTPBearer(auto_error=False)

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
    
    if credentials is None:
        raise credentials_exception
    
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
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tuple[User, Optional[APIKey]]:
    """Get user from API key or JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )
    
    # Try API key from X-API-Key header first
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        api_key = db.query(APIKey).filter(
            APIKey.api_key == api_key_header,
            APIKey.is_active == True
        ).first()
        if api_key:
            user = db.query(User).filter(
                User.id == api_key.user_id,
                User.is_active == True
            ).first()
            if user:
                return user, api_key
        raise credentials_exception
    
    # Try JWT token
    if credentials:
        token = credentials.credentials
        payload = verify_token(token)
        if payload:
            email = payload.get("sub")
            if email:
                user = db.query(User).filter(User.email == email).first()
                if user and bool(user.is_active):  # type: ignore
                    return user, None
        
        # Try API key from Bearer token as fallback
        api_key = db.query(APIKey).filter(
            APIKey.api_key == token,
            APIKey.is_active == True
        ).first()
        if api_key:
            user = db.query(User).filter(
                User.id == api_key.user_id,
                User.is_active == True
            ).first()
            if user:
                return user, api_key
    
    raise credentials_exception

async def get_licensed_user(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """Get current user and validate they have a valid license for the endpoint"""
    from app.services.license_service import LicenseService
    
    license_service = LicenseService(db)
    
    # Check if this endpoint requires a license
    if not license_service.is_license_required_for_endpoint(request.url.path):
        return current_user
    
    # Check if user has a valid license
    license_status = license_service.check_license_validity(current_user)
    
    if not license_status.has_valid_license:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Valid license required",
                "message": "This feature requires a valid license. Please purchase a license to continue.",
                "license_status": "expired" if license_status.current_license else "none",
                "purchase_url": "/v1/licenses/pricing"
            }
        )
    
    return current_user

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ldp_{secrets.token_urlsafe(32)}"
