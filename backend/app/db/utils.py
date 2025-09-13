"""
Database utility functions for common operations.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from bson import ObjectId
import logging

from app.db.database import get_database
from app.db.models import (
    Certificate, Institution, User, VerificationRecord, 
    BlacklistEntry, AuditLog, SystemConfig
)

logger = logging.getLogger(__name__)

class DatabaseUtils:
    """Utility class for common database operations."""
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def to_object_id(id_str: str) -> ObjectId:
        """Convert string ID to ObjectId."""
        if ObjectId.is_valid(id_str):
            return ObjectId(id_str)
        raise ValueError(f"Invalid ObjectId: {id_str}")
    
    @staticmethod
    def serialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize MongoDB document for JSON response."""
        if doc is None:
            return None
        
        # Convert ObjectId to string
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        
        # Convert datetime objects to ISO format
        for key, value in doc.items():
            if isinstance(value, datetime):
                doc[key] = value.isoformat()
            elif isinstance(value, ObjectId):
                doc[key] = str(value)
        
        return doc
    
    @staticmethod
    async def create_audit_log(
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Create an audit log entry."""
        try:
            db = await get_database()
            
            audit_log = AuditLog(
                log_id=DatabaseUtils.generate_id(),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow()
            )
            
            await db.audit_logs.insert_one(audit_log.model_dump(by_alias=True))
            logger.debug(f"Created audit log: {action} on {resource_type}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            # Don't fail the main operation if audit logging fails
            pass

class CertificateRepository:
    """Repository for certificate operations."""
    
    @staticmethod
    async def create(certificate: Certificate) -> str:
        """Create a new certificate."""
        db = await get_database()
        
        # Ensure timestamps are set
        certificate.created_at = datetime.utcnow()
        certificate.updated_at = datetime.utcnow()
        
        result = await db.certificates.insert_one(certificate.model_dump(by_alias=True))
        
        await DatabaseUtils.create_audit_log(
            user_id=certificate.created_by,
            action="CREATE_CERTIFICATE",
            resource_type="certificate",
            resource_id=certificate.certificate_id,
            details={"institution_id": certificate.institution_id}
        )
        
        return str(result.inserted_id)
    
    @staticmethod
    async def get_by_id(certificate_id: str) -> Optional[Dict[str, Any]]:
        """Get certificate by ID."""
        db = await get_database()
        doc = await db.certificates.find_one({"certificate_id": certificate_id})
        return DatabaseUtils.serialize_document(doc)
    
    @staticmethod
    async def get_by_certificate_number(certificate_number: str) -> Optional[Dict[str, Any]]:
        """Get certificate by certificate number."""
        db = await get_database()
        doc = await db.certificates.find_one({"certificate_number": certificate_number})
        return DatabaseUtils.serialize_document(doc)
    
    @staticmethod
    async def update(certificate_id: str, updates: Dict[str, Any], updated_by: Optional[str] = None) -> bool:
        """Update certificate."""
        db = await get_database()
        
        updates["updated_at"] = datetime.utcnow()
        
        result = await db.certificates.update_one(
            {"certificate_id": certificate_id},
            {"$set": updates}
        )
        
        if result.modified_count > 0:
            await DatabaseUtils.create_audit_log(
                user_id=updated_by,
                action="UPDATE_CERTIFICATE",
                resource_type="certificate",
                resource_id=certificate_id,
                changes=updates
            )
        
        return result.modified_count > 0
    
    @staticmethod
    async def search(
        query: Optional[str] = None,
        institution_id: Optional[str] = None,
        verification_status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Search certificates with filters."""
        db = await get_database()
        
        filter_query = {}
        
        if institution_id:
            filter_query["institution_id"] = institution_id
        
        if verification_status:
            filter_query["verification_status"] = verification_status
        
        if query:
            filter_query["$text"] = {"$search": query}
        
        cursor = db.certificates.find(filter_query).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        return [DatabaseUtils.serialize_document(doc) for doc in documents]

class InstitutionRepository:
    """Repository for institution operations."""
    
    @staticmethod
    async def create(institution: Institution) -> str:
        """Create a new institution."""
        db = await get_database()
        
        institution.created_at = datetime.utcnow()
        institution.updated_at = datetime.utcnow()
        
        result = await db.institutions.insert_one(institution.model_dump(by_alias=True))
        
        await DatabaseUtils.create_audit_log(
            user_id=institution.created_by,
            action="CREATE_INSTITUTION",
            resource_type="institution",
            resource_id=institution.institution_id
        )
        
        return str(result.inserted_id)
    
    @staticmethod
    async def get_by_id(institution_id: str) -> Optional[Dict[str, Any]]:
        """Get institution by ID."""
        db = await get_database()
        doc = await db.institutions.find_one({"institution_id": institution_id})
        return DatabaseUtils.serialize_document(doc)
    
    @staticmethod
    async def get_all_active() -> List[Dict[str, Any]]:
        """Get all active institutions."""
        db = await get_database()
        cursor = db.institutions.find({"is_active": True})
        documents = await cursor.to_list(length=None)
        return [DatabaseUtils.serialize_document(doc) for doc in documents]

class UserRepository:
    """Repository for user operations."""
    
    @staticmethod
    async def create(user: User) -> str:
        """Create a new user."""
        db = await get_database()
        
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        result = await db.users.insert_one(user.model_dump(by_alias=True))
        
        await DatabaseUtils.create_audit_log(
            user_id=user.created_by,
            action="CREATE_USER",
            resource_type="user",
            resource_id=user.user_id,
            details={"role": user.role, "email": user.email}
        )
        
        return str(result.inserted_id)
    
    @staticmethod
    async def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        db = await get_database()
        doc = await db.users.find_one({"email": email})
        return DatabaseUtils.serialize_document(doc)
    
    @staticmethod
    async def get_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        db = await get_database()
        doc = await db.users.find_one({"user_id": user_id})
        return DatabaseUtils.serialize_document(doc)
    
    @staticmethod
    async def update_login_info(user_id: str, ip_address: Optional[str] = None):
        """Update user login information."""
        db = await get_database()
        
        updates = {
            "last_login": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "$inc": {"login_count": 1}
        }
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )

class VerificationRepository:
    """Repository for verification record operations."""
    
    @staticmethod
    async def create(verification: VerificationRecord) -> str:
        """Create a new verification record."""
        db = await get_database()
        
        verification.verification_date = datetime.utcnow()
        
        result = await db.verification_records.insert_one(verification.model_dump(by_alias=True))
        
        await DatabaseUtils.create_audit_log(
            user_id=verification.requester_id,
            action="CREATE_VERIFICATION",
            resource_type="verification",
            resource_id=verification.verification_id,
            details={
                "certificate_id": verification.certificate_id,
                "status": verification.status,
                "confidence_score": verification.confidence_score
            }
        )
        
        return str(result.inserted_id)
    
    @staticmethod
    async def get_by_certificate(certificate_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get verification records for a certificate."""
        db = await get_database()
        cursor = db.verification_records.find(
            {"certificate_id": certificate_id}
        ).sort("verification_date", -1).limit(limit)
        
        documents = await cursor.to_list(length=limit)
        return [DatabaseUtils.serialize_document(doc) for doc in documents]
    
    @staticmethod
    async def get_statistics(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get verification statistics."""
        db = await get_database()
        
        match_query = {}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            match_query["verification_date"] = date_filter
        
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$confidence_score"},
                    "avg_processing_time": {"$avg": "$processing_time"}
                }
            }
        ]
        
        results = await db.verification_records.aggregate(pipeline).to_list(length=None)
        
        stats = {
            "total_verifications": sum(r["count"] for r in results),
            "by_status": {r["_id"]: r for r in results}
        }
        
        return stats

class BlacklistRepository:
    """Repository for blacklist operations."""
    
    @staticmethod
    async def create(entry: BlacklistEntry) -> str:
        """Create a new blacklist entry."""
        db = await get_database()
        
        entry.created_at = datetime.utcnow()
        
        result = await db.blacklist_entries.insert_one(entry.model_dump(by_alias=True))
        
        await DatabaseUtils.create_audit_log(
            user_id=entry.reported_by,
            action="CREATE_BLACKLIST_ENTRY",
            resource_type="blacklist",
            resource_id=entry.entry_id,
            details={
                "type": entry.type,
                "identifier": entry.identifier,
                "reason": entry.reason
            }
        )
        
        return str(result.inserted_id)
    
    @staticmethod
    async def check_blacklisted(identifier: str, entry_type: str) -> Optional[Dict[str, Any]]:
        """Check if an identifier is blacklisted."""
        db = await get_database()
        doc = await db.blacklist_entries.find_one({
            "identifier": identifier,
            "type": entry_type,
            "status": "ACTIVE"
        })
        return DatabaseUtils.serialize_document(doc)
    
    @staticmethod
    async def get_active_entries(limit: int = 100) -> List[Dict[str, Any]]:
        """Get active blacklist entries."""
        db = await get_database()
        cursor = db.blacklist_entries.find(
            {"status": "ACTIVE"}
        ).sort("created_at", -1).limit(limit)
        
        documents = await cursor.to_list(length=limit)
        return [DatabaseUtils.serialize_document(doc) for doc in documents]

# Export repository instances
certificate_repo = CertificateRepository()
institution_repo = InstitutionRepository()
user_repo = UserRepository()
verification_repo = VerificationRepository()
blacklist_repo = BlacklistRepository()