"""
Comprehensive Verification Service - Orchestrates multi-layer certificate verification
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib
import json

from ..db.database import get_database
from ..db.models import (
    VerificationRecord, VerificationStatus, Certificate, Institution,
    UserRole, DegreeType
)
from ..services.ocr import EnhancedOCRService
from ..services.tamper_detection import detect_tampering
from ..services.institution_service import InstitutionService
from ..services.upload_service import FileUploadService
from ..core.config import settings
from ..utils.exceptions import (
    ValidationError, ProcessingError, OCRError, 
    AIModelError, InstitutionNotFoundError
)

logger = logging.getLogger(__name__)

class VerificationService:
    """Comprehensive certificate verification service orchestrating all verification layers"""
    
    def __init__(self):
        self.db = None
        self.verification_records_collection = None
        
        # Initialize component services
        self.ocr_service = EnhancedOCRService()
        self.tamper_detection_func = detect_tampering
        self.institution_service = InstitutionService()
        self.upload_service = FileUploadService()
        
        # Verification configuration
        self.verification_config = {
            "weights": {
                "ocr_confidence": 0.15,
                "tamper_detection": 0.35,
                "institutional_verification": 0.40,
                "certificate_numbering": 0.10
            },
            "thresholds": {
                "authentic": 0.85,
                "likely_authentic": 0.70,
                "suspicious": 0.50,
                "forged": 0.30
            },
            "timeout_seconds": 120,
            "max_retries": 3
        }
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = await get_database()
            self.verification_records_collection = self.db.verification_records
    
    async def verify_certificate(
        self,
        file_path: str,
        requester_id: str,
        requester_type: UserRole,
        purpose: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive certificate verification workflow
        
        Args:
            file_path: Path to certificate image/PDF
            requester_id: ID of user requesting verification
            requester_type: Type of requester (EMPLOYER, GOVERNMENT, etc.)
            purpose: Purpose of verification
            metadata: Additional metadata
            
        Returns:
            Complete verification result with all analysis layers
        """
        verification_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Starting verification {verification_id} for file: {file_path}")
        
        try:
            await self._ensure_db_connection()
            
            # Initialize verification record
            verification_record = await self._initialize_verification_record(
                verification_id, requester_id, requester_type, purpose, metadata
            )
            
            # Step 1: File preprocessing and validation
            preprocessing_result = await self._preprocess_file(file_path)
            
            # Step 2: OCR extraction
            ocr_result = await self._perform_ocr_extraction(
                preprocessing_result["processed_file_path"]
            )
            
            # Step 3: Tamper detection
            tamper_result = await self._perform_tamper_detection(
                preprocessing_result["processed_file_path"]
            )
            
            # Step 4: Institutional verification
            institutional_result = await self._perform_institutional_verification(
                ocr_result["extracted_data"]
            )
            
            # Step 5: Certificate number validation
            numbering_result = await self._validate_certificate_numbering(
                ocr_result["extracted_data"], institutional_result
            )
            
            # Step 6: Duplicate detection
            duplicate_result = await self._check_for_duplicates(
                ocr_result["extracted_data"], preprocessing_result["file_hash"]
            )
            
            # Step 7: Combine all results
            final_result = await self._combine_verification_results(
                verification_id,
                {
                    "preprocessing": preprocessing_result,
                    "ocr": ocr_result,
                    "tamper_detection": tamper_result,
                    "institutional": institutional_result,
                    "numbering": numbering_result,
                    "duplicate_check": duplicate_result
                }
            )
            
            # Step 8: Generate recommendations
            recommendations = await self._generate_recommendations(final_result)
            final_result["recommendations"] = recommendations
            
            # Step 9: Update verification record
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._update_verification_record(
                verification_record, final_result, processing_time
            )
            
            logger.info(f"Verification {verification_id} completed in {processing_time:.2f}s")
            return final_result
            
        except Exception as e:
            logger.error(f"Verification {verification_id} failed: {str(e)}")
            
            # Record failure
            error_result = {
                "verification_id": verification_id,
                "status": VerificationStatus.INVALID,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                },
                "processing_time": (datetime.utcnow() - start_time).total_seconds()
            }
            
            return error_result
    
    async def verify_certificate_by_id(
        self,
        certificate_id: str,
        requester_id: str,
        requester_type: UserRole
    ) -> Dict[str, Any]:
        """
        Verify a certificate by its ID (for certificates already in the system)
        """
        try:
            await self._ensure_db_connection()
            
            # Get certificate from database
            cert_data = await self.db.certificates.find_one({
                "certificate_id": certificate_id
            })
            
            if not cert_data:
                return {
                    "verification_id": str(uuid.uuid4()),
                    "status": VerificationStatus.INVALID,
                    "message": "Certificate not found in system",
                    "confidence": 0.0
                }
            
            certificate = Certificate(**cert_data)
            
            # Perform institutional verification
            institutional_result = await self.institution_service.verify_certificate_against_institution(
                certificate_id, certificate.institution_id
            )
            
            # Check for any tamper flags or issues
            verification_status = VerificationStatus.VERIFIED
            confidence = 1.0
            
            if certificate.tamper_flags:
                verification_status = VerificationStatus.SUSPICIOUS
                confidence = 0.7
            
            if not institutional_result["verified"]:
                verification_status = VerificationStatus.INVALID
                confidence = 0.0
            
            return {
                "verification_id": str(uuid.uuid4()),
                "certificate_id": certificate_id,
                "status": verification_status,
                "confidence": confidence,
                "certificate_data": {
                    "student_name": certificate.student_name,
                    "roll_number": certificate.roll_number,
                    "course_name": certificate.course_name,
                    "degree_type": certificate.degree_type,
                    "graduation_date": certificate.graduation_date.isoformat(),
                    "institution_id": certificate.institution_id,
                    "certificate_number": certificate.certificate_number
                },
                "institutional_verification": institutional_result,
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Certificate ID verification failed: {str(e)}")
            raise ProcessingError(f"Failed to verify certificate by ID: {str(e)}")
    
    async def batch_verify_certificates(
        self,
        file_paths: List[str],
        requester_id: str,
        requester_type: UserRole,
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Batch verification of multiple certificates
        """
        batch_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Starting batch verification {batch_id} for {len(file_paths)} files")
        
        results = {
            "batch_id": batch_id,
            "total_files": len(file_paths),
            "completed": 0,
            "failed": 0,
            "results": [],
            "summary": {
                "authentic": 0,
                "suspicious": 0,
                "forged": 0,
                "errors": 0
            }
        }
        
        # Process files concurrently (with limit to avoid overwhelming system)
        semaphore = asyncio.Semaphore(5)  # Limit concurrent processing
        
        async def verify_single_file(file_path: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.verify_certificate(
                        file_path, requester_id, requester_type,
                        purpose=f"Batch verification {batch_id}",
                        metadata=batch_metadata
                    )
                    return {"file_path": file_path, "result": result, "success": True}
                except Exception as e:
                    return {
                        "file_path": file_path,
                        "error": str(e),
                        "success": False
                    }
        
        # Execute batch verification
        tasks = [verify_single_file(fp) for fp in file_paths]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for item in batch_results:
            if isinstance(item, Exception):
                results["failed"] += 1
                results["summary"]["errors"] += 1
                results["results"].append({
                    "error": str(item),
                    "success": False
                })
            elif item["success"]:
                results["completed"] += 1
                result = item["result"]
                
                # Categorize result
                if result.get("final_status") == "VERIFIED_AUTHENTIC":
                    results["summary"]["authentic"] += 1
                elif result.get("final_status") in ["SUSPICIOUS", "UNCERTAIN"]:
                    results["summary"]["suspicious"] += 1
                elif result.get("final_status") in ["FORGED", "TAMPERED"]:
                    results["summary"]["forged"] += 1
                else:
                    results["summary"]["errors"] += 1
                
                results["results"].append(item)
            else:
                results["failed"] += 1
                results["summary"]["errors"] += 1
                results["results"].append(item)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        results["processing_time"] = processing_time
        results["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Batch verification {batch_id} completed in {processing_time:.2f}s")
        return results
    
    async def _preprocess_file(self, file_path: str) -> Dict[str, Any]:
        """Preprocess and validate uploaded file"""
        try:
            # Validate file exists and is readable
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise ValidationError(f"File not found: {file_path}")
            
            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path)
            
            # Get file metadata
            file_stats = file_path_obj.stat()
            
            return {
                "processed_file_path": file_path,
                "file_hash": file_hash,
                "file_size": file_stats.st_size,
                "file_type": file_path_obj.suffix.lower(),
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"File preprocessing failed: {str(e)}")
            raise ProcessingError(f"File preprocessing failed: {str(e)}")
    
    async def _perform_ocr_extraction(self, file_path: str) -> Dict[str, Any]:
        """Perform OCR extraction on certificate"""
        try:
            ocr_result = await self.ocr_service.extract_certificate_data(file_path)
            
            return {
                "extracted_data": ocr_result.get("extracted_data", {}),
                "confidence": ocr_result.get("confidence", 0.0),
                "raw_text": ocr_result.get("raw_text", ""),
                "processing_time": ocr_result.get("processing_time", 0.0),
                "ocr_engine": ocr_result.get("engine", "tesseract"),
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            raise OCRError(f"OCR extraction failed: {str(e)}")
    
    async def _perform_tamper_detection(self, file_path: str) -> Dict[str, Any]:
        """Perform tamper detection analysis"""
        try:
            tamper_result = await self.tamper_detection_func(file_path, {})
            
            # Map tamper detection result to expected format
            overall_confidence = tamper_result.get("overall_confidence", 0.0)
            is_tampered = tamper_result.get("is_tampered", False)
            
            return {
                "overall_score": overall_confidence,
                "authenticity_status": "TAMPERED" if is_tampered else "AUTHENTIC",
                "confidence": overall_confidence,
                "detected_elements": tamper_result.get("detailed_analysis", {}),
                "tamper_flags": tamper_result.get("tamper_flags", []),
                "anomalies": tamper_result.get("tampered_areas", []),
                "processing_time": tamper_result.get("processing_time", 0.0),
                "model_version": "comprehensive_v1.0",
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Tamper detection failed: {str(e)}")
            raise AIModelError(f"Tamper detection failed: {str(e)}")
    
    async def _perform_institutional_verification(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform institutional database verification"""
        try:
            # Cross-reference against all institutional records
            cross_ref_result = await self.institution_service.cross_reference_certificate(extracted_data)
            
            institutional_result = {
                "found_in_records": cross_ref_result.get("found", False),
                "verification_status": cross_ref_result.get("status", "NOT_FOUND"),
                "confidence": cross_ref_result.get("confidence", 0.0),
                "message": cross_ref_result.get("message", ""),
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
            if cross_ref_result.get("found"):
                institutional_result.update({
                    "certificate_id": cross_ref_result.get("certificate_id"),
                    "institution": cross_ref_result.get("institution", {}),
                    "field_matches": cross_ref_result.get("matches", []),
                    "verified_data": cross_ref_result.get("verified_data", {})
                })
            
            return institutional_result
            
        except Exception as e:
            logger.error(f"Institutional verification failed: {str(e)}")
            # Don't raise exception - institutional verification failure shouldn't stop the process
            return {
                "found_in_records": False,
                "verification_status": "ERROR",
                "confidence": 0.0,
                "error": str(e),
                "verification_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _validate_certificate_numbering(
        self, 
        extracted_data: Dict[str, Any], 
        institutional_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate certificate numbering patterns"""
        try:
            cert_number = extracted_data.get("certificate_number", "")
            
            if not cert_number:
                return {
                    "valid_format": False,
                    "confidence": 0.0,
                    "message": "No certificate number found"
                }
            
            # Check against institutional numbering pattern if available
            if institutional_result.get("found_in_records") and institutional_result.get("institution"):
                institution_id = institutional_result["institution"].get("id")
                if institution_id:
                    try:
                        institution = await self.institution_service.get_institution(institution_id)
                        if institution.certificate_numbering_pattern:
                            pattern_match = self._validate_numbering_pattern(
                                cert_number, institution.certificate_numbering_pattern
                            )
                            return {
                                "valid_format": pattern_match["valid"],
                                "confidence": pattern_match["confidence"],
                                "pattern": institution.certificate_numbering_pattern,
                                "message": pattern_match["message"]
                            }
                    except InstitutionNotFoundError:
                        pass
            
            # Basic format validation
            basic_validation = self._basic_certificate_number_validation(cert_number)
            return basic_validation
            
        except Exception as e:
            logger.error(f"Certificate numbering validation failed: {str(e)}")
            return {
                "valid_format": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _check_for_duplicates(
        self, 
        extracted_data: Dict[str, Any], 
        file_hash: str
    ) -> Dict[str, Any]:
        """Check for duplicate certificates"""
        try:
            await self._ensure_db_connection()
            
            duplicates = []
            
            # Check by certificate number
            cert_number = extracted_data.get("certificate_number")
            if cert_number:
                existing_cert = await self.db.certificates.find_one({
                    "certificate_number": cert_number
                })
                if existing_cert:
                    duplicates.append({
                        "type": "certificate_number",
                        "certificate_id": existing_cert["certificate_id"],
                        "match_field": "certificate_number",
                        "match_value": cert_number
                    })
            
            # Check by file hash
            existing_hash = await self.db.certificates.find_one({
                "file_hash": file_hash
            })
            if existing_hash:
                duplicates.append({
                    "type": "file_hash",
                    "certificate_id": existing_hash["certificate_id"],
                    "match_field": "file_hash",
                    "match_value": file_hash
                })
            
            # Check by student details combination
            student_name = extracted_data.get("student_name")
            roll_number = extracted_data.get("roll_number")
            if student_name and roll_number:
                existing_student = await self.db.certificates.find_one({
                    "student_name": {"$regex": f"^{student_name}$", "$options": "i"},
                    "roll_number": roll_number
                })
                if existing_student:
                    duplicates.append({
                        "type": "student_details",
                        "certificate_id": existing_student["certificate_id"],
                        "match_field": "student_name_roll_number",
                        "match_value": f"{student_name}_{roll_number}"
                    })
            
            return {
                "has_duplicates": len(duplicates) > 0,
                "duplicate_count": len(duplicates),
                "duplicates": duplicates,
                "check_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {str(e)}")
            return {
                "has_duplicates": False,
                "duplicate_count": 0,
                "duplicates": [],
                "error": str(e)
            }
    
    async def _combine_verification_results(
        self, 
        verification_id: str, 
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine all verification results into final assessment"""
        
        # Extract individual scores
        ocr_confidence = results["ocr"].get("confidence", 0.0)
        tamper_score = results["tamper_detection"].get("overall_score", 0.0)
        institutional_confidence = results["institutional"].get("confidence", 0.0)
        numbering_confidence = results["numbering"].get("confidence", 0.0)
        
        # Calculate weighted overall confidence
        weights = self.verification_config["weights"]
        overall_confidence = (
            ocr_confidence * weights["ocr_confidence"] +
            tamper_score * weights["tamper_detection"] +
            institutional_confidence * weights["institutional_verification"] +
            numbering_confidence * weights["certificate_numbering"]
        )
        
        # Determine final status based on thresholds and individual results
        final_status, authenticity = self._determine_final_status(
            overall_confidence, results
        )
        
        # Compile detailed analysis
        detailed_analysis = {
            "verification_layers": {
                "ocr_extraction": {
                    "confidence": ocr_confidence,
                    "status": "SUCCESS" if ocr_confidence > 0.7 else "LOW_CONFIDENCE",
                    "extracted_fields": len(results["ocr"].get("extracted_data", {}))
                },
                "tamper_detection": {
                    "score": tamper_score,
                    "status": results["tamper_detection"].get("authenticity_status", "UNKNOWN"),
                    "flags_count": len(results["tamper_detection"].get("tamper_flags", []))
                },
                "institutional_verification": {
                    "confidence": institutional_confidence,
                    "status": results["institutional"].get("verification_status", "NOT_FOUND"),
                    "found_in_records": results["institutional"].get("found_in_records", False)
                },
                "certificate_numbering": {
                    "confidence": numbering_confidence,
                    "valid_format": results["numbering"].get("valid_format", False)
                },
                "duplicate_check": {
                    "has_duplicates": results["duplicate_check"].get("has_duplicates", False),
                    "duplicate_count": results["duplicate_check"].get("duplicate_count", 0)
                }
            },
            "risk_factors": self._identify_risk_factors(results),
            "confidence_breakdown": {
                "ocr": ocr_confidence,
                "tamper_detection": tamper_score,
                "institutional": institutional_confidence,
                "numbering": numbering_confidence,
                "weighted_average": overall_confidence
            }
        }
        
        return {
            "verification_id": verification_id,
            "final_status": final_status,
            "authenticity": authenticity,
            "overall_confidence": overall_confidence,
            "detailed_analysis": detailed_analysis,
            "verification_results": results,
            "verification_timestamp": datetime.utcnow().isoformat(),
            "processing_metadata": {
                "verification_layers_completed": 5,
                "total_processing_steps": 9,
                "system_version": "1.0.0"
            }
        }
    
    def _determine_final_status(
        self, 
        overall_confidence: float, 
        results: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Determine final verification status and authenticity"""
        
        thresholds = self.verification_config["thresholds"]
        
        # Check for critical failures first
        institutional = results["institutional"]
        tamper = results["tamper_detection"]
        duplicates = results["duplicate_check"]
        
        # Critical failure conditions
        if duplicates.get("has_duplicates", False):
            return "DUPLICATE_DETECTED", "SUSPICIOUS"
        
        if tamper.get("tamper_flags") and len(tamper["tamper_flags"]) > 2:
            return "HEAVILY_TAMPERED", "FORGED"
        
        if not institutional.get("found_in_records", False) and overall_confidence < 0.6:
            return "NOT_VERIFIED", "SUSPICIOUS"
        
        # Confidence-based determination
        if overall_confidence >= thresholds["authentic"]:
            if institutional.get("found_in_records", False) and tamper.get("overall_score", 0) > 0.8:
                return "VERIFIED_AUTHENTIC", "AUTHENTIC"
            else:
                return "LIKELY_AUTHENTIC", "LIKELY_AUTHENTIC"
        
        elif overall_confidence >= thresholds["likely_authentic"]:
            return "LIKELY_AUTHENTIC", "LIKELY_AUTHENTIC"
        
        elif overall_confidence >= thresholds["suspicious"]:
            return "SUSPICIOUS", "SUSPICIOUS"
        
        elif overall_confidence >= thresholds["forged"]:
            return "LIKELY_FORGED", "LIKELY_FORGED"
        
        else:
            return "FORGED", "FORGED"
    
    def _identify_risk_factors(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify risk factors from verification results"""
        risk_factors = []
        
        # OCR risks
        ocr = results["ocr"]
        if ocr.get("confidence", 0) < 0.7:
            risk_factors.append({
                "category": "OCR_QUALITY",
                "severity": "MEDIUM",
                "description": "Low OCR confidence may indicate poor image quality or unusual formatting",
                "confidence": ocr.get("confidence", 0)
            })
        
        # Tamper detection risks
        tamper = results["tamper_detection"]
        if tamper.get("tamper_flags"):
            for flag in tamper["tamper_flags"]:
                risk_factors.append({
                    "category": "TAMPERING",
                    "severity": "HIGH",
                    "description": f"Tampering detected: {flag}",
                    "detection_confidence": tamper.get("confidence", 0)
                })
        
        # Institutional verification risks
        institutional = results["institutional"]
        if not institutional.get("found_in_records", False):
            risk_factors.append({
                "category": "INSTITUTIONAL_VERIFICATION",
                "severity": "CRITICAL",
                "description": "Certificate not found in any institutional database",
                "status": institutional.get("verification_status", "UNKNOWN")
            })
        elif institutional.get("confidence", 0) < 0.9:
            risk_factors.append({
                "category": "INSTITUTIONAL_MATCH",
                "severity": "MEDIUM",
                "description": "Partial match with institutional records",
                "confidence": institutional.get("confidence", 0)
            })
        
        # Numbering pattern risks
        numbering = results["numbering"]
        if not numbering.get("valid_format", True):
            risk_factors.append({
                "category": "CERTIFICATE_NUMBERING",
                "severity": "MEDIUM",
                "description": "Certificate number format doesn't match expected pattern",
                "message": numbering.get("message", "")
            })
        
        # Duplicate risks
        duplicates = results["duplicate_check"]
        if duplicates.get("has_duplicates", False):
            risk_factors.append({
                "category": "DUPLICATE_CERTIFICATE",
                "severity": "CRITICAL",
                "description": f"Certificate appears to be a duplicate ({duplicates['duplicate_count']} matches found)",
                "duplicate_types": [d["type"] for d in duplicates.get("duplicates", [])]
            })
        
        return risk_factors
    
    async def _generate_recommendations(self, verification_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on verification results"""
        recommendations = []
        
        final_status = verification_result["final_status"]
        detailed_analysis = verification_result["detailed_analysis"]
        risk_factors = detailed_analysis["risk_factors"]
        
        # Status-based recommendations
        if final_status == "VERIFIED_AUTHENTIC":
            recommendations.append({
                "type": "VERIFICATION_SUCCESS",
                "priority": "INFO",
                "title": "Certificate Verified Successfully",
                "description": "Certificate appears authentic and has been verified against institutional records.",
                "action": "Certificate can be accepted with confidence."
            })
        
        elif final_status in ["SUSPICIOUS", "LIKELY_FORGED", "FORGED"]:
            recommendations.append({
                "type": "MANUAL_REVIEW_REQUIRED",
                "priority": "HIGH",
                "title": "Manual Review Required",
                "description": "Certificate verification indicates potential issues that require human review.",
                "action": "Contact the issuing institution directly for verification."
            })
        
        elif final_status == "NOT_VERIFIED":
            recommendations.append({
                "type": "INSTITUTIONAL_CONTACT",
                "priority": "MEDIUM",
                "title": "Contact Issuing Institution",
                "description": "Certificate not found in institutional databases.",
                "action": "Verify directly with the institution that allegedly issued this certificate."
            })
        
        # Risk-based recommendations
        for risk in risk_factors:
            if risk["category"] == "OCR_QUALITY":
                recommendations.append({
                    "type": "IMAGE_QUALITY",
                    "priority": "MEDIUM",
                    "title": "Improve Image Quality",
                    "description": "OCR confidence is low, possibly due to image quality issues.",
                    "action": "Try uploading a higher resolution, clearer image of the certificate."
                })
            
            elif risk["category"] == "TAMPERING":
                recommendations.append({
                    "type": "TAMPERING_DETECTED",
                    "priority": "CRITICAL",
                    "title": "Potential Tampering Detected",
                    "description": f"AI analysis detected potential tampering: {risk['description']}",
                    "action": "Reject certificate and report potential fraud if applicable."
                })
            
            elif risk["category"] == "DUPLICATE_CERTIFICATE":
                recommendations.append({
                    "type": "DUPLICATE_FOUND",
                    "priority": "CRITICAL",
                    "title": "Duplicate Certificate Detected",
                    "description": "This certificate appears to match existing records in the system.",
                    "action": "Investigate potential fraud or resubmission of the same certificate."
                })
        
        # Confidence-based recommendations
        overall_confidence = verification_result["overall_confidence"]
        if overall_confidence < 0.5:
            recommendations.append({
                "type": "LOW_CONFIDENCE",
                "priority": "HIGH",
                "title": "Low Verification Confidence",
                "description": f"Overall verification confidence is low ({overall_confidence:.1%}).",
                "action": "Consider additional verification methods or reject the certificate."
            })
        
        return recommendations
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _validate_numbering_pattern(self, cert_number: str, pattern: str) -> Dict[str, Any]:
        """Validate certificate number against institutional pattern"""
        # This is a simplified pattern matching - can be enhanced with regex
        # Pattern format: "INST/{year}/{course_code}/{serial}"
        
        try:
            if not pattern or not cert_number:
                return {"valid": False, "confidence": 0.0, "message": "Missing pattern or number"}
            
            # Basic pattern matching (can be enhanced)
            pattern_parts = pattern.split("/")
            number_parts = cert_number.split("/")
            
            if len(pattern_parts) != len(number_parts):
                return {
                    "valid": False, 
                    "confidence": 0.2, 
                    "message": "Number format doesn't match institutional pattern"
                }
            
            # Check each part
            matches = 0
            for i, (pattern_part, number_part) in enumerate(zip(pattern_parts, number_parts)):
                if "{" in pattern_part and "}" in pattern_part:
                    # Variable part - just check if it's not empty
                    if number_part:
                        matches += 1
                else:
                    # Fixed part - exact match
                    if pattern_part == number_part:
                        matches += 1
            
            confidence = matches / len(pattern_parts)
            valid = confidence >= 0.8
            
            return {
                "valid": valid,
                "confidence": confidence,
                "message": f"Pattern match: {matches}/{len(pattern_parts)} parts matched"
            }
            
        except Exception as e:
            return {"valid": False, "confidence": 0.0, "message": f"Pattern validation error: {str(e)}"}
    
    def _basic_certificate_number_validation(self, cert_number: str) -> Dict[str, Any]:
        """Basic certificate number format validation"""
        if not cert_number:
            return {"valid_format": False, "confidence": 0.0, "message": "No certificate number provided"}
        
        # Basic checks
        checks = {
            "has_alphanumeric": any(c.isalnum() for c in cert_number),
            "reasonable_length": 5 <= len(cert_number) <= 50,
            "has_separators": any(c in cert_number for c in ["/", "-", "_", "."]),
            "not_all_same_char": len(set(cert_number)) > 1
        }
        
        passed_checks = sum(checks.values())
        confidence = passed_checks / len(checks)
        
        return {
            "valid_format": confidence >= 0.75,
            "confidence": confidence,
            "message": f"Basic validation: {passed_checks}/{len(checks)} checks passed",
            "checks": checks
        }
    
    async def _initialize_verification_record(
        self,
        verification_id: str,
        requester_id: str,
        requester_type: UserRole,
        purpose: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> VerificationRecord:
        """Initialize verification record in database"""
        
        verification_record = VerificationRecord(
            verification_id=verification_id,
            certificate_id="",  # Will be updated if found
            requester_id=requester_id,
            requester_type=requester_type,
            requester_organization=metadata.get("organization") if metadata else None,
            verification_method="COMPREHENSIVE_MULTI_LAYER",
            verification_steps=[],
            result={},
            status=VerificationStatus.PENDING,
            confidence_score=0.0,
            processing_time=0.0,
            flags_detected=[],
            tamper_indicators=[],
            anomalies=[],
            purpose=purpose,
            metadata=metadata or {}
        )
        
        # Insert into database
        await self._ensure_db_connection()
        result = await self.verification_records_collection.insert_one(
            verification_record.model_dump(by_alias=True)
        )
        verification_record.id = result.inserted_id
        
        return verification_record
    
    async def _update_verification_record(
        self,
        verification_record: VerificationRecord,
        final_result: Dict[str, Any],
        processing_time: float
    ):
        """Update verification record with final results"""
        
        # Extract key information for the record
        status_mapping = {
            "VERIFIED_AUTHENTIC": VerificationStatus.VERIFIED,
            "LIKELY_AUTHENTIC": VerificationStatus.VERIFIED,
            "SUSPICIOUS": VerificationStatus.SUSPICIOUS,
            "LIKELY_FORGED": VerificationStatus.INVALID,
            "FORGED": VerificationStatus.INVALID,
            "NOT_VERIFIED": VerificationStatus.INVALID
        }
        
        final_status = final_result.get("final_status", "UNKNOWN")
        verification_status = status_mapping.get(final_status, VerificationStatus.PENDING)
        
        # Extract certificate ID if found
        certificate_id = ""
        institutional_result = final_result.get("verification_results", {}).get("institutional", {})
        if institutional_result.get("found_in_records"):
            certificate_id = institutional_result.get("certificate_id", "")
        
        # Update record
        update_data = {
            "certificate_id": certificate_id,
            "result": final_result,
            "status": verification_status,
            "confidence_score": final_result.get("overall_confidence", 0.0),
            "processing_time": processing_time,
            "flags_detected": final_result.get("detailed_analysis", {}).get("risk_factors", []),
            "verification_date": datetime.utcnow()
        }
        
        await self.verification_records_collection.update_one(
            {"verification_id": verification_record.verification_id},
            {"$set": update_data}
        )