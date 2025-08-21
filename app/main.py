from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import jobs, auth, plans, companies
from app.api import deployment_licenses as licenses
from app.core.config import settings, DeploymentMode
from dotenv import load_dotenv

load_dotenv()

# Create FastAPI app with deployment-aware configuration
app_title = (
    "Document Processing API - SaaS" 
    if settings.DEPLOYMENT_MODE == DeploymentMode.SAAS 
    else "Document Processing API - Self-Hosted"
)

app_description = (
    "Cloud-hosted document processing service with premium subscriptions"
    if settings.DEPLOYMENT_MODE == DeploymentMode.SAAS
    else "Self-hosted document processing solution with license validation"
)

app = FastAPI(
    title=app_title,
    description=app_description,
    version="2.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(licenses.router, prefix="/v1/licenses", tags=["License Management"])
app.include_router(plans.router, prefix="/v1/plans", tags=["Plans & Usage"])
app.include_router(companies.router, prefix="/v1/companies", tags=["Companies"])
app.include_router(jobs.router, prefix="/v1", tags=["Jobs"])

@app.get("/")
def read_root():
    deployment_info = {
        "mode": settings.DEPLOYMENT_MODE.value,
        "is_saas": settings.DEPLOYMENT_MODE == DeploymentMode.SAAS,
        "is_self_hosted": settings.DEPLOYMENT_MODE == DeploymentMode.SELF_HOSTED
    }
    
    if settings.DEPLOYMENT_MODE == DeploymentMode.SAAS:
        return {
            "message": "Welcome to Document Processing SaaS v2.1",
            "deployment": "Cloud-hosted service",
            "features": [
                "Cloud-hosted - no setup required",
                "Automatic updates and maintenance",
                "Premium subscriptions",
                "Free tier available" if settings.ALLOW_FREE_TIER else "Premium subscriptions only",
                "API key management",
                "Usage tracking and limits",
                "Document processing with AI"
            ],
            "docs": "/docs",
            "deployment_info": deployment_info,
            "auth_endpoints": {
                "register": "/v1/auth/register",
                "login": "/v1/auth/login",
                "profile": "/v1/auth/me",
                "company": "/v1/auth/company",
                "api_keys": "/v1/auth/api-keys"
            },
            "subscription_endpoints": {
                "pricing": "/v1/licenses/pricing",
                "purchase": "/v1/licenses/purchase",
                "status": "/v1/licenses/status",
                "my_licenses": "/v1/licenses/my-licenses"
            },
            "free_tier": {
                "enabled": settings.ALLOW_FREE_TIER,
                "max_documents": settings.MAX_FREE_DOCUMENTS if settings.ALLOW_FREE_TIER else 0
            }
        }
    else:
        return {
            "message": "Welcome to Self-Hosted Document Processing v2.1",
            "deployment": "Self-hosted instance",
            "instance_info": {
                "instance_id": settings.INSTANCE_ID or "Not configured",
                "instance_name": settings.INSTANCE_NAME,
                "organization": settings.ORGANIZATION_NAME,
                "admin_email": settings.ADMIN_EMAIL
            },
            "features": [
                "Self-hosted - full control over your data",
                "License-based access control",
                "Unlimited processing (with valid license)",
                "On-premises deployment",
                "API key management",
                "Document processing with AI"
            ],
            "docs": "/docs",
            "deployment_info": deployment_info,
            "auth_endpoints": {
                "register": "/v1/auth/register",
                "login": "/v1/auth/login",
                "profile": "/v1/auth/me",
                "company": "/v1/auth/company",
                "api_keys": "/v1/auth/api-keys"
            },
            "license_endpoints": {
                "pricing": "/v1/licenses/pricing",
                "purchase": "/v1/licenses/purchase",
                "status": "/v1/licenses/status",
                "my_licenses": "/v1/licenses/my-licenses",
                "deployment_info": "/v1/licenses/deployment-info"
            },
            "plan_endpoints": {
                "available_plans": "/v1/plans",
                "current_plan": "/v1/plans/current", 
                "usage_stats": "/v1/plans/usage",
                "upgrade": "/v1/plans/upgrade"
            },
            "company_endpoints": {
                "company_info": "/v1/companies/{company_id}",
                "company_users": "/v1/companies/{company_id}/users"
            },
            "license_server": {
                "url": settings.LICENSE_SERVER_URL or "Not configured",
                "validation_required": settings.REQUIRE_LICENSE_VALIDATION
            }
        }
