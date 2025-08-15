from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import jobs, auth, plans
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Large Document Processing API",
    description="An API to process large Excel and PDF files using OCR and LLMs with authentication and user plans.",
    version="2.0.0"
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
app.include_router(plans.router, prefix="/v1/plans", tags=["Plans & Usage"])
app.include_router(jobs.router, prefix="/v1", tags=["Jobs"])

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Document Processing API v2.0",
        "features": [
            "User authentication with JWT",
            "Multiple subscription plans", 
            "API key management",
            "Usage tracking and limits",
            "Document processing with AI"
        ],
        "docs": "/docs",
        "auth_endpoints": {
            "register": "/v1/auth/register",
            "login": "/v1/auth/login",
            "profile": "/v1/auth/me",
            "api_keys": "/v1/auth/api-keys"
        },
        "plan_endpoints": {
            "available_plans": "/v1/plans/plans",
            "current_plan": "/v1/plans/current-plan",
            "usage_stats": "/v1/plans/usage"
        }
    }
