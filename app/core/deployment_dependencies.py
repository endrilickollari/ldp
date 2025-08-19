from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.auth import verify_token
from app.models.user import User, APIKey
from app.schemas.user import TokenData
from app.services.deployment_license_service import DeploymentAwareLicenseService
from app.core.config import settings, DeploymentMode
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
    if not getattr(current_user, "is_active"):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_user_from_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tuple[User, Optional[APIKey]]:
    """Get user from API key or JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
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
                if user and getattr(user, "is_active"):
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

async def get_deployment_aware_licensed_user(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """Get current user and validate they have a valid license based on deployment mode"""
    
    license_service = DeploymentAwareLicenseService(db)
    
    # Check if this endpoint requires a license
    if not license_service.is_license_required_for_endpoint(request.url.path):
        return current_user
    
    # In SaaS mode with free tier, allow limited access
    if (license_service.is_saas_mode() and 
        settings.ALLOW_FREE_TIER and 
        request.url.path in ["/v1/jobs"] and
        request.method == "POST"):
        
        # Check if user has used their free tier allocation
        from app.services.user_service import UserService
        user_service = UserService(db)
        usage_stats = user_service.get_usage_stats(current_user)
        
        if usage_stats.current_month_usage < settings.MAX_FREE_DOCUMENTS:
            # Allow free tier usage
            return current_user
    
    # Check if user has a valid license
    license_status = await license_service.check_license_validity(current_user)
    
    if not license_status.has_valid_license:
        deployment_message = (
            "This SaaS feature requires a premium subscription. Upgrade to continue."
            if license_service.is_saas_mode() 
            else "This self-hosted instance requires a valid license. Please contact your administrator."
        )
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Valid license required",
                "message": deployment_message,
                "license_status": "expired" if license_status.current_license else "none",
                "deployment_mode": settings.DEPLOYMENT_MODE.value,
                "purchase_url": "/v1/licenses/pricing" if license_service.is_saas_mode() else None,
                "contact_admin": license_service.is_self_hosted_mode()
            }
        )
    
    return current_user

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ldp_{secrets.token_urlsafe(32)}"
