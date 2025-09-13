"""
Institution API endpoints - Handle institution registration, certificate management, and verification
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime

from ...services.institution_service import InstitutionService
from ...services.auth_service import AuthService
from ...db.models import (
    Institution, Certificate, InstitutionCreate, InstitutionResponse,
    CertificateCreate, CertificateResponse, UserRole, InstitutionType, DegreeType
)
from ...core.security import get_current_user
from ...utils.exceptions import (
    InstitutionNotFoundError, CertificateNotFoundError,
    ValidationError, DuplicateError, UnauthorizedError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/institutions", tags=["institutions"])
security = HTTPBearer()

# Initialize services
institution_service = InstitutionService()
auth_service = AuthService()

@router.post("/register", response_model=InstitutionResponse)
async def register_institution(
    institution_data: InstitutionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Register a new institution"""
    try:
        # Only admin users can register institutions
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to register institution")
        
        institution = await institution_service.register_institution(
            institution_data.model_dump(),
            current_user["user_id"]
        )
        
        return InstitutionResponse(**institution.model_dump())
        
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering institution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get institution details"""
    try:
        institution = await institution_service.get_institution(institution_id)
        
        # Check if user has permission to view this institution
        if (current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT] and 
            current_user["user_id"] not in institution.admin_users):
            # Return limited public information
            return InstitutionResponse(
                institution_id=institution.institution_id,
                name=institution.name,
                type=institution.type,
                address={"city": institution.address.get("city", ""), "state": institution.address.get("state", "")},
                contact_info={"website": institution.contact_info.get("website", "")},
                accreditation_status=institution.accreditation_status,
                is_active=institution.is_active,
                verification_enabled=institution.verification_enabled,
                total_certificates=institution.total_certificates,
                created_at=institution.created_at
            )
        
        return InstitutionResponse(**institution.model_dump())
        
    except InstitutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: str,
    update_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update institution information"""
    try:
        institution = await institution_service.update_institution(
            institution_id,
            update_data,
            current_user["user_id"]
        )
        
        return InstitutionResponse(**institution.model_dump())
        
    except InstitutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{institution_id}/certificates", response_model=CertificateResponse)
async def add_certificate(
    institution_id: str,
    certificate_data: CertificateCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a single certificate record"""
    try:
        # Ensure institution_id matches
        cert_data = certificate_data.model_dump()
        cert_data["institution_id"] = institution_id
        
        certificate = await institution_service.add_certificate_record(
            cert_data,
            current_user["user_id"]
        )
        
        return CertificateResponse(**certificate.model_dump())
        
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding certificate for institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{institution_id}/certificates/bulk-upload")
async def bulk_upload_certificates(
    institution_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Bulk upload certificates from CSV file"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=422, detail="Only CSV files are supported")
        
        # Read CSV content
        csv_content = await file.read()
        csv_data = csv_content.decode('utf-8')
        
        # Process bulk upload
        results = await institution_service.bulk_upload_certificates(
            institution_id,
            csv_data,
            current_user["user_id"]
        )
        
        return {
            "message": "Bulk upload completed",
            "results": results
        }
        
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error in bulk upload for institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{institution_id}/certificates")
async def get_institution_certificates(
    institution_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    degree_type: Optional[DegreeType] = Query(None),
    graduation_year: Optional[int] = Query(None),
    verification_status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get certificates for an institution with pagination and filtering"""
    try:
        filters = {}
        if degree_type:
            filters["degree_type"] = degree_type
        if graduation_year:
            filters["graduation_year"] = graduation_year
        if verification_status:
            filters["verification_status"] = verification_status
        
        result = await institution_service.get_institution_certificates(
            institution_id,
            current_user["user_id"],
            limit=limit,
            offset=offset,
            filters=filters if filters else None
        )
        
        # Convert certificates to response format
        certificates = [CertificateResponse(**cert.model_dump()) for cert in result["certificates"]]
        
        return {
            "certificates": certificates,
            "pagination": {
                "total_count": result["total_count"],
                "limit": result["limit"],
                "offset": result["offset"],
                "has_more": result["has_more"]
            }
        }
        
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InstitutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting certificates for institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{institution_id}/statistics")
async def get_institution_statistics(
    institution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get statistics for an institution"""
    try:
        statistics = await institution_service.get_institution_statistics(
            institution_id,
            current_user["user_id"]
        )
        
        return statistics
        
    except UnauthorizedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InstitutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting statistics for institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{institution_id}/verify-certificate")
async def verify_certificate_against_institution(
    institution_id: str,
    certificate_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Verify a certificate against institution records"""
    try:
        result = await institution_service.verify_certificate_against_institution(
            certificate_id,
            institution_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error verifying certificate {certificate_id} against institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cross-reference")
async def cross_reference_certificate(
    extracted_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Cross-reference extracted certificate data against all institution records"""
    try:
        result = await institution_service.cross_reference_certificate(extracted_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error cross-referencing certificate: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/")
async def list_institutions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    institution_type: Optional[InstitutionType] = Query(None),
    state: Optional[str] = Query(None),
    active_only: bool = Query(True),
    current_user: dict = Depends(get_current_user)
):
    """List institutions with pagination and filtering"""
    try:
        # Build query filters
        filters = {}
        if institution_type:
            filters["type"] = institution_type
        if state:
            filters["address.state"] = state
        if active_only:
            filters["is_active"] = True
        
        # Get institutions from database
        db = institution_service.db
        cursor = db.institutions.find(filters).skip(offset).limit(limit)
        
        institutions = []
        async for inst_data in cursor:
            institution = Institution(**inst_data)
            # Return limited public information for non-admin users
            if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
                institutions.append(InstitutionResponse(
                    institution_id=institution.institution_id,
                    name=institution.name,
                    type=institution.type,
                    address={"city": institution.address.get("city", ""), "state": institution.address.get("state", "")},
                    contact_info={"website": institution.contact_info.get("website", "")},
                    accreditation_status=institution.accreditation_status,
                    is_active=institution.is_active,
                    verification_enabled=institution.verification_enabled,
                    total_certificates=institution.total_certificates,
                    created_at=institution.created_at
                ))
            else:
                institutions.append(InstitutionResponse(**institution.model_dump()))
        
        # Get total count
        total_count = await db.institutions.count_documents(filters)
        
        return {
            "institutions": institutions,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing institutions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# CSV template endpoint
@router.get("/{institution_id}/certificate-template")
async def get_certificate_csv_template(
    institution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get CSV template for bulk certificate upload"""
    try:
        # Verify user has permission
        institution = await institution_service.get_institution(institution_id)
        if current_user["user_id"] not in institution.admin_users:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        template = {
            "csv_headers": [
                "certificate_id",
                "student_name", 
                "roll_number",
                "course_name",
                "degree_type",
                "graduation_date",
                "issue_date",
                "certificate_number",
                "grades",
                "specialization",
                "duration"
            ],
            "sample_data": [
                {
                    "certificate_id": f"{institution_id}_CERT_001",
                    "student_name": "John Doe",
                    "roll_number": "2020001",
                    "course_name": "Bachelor of Computer Science",
                    "degree_type": "BACHELOR",
                    "graduation_date": "2024-06-15",
                    "issue_date": "2024-07-01",
                    "certificate_number": "CERT001/2024",
                    "grades": '{"overall": "A", "cgpa": "8.5"}',
                    "specialization": "Software Engineering",
                    "duration": "4 years"
                }
            ],
            "field_descriptions": {
                "certificate_id": "Unique identifier for the certificate (optional, will be auto-generated)",
                "student_name": "Full name of the student (required)",
                "roll_number": "Student roll number or ID (required)",
                "course_name": "Name of the course or program (required)",
                "degree_type": "Type of degree: BACHELOR, MASTER, DOCTORATE, DIPLOMA, CERTIFICATE, PROFESSIONAL (required)",
                "graduation_date": "Date of graduation in YYYY-MM-DD format (required)",
                "issue_date": "Date when certificate was issued in YYYY-MM-DD format (optional, defaults to graduation_date)",
                "certificate_number": "Official certificate number (required)",
                "grades": "JSON string with grade information (optional)",
                "specialization": "Area of specialization (optional)",
                "duration": "Course duration (optional)"
            }
        }
        
        return template
        
    except InstitutionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting CSV template for institution {institution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")