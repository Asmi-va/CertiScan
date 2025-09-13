from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.api import api_router
from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection
from app.middleware.auth_middleware import add_security_headers, RateLimitMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Fake Certificate Detection System API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.middleware("http")(add_security_headers)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files directory for uploaded certificates
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    
    # Perform system validation
    from app.services.startup_validation import validate_system_startup
    validation_results = await validate_system_startup()
    
    if not validation_results["system_ready"]:
        print("\n" + "="*60)
        print("⚠ SYSTEM STARTUP WARNINGS")
        print("="*60)
        for error in validation_results.get("errors", []):
            print(f"ERROR: {error}")
        for warning in validation_results.get("warnings", []):
            print(f"WARNING: {warning}")
        print("="*60)
        print("System will continue with limited functionality.")
        print("Check dataset paths and configuration.")
        print("="*60 + "\n")
    else:
        print("✓ System validation completed successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Fake Certificate Detection System API",
        "docs": "/docs",
        "version": "1.0.0"
    }