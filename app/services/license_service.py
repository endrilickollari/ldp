from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import hashlib
from app.models.user import User, License, LicenseDuration, LicenseStatus, PlanType
from app.schemas.user import LicenseCreate, LicensePurchase, LicenseStatusResponse
import json

class LicenseService:
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def get_license_pricing() -> Dict[str, Dict[str, float]]:
        """Get pricing for different license types"""
        return {
            PlanType.PREMIUM.value: {
                LicenseDuration.MONTHLY.value: 29.99,
                LicenseDuration.SIX_MONTHS.value: 149.99,
                LicenseDuration.YEARLY.value: 299.99,
                LicenseDuration.LIFETIME.value: 999.99
            },
            PlanType.EXTRA_PREMIUM.value: {
                LicenseDuration.MONTHLY.value: 59.99,
                LicenseDuration.SIX_MONTHS.value: 299.99,
                LicenseDuration.YEARLY.value: 599.99,
                LicenseDuration.LIFETIME.value: 1999.99
            }
        }
    
    def generate_license_key(self, user_id: int, plan_type: PlanType) -> str:
        """Generate a unique license key"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        random_part = secrets.token_hex(8)
        data = f"{user_id}:{plan_type.value}:{timestamp}:{random_part}"
        hash_part = hashlib.sha256(data.encode()).hexdigest()[:12].upper()
        
        # Format: PLAN-XXXX-XXXX-XXXX
        plan_prefix = "PREM" if plan_type == PlanType.PREMIUM else "EXTR"
        formatted_key = f"{plan_prefix}-{hash_part[:4]}-{hash_part[4:8]}-{hash_part[8:12]}"
        
        # Ensure uniqueness
        existing = self.db.query(License).filter(License.license_key == formatted_key).first()
        if existing:
            return self.generate_license_key(user_id, plan_type)  # Recursively retry
        
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
    
    def create_license(self, user: User, license_data: LicensePurchase) -> License:
        """Create a new license for a user"""
        pricing = self.get_license_pricing()
        price = pricing[license_data.plan_type.value][license_data.duration.value]
        
        license_key = self.generate_license_key(getattr(user, "id"), license_data.plan_type)
        expiry_date = self.calculate_expiry_date(license_data.duration)
        
        new_license = License(
            user_id=getattr(user, "id"),
            license_key=license_key,
            plan_type=license_data.plan_type,
            duration=license_data.duration,
            status=LicenseStatus.PENDING,  # Will be activated after payment confirmation
            price_paid=price,
            currency="USD",
            expires_at=expiry_date,
            payment_id=license_data.payment_id,
            payment_method=license_data.payment_method
        )
        
        self.db.add(new_license)
        self.db.commit()
        self.db.refresh(new_license)
        
        return new_license
    
    def activate_license(self, license_key: str, payment_confirmed: bool = True) -> Optional[License]:
        """Activate a license after payment confirmation"""
        license_obj = self.db.query(License).filter(
            License.license_key == license_key,
            License.status == LicenseStatus.PENDING
        ).first()
        
        if not license_obj:
            return None
        
        if payment_confirmed:
            setattr(license_obj, "status", LicenseStatus.ACTIVE)
            setattr(license_obj, "activated_at", datetime.utcnow())
            
            # Update user's plan type
            user = self.db.query(User).filter(User.id == license_obj.user_id).first()
            if user:
                setattr(user, "plan_type", license_obj.plan_type)
            
            self.db.commit()
            self.db.refresh(license_obj)
        
        return license_obj
    
    def get_user_active_license(self, user_id: int) -> Optional[License]:
        """Get user's current active license"""
        return self.db.query(License).filter(
            License.user_id == user_id,
            License.status == LicenseStatus.ACTIVE,
            # Check if not expired (or lifetime)
            (License.expires_at.is_(None)) | (License.expires_at > datetime.utcnow())
        ).order_by(License.created_at.desc()).first()
    
    def check_license_validity(self, user: User) -> LicenseStatusResponse:
        """Check if user has a valid license"""
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
                # Mark as expired
                setattr(active_license, "status", LicenseStatus.EXPIRED)
                self.db.commit()
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
    
    def suspend_license(self, license_key: str, reason: Optional[str] = None) -> Optional[License]:
        """Suspend a license"""
        license_obj = self.db.query(License).filter(
            License.license_key == license_key,
            License.status == LicenseStatus.ACTIVE
        ).first()
        
        if not license_obj:
            return None
        
        setattr(license_obj, "status", LicenseStatus.SUSPENDED)
        setattr(license_obj, "suspended_at", datetime.utcnow())
        
        if reason:
            extra_data_str = getattr(license_obj, "extra_data") or "{}"
            extra_data = json.loads(extra_data_str)
            extra_data["suspension_reason"] = reason
            extra_data["suspended_at"] = datetime.utcnow().isoformat()
            setattr(license_obj, "extra_data", json.dumps(extra_data))
        
        self.db.commit()
        self.db.refresh(license_obj)
        
        return license_obj
    
    def get_user_licenses(self, user_id: int) -> list[License]:
        """Get all licenses for a user"""
        return self.db.query(License).filter(
            License.user_id == user_id
        ).order_by(License.created_at.desc()).all()
    
    def is_license_required_for_endpoint(self, endpoint_path: str) -> bool:
        """Determine if an endpoint requires a valid license"""
        # Define endpoints that don't require licenses
        public_endpoints = {
            "/",
            "/docs",
            "/openapi.json",
            "/v1/auth/register",
            "/v1/auth/login",
            "/v1/licenses/pricing",
            "/v1/licenses/purchase",
            "/v1/licenses/activate",
        }
        
        # Allow health check and static endpoints
        if endpoint_path in public_endpoints:
            return False
        
        if endpoint_path.startswith("/v1/auth/") and endpoint_path in [
            "/v1/auth/register", "/v1/auth/login"
        ]:
            return False
        
        # All other endpoints require valid license
        return True
