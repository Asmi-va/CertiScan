"""
Institution Service - Handles institution registration, certificate management, and verification
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
import hashlib
import uuid
import csv
import io
import json
from pathlib import Path

from ..db.database import get_database
from ..db.models import (
    Institution, Certificate, User, VerificationRecord, CertificateTemplate,
    InstitutionType, VerificationStatus, DegreeType, UserRole
)
from ..core.config import settings
from ..utils.exceptions import (
    InstitutionNotFoundError, CertificateNotFoundError, 
    ValidationError, DuplicateError, UnauthorizedError
)

logger = logging.getLogger(__name__)

class InstitutionService:
    """Service for managing institutions and their certificates"""
    
    def __init__(self):
        self.db = None
        self.institutions_collection = None
        self.certificates_collection = None
        self.users_collection = None
        self.templates_collection = None
        self.verification_records_collection = None
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = await get_database()
            self.institutions_collection = self.db.institutions
            self.certificates_collection = self.db.certificates
            self.users_collection = self.db.users
            self.templates_collection = self.db.certificate_templates
            self.verification_records_collection = self.db.verification_records
    
    async def register_institution(
        self, 
        institution_data: Dict[str, Any], 
        admin_user_id: str
    ) -> Institution:
        """Register a new institution in the system"""
        try:
            await self._ensure_db_connection()
            # Check if institution already exists
            existing = await self.institutions_collection.find_one({
                "institution_id": institution_data["institution_id"]
            })
            if existing:
                raise DuplicateError(f"Institution with ID {institution_data['institution_id']} already exists")
            
            # Validate institution data
            institution = Institution(**institution_data)
            institution.created_by = admin_user_id
            institution.admin_users = [admin_user_id]
            
            # Generate API key for external integrations
            institution.api_key = self._generate_api_key(institution.institution_id)
            
            # Insert into database
            result = await self.institutions_collection.insert_one(institution.model_dump(by_alias=True))
            institution.id = result.inserted_id
            
            logger.info(f"Institution registered: {institution.institution_id}")
            return institution
            
        except Exception as e:
            logger.error(f"Error registering institution: {str(e)}")
            raise
    
    async def get_institution(self, institution_id: str) -> Institution:
        """Get institution by ID"""
        await self._ensure_db_connection()
        institution_data = await self.institutions_collection.find_one({
            "institution_id": institution_id
        })
        if not institution_data:
            raise InstitutionNotFoundError(f"Institution {institution_id} not found")
        
        return Institution(**institution_data)
    
    async def update_institution(
        self, 
        institution_id: str, 
        update_data: Dict[str, Any],
        user_id: str
    ) -> Institution:
        """Update institution information"""
        try:
            # Verify user has permission to update this institution
            institution = await self.get_institution(institution_id)
            if user_id not in institution.admin_users:
                raise UnauthorizedError("User not authorized to update this institution")
            
            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Update in database
            result = await self.institutions_collection.update_one(
                {"institution_id": institution_id},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                raise InstitutionNotFoundError(f"Institution {institution_id} not found")
            
            # Return updated institution
            return await self.get_institution(institution_id)
            
        except Exception as e:
            logger.error(f"Error updating institution {institution_id}: {str(e)}")
            raise
    
    async def add_certificate_record(
        self, 
        certificate_data: Dict[str, Any], 
        user_id: str
    ) -> Certificate:
        """Add a single certificate record to institution database"""
        try:
            await self._ensure_db_connection()
            # Validate user has permission for this institution
            institution = await self.get_institution(certificate_data["institution_id"])
            if user_id not in institution.admin_users:
                raise UnauthorizedError("User not authorized to add certificates for this institution")
            
            # Check if certificate already exists
            existing = await self.certificates_collection.find_one({
                "certificate_id": certificate_data["certificate_id"]
            })
            if existing:
                raise DuplicateError(f"Certificate {certificate_data['certificate_id']} already exists")
            
            # Create certificate object
            certificate = Certificate(**certificate_data)
            certificate.created_by = user_id
            certificate.verification_status = VerificationStatus.VERIFIED  # Institution-added certificates are pre-verified
            certificate.verification_score = 1.0
            
            # Insert into database
            result = await self.certificates_collection.insert_one(certificate.model_dump(by_alias=True))
            certificate.id = result.inserted_id
            
            # Update institution statistics
            await self.institutions_collection.update_one(
                {"institution_id": certificate_data["institution_id"]},
                {
                    "$inc": {
                        "total_certificates": 1,
                        "verified_certificates": 1
                    },
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            logger.info(f"Certificate added: {certificate.certificate_id}")
            return certificate
            
        except Exception as e:
            logger.error(f"Error adding certificate: {str(e)}")
            raise
    
    async def bulk_upload_certificates(
        self, 
        institution_id: str, 
        csv_data: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Bulk upload certificates from CSV data"""
        try:
            # Validate user has permission
            institution = await self.get_institution(institution_id)
            if user_id not in institution.admin_users:
                raise UnauthorizedError("User not authorized to upload certificates for this institution")
            
            # Parse CSV data
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            results = {
                "total_processed": 0,
                "successful": 0,
                "failed": 0,
                "errors": [],
                "certificate_ids": []
            }
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 to account for header
                try:
                    # Map CSV columns to certificate fields
                    certificate_data = self._map_csv_to_certificate(row, institution_id)
                    
                    # Add certificate
                    certificate = await self.add_certificate_record(certificate_data, user_id)
                    results["certificate_ids"].append(certificate.certificate_id)
                    results["successful"] += 1
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "row": row_num,
                        "error": str(e),
                        "data": row
                    })
                
                results["total_processed"] += 1
            
            logger.info(f"Bulk upload completed for {institution_id}: {results['successful']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk upload for {institution_id}: {str(e)}")
            raise
    
    async def verify_certificate_against_institution(
        self, 
        certificate_id: str, 
        institution_id: str
    ) -> Dict[str, Any]:
        """Verify a certificate against institution records"""
        try:
            await self._ensure_db_connection()
            # Get certificate from institution database
            certificate = await self.certificates_collection.find_one({
                "certificate_id": certificate_id,
                "institution_id": institution_id
            })
            
            if not certificate:
                return {
                    "verified": False,
                    "status": "NOT_FOUND",
                    "message": "Certificate not found in institution records",
                    "confidence": 0.0
                }
            
            # Check certificate validity
            cert_obj = Certificate(**certificate)
            
            verification_result = {
                "verified": True,
                "status": "VERIFIED",
                "message": "Certificate found and verified in institution records",
                "confidence": 1.0,
                "certificate_data": {
                    "student_name": cert_obj.student_name,
                    "roll_number": cert_obj.roll_number,
                    "course_name": cert_obj.course_name,
                    "degree_type": cert_obj.degree_type,
                    "graduation_date": cert_obj.graduation_date.isoformat(),
                    "issue_date": cert_obj.issue_date.isoformat(),
                    "grades": cert_obj.grades,
                    "certificate_number": cert_obj.certificate_number
                },
                "institution_verified": True,
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Error verifying certificate {certificate_id} against institution {institution_id}: {str(e)}")
            return {
                "verified": False,
                "status": "ERROR",
                "message": f"Verification error: {str(e)}",
                "confidence": 0.0
            }
    
    async def cross_reference_certificate(
        self, 
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Cross-reference extracted certificate data against all institution records"""
        try:
            await self._ensure_db_connection()
            # Try to find certificate by certificate number first
            certificate = None
            if "certificate_number" in extracted_data:
                certificate = await self.certificates_collection.find_one({
                    "certificate_number": extracted_data["certificate_number"]
                })
            
            # If not found by certificate number, try by student details
            if not certificate and "student_name" in extracted_data and "roll_number" in extracted_data:
                certificate = await self.certificates_collection.find_one({
                    "student_name": {"$regex": extracted_data["student_name"], "$options": "i"},
                    "roll_number": extracted_data["roll_number"]
                })
            
            if not certificate:
                return {
                    "found": False,
                    "status": "NOT_FOUND",
                    "message": "Certificate not found in any institution records",
                    "confidence": 0.0,
                    "matches": []
                }
            
            cert_obj = Certificate(**certificate)
            
            # Calculate match confidence based on data similarity
            confidence = self._calculate_match_confidence(extracted_data, cert_obj)
            
            # Get institution details
            institution = await self.get_institution(cert_obj.institution_id)
            
            result = {
                "found": True,
                "status": "FOUND",
                "message": "Certificate found in institution records",
                "confidence": confidence,
                "certificate_id": cert_obj.certificate_id,
                "institution": {
                    "id": institution.institution_id,
                    "name": institution.name,
                    "type": institution.type,
                    "accreditation_status": institution.accreditation_status
                },
                "matches": self._compare_certificate_data(extracted_data, cert_obj),
                "verified_data": {
                    "student_name": cert_obj.student_name,
                    "roll_number": cert_obj.roll_number,
                    "course_name": cert_obj.course_name,
                    "degree_type": cert_obj.degree_type,
                    "graduation_date": cert_obj.graduation_date.isoformat(),
                    "certificate_number": cert_obj.certificate_number,
                    "grades": cert_obj.grades
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error cross-referencing certificate: {str(e)}")
            return {
                "found": False,
                "status": "ERROR",
                "message": f"Cross-reference error: {str(e)}",
                "confidence": 0.0,
                "matches": []
            }
    
    async def get_institution_certificates(
        self, 
        institution_id: str, 
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get certificates for an institution with pagination and filtering"""
        try:
            # Verify user has permission
            institution = await self.get_institution(institution_id)
            if user_id not in institution.admin_users:
                raise UnauthorizedError("User not authorized to view certificates for this institution")
            
            # Build query
            query = {"institution_id": institution_id}
            if filters:
                if "degree_type" in filters:
                    query["degree_type"] = filters["degree_type"]
                if "graduation_year" in filters:
                    query["graduation_date"] = {
                        "$gte": datetime(filters["graduation_year"], 1, 1),
                        "$lt": datetime(filters["graduation_year"] + 1, 1, 1)
                    }
                if "verification_status" in filters:
                    query["verification_status"] = filters["verification_status"]
            
            # Get total count
            total_count = await self.certificates_collection.count_documents(query)
            
            # Get certificates with pagination
            cursor = self.certificates_collection.find(query).skip(offset).limit(limit)
            certificates = []
            async for cert_data in cursor:
                certificates.append(Certificate(**cert_data))
            
            return {
                "certificates": certificates,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
            
        except Exception as e:
            logger.error(f"Error getting certificates for institution {institution_id}: {str(e)}")
            raise
    
    async def get_institution_statistics(self, institution_id: str, user_id: str) -> Dict[str, Any]:
        """Get statistics for an institution"""
        try:
            # Verify user has permission
            institution = await self.get_institution(institution_id)
            if user_id not in institution.admin_users:
                raise UnauthorizedError("User not authorized to view statistics for this institution")
            
            # Get certificate statistics
            pipeline = [
                {"$match": {"institution_id": institution_id}},
                {"$group": {
                    "_id": "$verification_status",
                    "count": {"$sum": 1}
                }}
            ]
            
            status_counts = {}
            async for result in self.certificates_collection.aggregate(pipeline):
                status_counts[result["_id"]] = result["count"]
            
            # Get verification statistics
            verification_pipeline = [
                {"$match": {"certificate_id": {"$in": await self._get_institution_certificate_ids(institution_id)}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m", "date": "$verification_date"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            monthly_verifications = []
            async for result in self.verification_records_collection.aggregate(verification_pipeline):
                monthly_verifications.append({
                    "month": result["_id"],
                    "verifications": result["count"]
                })
            
            return {
                "institution": {
                    "id": institution.institution_id,
                    "name": institution.name,
                    "type": institution.type
                },
                "certificate_statistics": {
                    "total": institution.total_certificates,
                    "verified": institution.verified_certificates,
                    "by_status": status_counts
                },
                "verification_statistics": {
                    "monthly": monthly_verifications,
                    "total_verifications": sum(item["verifications"] for item in monthly_verifications)
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics for institution {institution_id}: {str(e)}")
            raise
    
    def _generate_api_key(self, institution_id: str) -> str:
        """Generate a unique API key for an institution"""
        data = f"{institution_id}_{datetime.utcnow().isoformat()}_{uuid.uuid4()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _map_csv_to_certificate(self, row: Dict[str, str], institution_id: str) -> Dict[str, Any]:
        """Map CSV row data to certificate fields"""
        try:
            # Required fields mapping
            certificate_data = {
                "certificate_id": row.get("certificate_id") or f"{institution_id}_{row['certificate_number']}",
                "student_name": row["student_name"],
                "roll_number": row["roll_number"],
                "institution_id": institution_id,
                "course_name": row["course_name"],
                "degree_type": DegreeType(row["degree_type"].upper()),
                "graduation_date": datetime.fromisoformat(row["graduation_date"]),
                "issue_date": datetime.fromisoformat(row.get("issue_date", row["graduation_date"])),
                "certificate_number": row["certificate_number"],
                "file_hash": hashlib.sha256(f"{row['certificate_number']}_{row['student_name']}".encode()).hexdigest()
            }
            
            # Optional fields
            if "grades" in row and row["grades"]:
                try:
                    certificate_data["grades"] = json.loads(row["grades"])
                except json.JSONDecodeError:
                    certificate_data["grades"] = {"overall": row["grades"]}
            
            if "specialization" in row:
                certificate_data["specialization"] = row["specialization"]
            
            if "duration" in row:
                certificate_data["duration"] = row["duration"]
            
            return certificate_data
            
        except KeyError as e:
            raise ValidationError(f"Missing required field in CSV: {e}")
        except ValueError as e:
            raise ValidationError(f"Invalid data format in CSV: {e}")
    
    def _calculate_match_confidence(self, extracted_data: Dict[str, Any], certificate: Certificate) -> float:
        """Calculate confidence score for certificate match"""
        matches = 0
        total_checks = 0
        
        # Check exact matches
        exact_match_fields = [
            ("certificate_number", "certificate_number"),
            ("roll_number", "roll_number"),
            ("course_name", "course_name")
        ]
        
        for extracted_field, cert_field in exact_match_fields:
            if extracted_field in extracted_data:
                total_checks += 1
                if str(extracted_data[extracted_field]).lower() == str(getattr(certificate, cert_field)).lower():
                    matches += 1
        
        # Check name similarity (fuzzy match)
        if "student_name" in extracted_data:
            total_checks += 1
            name_similarity = self._calculate_name_similarity(
                extracted_data["student_name"], 
                certificate.student_name
            )
            matches += name_similarity
        
        # Check date proximity
        if "graduation_date" in extracted_data:
            total_checks += 1
            try:
                extracted_date = datetime.fromisoformat(extracted_data["graduation_date"])
                date_diff = abs((extracted_date - certificate.graduation_date).days)
                if date_diff <= 30:  # Within 30 days
                    matches += 1
                elif date_diff <= 365:  # Within 1 year
                    matches += 0.5
            except:
                pass
        
        return matches / total_checks if total_checks > 0 else 0.0
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        # Simple similarity calculation - can be enhanced with more sophisticated algorithms
        name1_words = set(name1.lower().split())
        name2_words = set(name2.lower().split())
        
        if not name1_words or not name2_words:
            return 0.0
        
        intersection = name1_words.intersection(name2_words)
        union = name1_words.union(name2_words)
        
        return len(intersection) / len(union)
    
    def _compare_certificate_data(self, extracted_data: Dict[str, Any], certificate: Certificate) -> List[Dict[str, Any]]:
        """Compare extracted data with certificate data and return detailed matches"""
        comparisons = []
        
        fields_to_compare = [
            ("student_name", "student_name", "Student Name"),
            ("roll_number", "roll_number", "Roll Number"),
            ("course_name", "course_name", "Course Name"),
            ("certificate_number", "certificate_number", "Certificate Number"),
            ("degree_type", "degree_type", "Degree Type")
        ]
        
        for extracted_field, cert_field, display_name in fields_to_compare:
            if extracted_field in extracted_data:
                extracted_value = str(extracted_data[extracted_field])
                cert_value = str(getattr(certificate, cert_field))
                
                match_status = "EXACT" if extracted_value.lower() == cert_value.lower() else "MISMATCH"
                if match_status == "MISMATCH" and extracted_field == "student_name":
                    similarity = self._calculate_name_similarity(extracted_value, cert_value)
                    if similarity > 0.7:
                        match_status = "SIMILAR"
                
                comparisons.append({
                    "field": display_name,
                    "extracted": extracted_value,
                    "verified": cert_value,
                    "status": match_status
                })
        
        return comparisons
    
    async def _get_institution_certificate_ids(self, institution_id: str) -> List[str]:
        """Get all certificate IDs for an institution"""
        cursor = self.certificates_collection.find(
            {"institution_id": institution_id},
            {"certificate_id": 1}
        )
        
        certificate_ids = []
        async for cert in cursor:
            certificate_ids.append(cert["certificate_id"])
        
        return certificate_ids