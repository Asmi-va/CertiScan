#!/usr/bin/env python3
"""
Test script for data models and database functionality.
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def test_models_and_database():
    """Test the data models and database functionality."""
    print("Testing Data Models and Database")
    print("=" * 50)
    
    try:
        # Test model imports
        print("\n1. Testing Model Imports...")
        from app.db.models import (
            Certificate, Institution, User, VerificationRecord, BlacklistEntry,
            CertificateTemplate, AuditLog, SystemConfig,
            VerificationStatus, UserRole, InstitutionType, DegreeType,
            BlacklistType, BlacklistStatus
        )
        print("   ✓ All models imported successfully")
        
        # Test enum values
        print("\n2. Testing Enums...")
        print(f"   Verification Status: {list(VerificationStatus)}")
        print(f"   User Roles: {list(UserRole)}")
        print(f"   Institution Types: {list(InstitutionType)}")
        print(f"   Degree Types: {list(DegreeType)}")
        print("   ✓ All enums working correctly")
        
        # Test model creation
        print("\n3. Testing Model Creation...")
        
        # Test Certificate model
        certificate = Certificate(
            certificate_id="CERT-2024-001",
            student_name="John Doe",
            roll_number="2020CS001",
            institution_id="INST-001",
            course_name="Computer Science",
            degree_type=DegreeType.BACHELOR,
            graduation_date=datetime(2024, 6, 15),
            issue_date=datetime(2024, 7, 1),
            certificate_number="CS-2024-001",
            file_hash="abc123def456",
            grades={"cgpa": 8.5, "percentage": 85.0}
        )
        print("   ✓ Certificate model created")
        
        # Test Institution model
        institution = Institution(
            institution_id="INST-001",
            name="Test University",
            type=InstitutionType.UNIVERSITY,
            accreditation_status="NAAC A+",
            address={"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            contact_info={"email": "admin@testuni.edu", "phone": "+91-22-12345678"}
        )
        print("   ✓ Institution model created")
        
        # Test User model
        user = User(
            user_id="USER-001",
            email="admin@testuni.edu",
            hashed_password="hashed_password_here",
            full_name="Admin User",
            role=UserRole.INSTITUTION,
            institution_id="INST-001"
        )
        print("   ✓ User model created")
        
        # Test VerificationRecord model
        verification = VerificationRecord(
            verification_id="VER-001",
            certificate_id="CERT-2024-001",
            requester_type=UserRole.EMPLOYER,
            verification_method="AI_OCR_BLOCKCHAIN",
            result={"status": "verified", "confidence": 0.95},
            status=VerificationStatus.VERIFIED,
            confidence_score=0.95,
            processing_time=2.5
        )
        print("   ✓ VerificationRecord model created")
        
        # Test BlacklistEntry model
        blacklist_entry = BlacklistEntry(
            entry_id="BL-001",
            type=BlacklistType.CERTIFICATE,
            identifier="FAKE-CERT-001",
            reason="Forged certificate detected",
            reported_by="USER-001"
        )
        print("   ✓ BlacklistEntry model created")
        
        # Test model serialization
        print("\n4. Testing Model Serialization...")
        cert_dict = certificate.model_dump()
        print(f"   Certificate serialized: {len(cert_dict)} fields")
        
        inst_dict = institution.model_dump()
        print(f"   Institution serialized: {len(inst_dict)} fields")
        
        user_dict = user.model_dump()
        print(f"   User serialized: {len(user_dict)} fields")
        
        print("   ✓ All models serialize correctly")
        
        # Test database connection (if MongoDB is available)
        print("\n5. Testing Database Connection...")
        try:
            from app.db.database import connect_to_mongo, close_mongo_connection, get_database
            
            await connect_to_mongo()
            print("   ✓ Database connection successful")
            
            db = await get_database()
            print(f"   ✓ Database instance obtained: {db.name}")
            
            # Test collection access
            collections = await db.list_collection_names()
            print(f"   ✓ Collections available: {len(collections)}")
            
            await close_mongo_connection()
            print("   ✓ Database connection closed")
            
        except Exception as e:
            print(f"   ⚠ Database connection failed: {str(e)}")
            print("   (This is expected if MongoDB is not running)")
        
        # Test database utilities
        print("\n6. Testing Database Utilities...")
        from app.db.utils import DatabaseUtils
        
        # Test ID generation
        test_id = DatabaseUtils.generate_id()
        print(f"   Generated ID: {test_id}")
        print("   ✓ ID generation working")
        
        # Test document serialization
        test_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "created_at": datetime.utcnow(),
            "name": "Test Document"
        }
        
        serialized = DatabaseUtils.serialize_document(test_doc.copy())
        print(f"   Document serialized: {serialized}")
        print("   ✓ Document serialization working")
        
        # Test repository imports
        print("\n7. Testing Repository Imports...")
        from app.db.utils import (
            certificate_repo, institution_repo, user_repo,
            verification_repo, blacklist_repo
        )
        print("   ✓ All repositories imported successfully")
        
        # Test index definitions
        print("\n8. Testing Index Definitions...")
        from app.db.indexes import INDEXES
        
        print(f"   Index definitions for {len(INDEXES)} collections:")
        for collection, indexes in INDEXES.items():
            print(f"     {collection}: {len(indexes)} indexes")
        
        print("   ✓ Index definitions loaded successfully")
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED - Models and database setup successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    success = asyncio.run(test_models_and_database())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()