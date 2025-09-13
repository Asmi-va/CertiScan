import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from bson import ObjectId

from app.db.database import get_collection
from app.db.models import VerificationResult
from app.services.ocr import extract_text_from_image
from app.services.tamper_detection import detect_tampering
from app.services.verification import verify_certificate_data
from app.core.config import settings

router = APIRouter()

@router.post("/upload", response_model=VerificationResult)
async def upload_certificate(
    file: UploadFile = File(...),
    institution_id: Optional[str] = Form(None)
):
    """Upload and verify a certificate."""
    # Validate file type
    allowed_extensions = [".jpg", ".jpeg", ".png", ".pdf"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extract text using OCR
        extracted_data = await extract_text_from_image(file_path)
        
        # Check for tampering using multiple methods including our new ML models
        tamper_result = await detect_tampering(file_path, extracted_data)
        
        # Verify certificate data against database
        verification_result = await verify_certificate_data(
            extracted_data, 
            file_path,
            institution_id=institution_id,
            tamper_result=tamper_result
        )
        
        # Add certificate element detection results to the verification result
        from app.services.certificate_detection import detect_certificate_elements
        detection_result = await detect_certificate_elements(file_path)
        if "error" not in detection_result:
            verification_result["details"]["certificate_elements"] = detection_result["detected_elements"]
        
        # Add SSL verification results
        from app.services.ssl_verification import extract_ssl_certificate_data, verify_ssl_certificate
        ssl_data = extract_ssl_certificate_data(extracted_data)
        ssl_result = await verify_ssl_certificate(ssl_data)
        verification_result["details"]["ssl_verification"] = ssl_result["details"]
        
        # Log verification attempt
        verification_collection = await get_collection("verifications")
        verification_id = await verification_collection.insert_one({
            "cert_id": extracted_data.get("cert_id", "unknown"),
            "timestamp": datetime.utcnow(),
            "result": verification_result["status"],
            "verification_method": "upload",
            "details": verification_result["details"],
            "file_path": file_path
        })
        
        # Add verification ID to result
        verification_result["verification_id"] = str(verification_id.inserted_id)
        
        return verification_result
        
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing certificate: {str(e)}"
        )

@router.get("/verify/{cert_id}", response_model=VerificationResult)
async def verify_certificate(cert_id: str):
    """Verify a certificate by ID."""
    try:
        # Get certificate from database
        certificates_collection = await get_collection("certificates")
        certificate = await certificates_collection.find_one({"cert_id": cert_id})
        
        if not certificate:
            # Check if certificate is blacklisted
            blacklist_collection = await get_collection("blacklist")
            blacklisted = await blacklist_collection.find_one({"cert_id": cert_id})
            
            if blacklisted:
                return VerificationResult(
                    status="FLAG",
                    cert_id=cert_id,
                    details={
                        "message": "Certificate is blacklisted",
                        "reason": blacklisted.get("reason", "Unknown reason")
                    }
                )
            
            return VerificationResult(
                status="FLAG",
                cert_id=cert_id,
                details={"message": "Certificate not found in database"}
            )
        
        # Log verification attempt
        verification_collection = await get_collection("verifications")
        verification_id = await verification_collection.insert_one({
            "cert_id": cert_id,
            "timestamp": datetime.utcnow(),
            "result": "PASS",
            "verification_method": "id_lookup",
            "details": {"message": "Certificate found in database"}
        })
        
        return VerificationResult(
            status="PASS",
            cert_id=cert_id,
            details={
                "message": "Certificate verified successfully",
                "name": certificate.get("name"),
                "roll_no": certificate.get("roll_no"),
                "course": certificate.get("course"),
                "issue_date": certificate.get("issue_date")
            },
            verification_id=str(verification_id.inserted_id)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying certificate: {str(e)}"
        )