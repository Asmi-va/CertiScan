from fastapi import APIRouter

from app.api.endpoints import certificate, institution, admin, auth, upload, tamper_test, verification, fraud_detection

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(certificate.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(institution.router, prefix="/institutions", tags=["institutions"])
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
api_router.include_router(fraud_detection.router, prefix="/fraud-detection", tags=["fraud-detection"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(tamper_test.router, prefix="/tamper", tags=["tamper-detection"])