from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import secrets
import hashlib
import httpx
import json
from app.models.user import User, License, LicenseDuration, LicenseStatus, PlanType
from app.schemas.user import LicenseCreate, LicensePurchase, LicenseStatusResponse
from app.core.config import settings, DeploymentMode
import logging

logger = logging.getLogger(__name__)

class DeploymentAwareLicenseService:
    def __init__(self, db: Session):
        self.db = db
        self.deployment_mode = settings.DEPLOYMENT_MODE
    
    def is_saas_mode(self) -> bool:
        """Check if running in SaaS mode"""
        return self.deployment_mode == DeploymentMode.SAAS
    
    def is_self_hosted_mode(self) -> bool:
        """Check if running in self-hosted mode"""
        return self.deployment_mode == DeploymentMode.SELF_HOSTED
    
    @staticmethod
    def get_license_pricing() -> Dict[str, Dict[str, float]]:
        """Get pricing for different license types based on deployment mode"""
        if settings.DEPLOYMENT_MODE == DeploymentMode.SAAS:
            # SaaS pricing - subscription based
            return {
                PlanType.PREMIUM.value: {
                    LicenseDuration.MONTHLY.value: 29.99,
                    LicenseDuration.SIX_MONTHS.value: 149.99,
                    LicenseDuration.YEARLY.value: 299.99,
                },
                PlanType.EXTRA_PREMIUM.value: {
                    LicenseDuration.MONTHLY.value: 59.99,
                    LicenseDuration.SIX_MONTHS.value: 299.99,
                    LicenseDuration.YEARLY.value: 599.99,
                }
            }
        else:
            # Self-hosted pricing - includes lifetime options
            return {
                PlanType.PREMIUM.value: {
                    LicenseDuration.MONTHLY.value: 99.99,
                    LicenseDuration.SIX_MONTHS.value: 499.99,
                    LicenseDuration.YEARLY.value: 899.99,
                    LicenseDuration.LIFETIME.value: 2999.99
                },
                PlanType.EXTRA_PREMIUM.value: {
                    LicenseDuration.MONTHLY.value: 199.99,
                    LicenseDuration.SIX_MONTHS.value: 999.99,
                    LicenseDuration.YEARLY.value: 1799.99,
                    LicenseDuration.LIFETIME.value: 4999.99
                }
            }
    
    def generate_license_key(self, user_id: int, plan_type: PlanType) -> str:
        """Generate a license key with deployment mode prefix"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        random_part = secrets.token_hex(8)
        instance_part = settings.INSTANCE_ID[:4] if settings.INSTANCE_ID else "0000"
        
        data = f"{user_id}:{plan_type.value}:{timestamp}:{random_part}:{instance_part}"
        hash_part = hashlib.sha256(data.encode()).hexdigest()[:12].upper()
        
        # Different prefixes based on deployment mode and plan
        if self.is_saas_mode():
            plan_prefix = "SAAS-PREM" if plan_type == PlanType.PREMIUM else "SAAS-EXTR"
        else:
            plan_prefix = "HOST-PREM" if plan_type == PlanType.PREMIUM else "HOST-EXTR"
        
        formatted_key = f"{plan_prefix}-{hash_part[:4]}-{hash_part[4:8]}-{hash_part[8:12]}"
        
        # Ensure uniqueness
        existing = self.db.query(License).filter(License.license_key == formatted_key).first()
        if existing:
            return self.generate_license_key(user_id, plan_type)
        
        return formatted_key
    
    def calculate_expiry_date(self, duration: LicenseDuration, from_date: Optional[datetime] = None) -> Optional[datetime]:
        """Calculate license expiry date based on duration"""
        if duration == LicenseDuration.LIFETIME:
            return None
        
        start_date = from_date or datetime.utcnow()
        
        if duration == LicenseDuration.MONTHLY:
            return start_date + timedelta(days=30)
        elif duration == LicenseDuration.SIX_MONTHS:
            return start_date + timedelta(days=180)
        elif duration == LicenseDuration.YEARLY:
            return start_date + timedelta(days=365)
        
        return None
    
    async def validate_self_hosted_license(self, license_key: str) -> Dict[str, Any]:
        """Validate license with central license server for self-hosted deployments"""
        if not settings.LICENSE_SERVER_URL:
            logger.warning("License server URL not configured for self-hosted validation")
            return {"valid": False, "reason": "License server not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.LICENSE_SERVER_URL}{settings.LICENSE_VALIDATION_ENDPOINT}/{license_key}",
                    params={
                        "instance_id": settings.INSTANCE_ID,
                        "instance_name": settings.INSTANCE_NAME
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "valid": False,
                        "reason": f"License server returned {response.status_code}"
                    }
        except Exception as e:
            logger.error(f"Failed to validate license with server: {e}")
            return {
                "valid": False,
                "reason": "License server unreachable"
            }
    
    def create_license(self, user: User, license_data: LicensePurchase) -> License:
        """Create a new license based on deployment mode"""
        pricing = self.get_license_pricing()
        price = pricing[license_data.plan_type.value][license_data.duration.value]
        
        license_key = self.generate_license_key(getattr(user, "id"), license_data.plan_type)
        expiry_date = self.calculate_expiry_date(license_data.duration)
        
        # In SaaS mode, licenses are typically activated immediately
        initial_status = LicenseStatus.ACTIVE if self.is_saas_mode() else LicenseStatus.PENDING
        activated_at = datetime.utcnow() if self.is_saas_mode() else None
        
        new_license = License(
            user_id=user.id,
            license_key=license_key,
            plan_type=license_data.plan_type,
            duration=license_data.duration,
            status=initial_status,
            price_paid=price,
            currency="USD",
            expires_at=expiry_date,
            activated_at=activated_at,
            payment_id=license_data.payment_id,
            payment_method=license_data.payment_method
        )
        
        self.db.add(new_license)
        self.db.commit()
        self.db.refresh(new_license)
        
        # Update user's plan type if activated
        if initial_status == LicenseStatus.ACTIVE:
            setattr(user, "plan_type", license_data.plan_type)
            self.db.commit()
        
        return new_license
    
    def get_user_active_license(self, user_id: int) -> Optional[License]:
        """Get user's current active license"""
        return self.db.query(License).filter(
            License.user_id == user_id,
            License.status == LicenseStatus.ACTIVE,
            # Check if not expired (or lifetime)
            (License.expires_at.is_(None)) | (License.expires_at > datetime.utcnow())
        ).order_by(License.created_at.desc()).first()
    
    async def check_license_validity(self, user: User) -> LicenseStatusResponse:
        """Check if user has a valid license based on deployment mode"""
        if self.is_saas_mode():
            # In SaaS mode, check local database
            return self._check_local_license_validity(user)
        else:
            # In self-hosted mode, validate with central server if configured
            local_license = self.get_user_active_license(getattr(user, "id"))
            if not local_license:
                return LicenseStatusResponse(
                    has_valid_license=False,
                    current_license=None,
                    days_until_expiry=None,
                    license_type=None
                )
            
            # Validate with central server
            validation_result = await self.validate_self_hosted_license(getattr(local_license, "license_key"))
            
            if validation_result.get("valid", False):
                return self._check_local_license_validity(user)
            else:
                # License invalid according to central server
                return LicenseStatusResponse(
                    has_valid_license=False,
                    current_license=local_license,
                    days_until_expiry=None,
                    license_type="invalid"
                )
    
    def _check_local_license_validity(self, user: User) -> LicenseStatusResponse:
        """Check local license validity"""
        active_license = self.get_user_active_license(getattr(user, "id"))
        
        if not active_license:
            return LicenseStatusResponse(
                has_valid_license=False,
                current_license=None,
                days_until_expiry=None,
                license_type=None
            )
        
        days_until_expiry = None
        expires_at = getattr(active_license, "expires_at")
        if expires_at:
            days_until_expiry = (expires_at - datetime.utcnow()).days
            
            # Check if expired
            if days_until_expiry < 0:
                return LicenseStatusResponse(
                    has_valid_license=False,
                    current_license=active_license,
                    days_until_expiry=days_until_expiry,
                    license_type=active_license.duration.value
                )
        
        return LicenseStatusResponse(
            has_valid_license=True,
            current_license=active_license,
            days_until_expiry=days_until_expiry,
            license_type=active_license.duration.value
        )
    
    def is_license_required_for_endpoint(self, endpoint_path: str) -> bool:
        """Determine if an endpoint requires a valid license based on deployment mode"""
        # Public endpoints that never require licenses
        public_endpoints = {
            "/",
            "/docs",
            "/openapi.json",
            "/v1/auth/register",
            "/v1/auth/login",
            "/v1/licenses/pricing",
        }
        
        if endpoint_path in public_endpoints:
            return False
        
        # In SaaS mode, allow some endpoints for free tier
        if self.is_saas_mode() and settings.ALLOW_FREE_TIER:
            free_tier_endpoints = {
                "/v1/plans/plans",
                "/v1/plans/current-plan",
                "/v1/auth/me",
                "/v1/licenses/status"
            }
            if endpoint_path in free_tier_endpoints:
                return False
        
        # Purchase and activation endpoints
        if endpoint_path in ["/v1/licenses/purchase", "/v1/licenses/my-licenses", "/v1/licenses/status"]:
            return False
        
        # Admin endpoints (you might want to add proper admin authentication)
        if endpoint_path.startswith("/v1/licenses/activate/") or endpoint_path.startswith("/v1/licenses/suspend/"):
            return False
        
        # All other endpoints require valid license
        return True
    
    def get_deployment_info(self) -> Dict[str, Any]:
        """Get information about current deployment"""
        return {
            "deployment_mode": self.deployment_mode.value,
            "instance_id": settings.INSTANCE_ID if self.is_self_hosted_mode() else None,
            "instance_name": settings.INSTANCE_NAME if self.is_self_hosted_mode() else None,
            "organization": settings.ORGANIZATION_NAME if self.is_self_hosted_mode() else None,
            "license_server": settings.LICENSE_SERVER_URL if self.is_self_hosted_mode() else None,
            "allows_free_tier": settings.ALLOW_FREE_TIER if self.is_saas_mode() else False,
            "max_free_documents": settings.MAX_FREE_DOCUMENTS if self.is_saas_mode() and settings.ALLOW_FREE_TIER else 0
        }
