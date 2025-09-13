"""
Simple test script for institutional database verification system
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.app.services.institution_service import InstitutionService
from backend.app.db.models import InstitutionType, DegreeType, VerificationStatus
from backend.app.db.database import connect_to_mongo, close_mongo_connection
from backend.app.core.config import settings

async def test_basic_functionality():
    """Test basic institutional verification functionality"""
    print("Testing Institutional Database Verification System")
    print("=" * 60)
    
    # Initialize database connection
    print("Connecting to database...")
    await connect_to_mongo()
    print("✓ Database connected")
    
    # Initialize service
    institution_service = InstitutionService()
    
    # Test institution data
    test_institution = {
        "institution_id": "TEST_UNIV_001",
        "name": "Test University",
        "short_name": "TU",
        "type": InstitutionType.UNIVERSITY,
        "address": {
            "street": "Test Street",
            "city": "Test City",
            "state": "Test State",
            "postal_code": "123456",
            "country": "India"
        },
        "contact_info": {
            "phone": "+91-123-4567890",
            "email": "admin@testuniv.ac.in",
            "website": "https://testuniv.ac.in"
        },
        "accreditation_status": "A Grade",
        "accreditation_body": "NAAC",
        "license_number": "TEST/UNIV/2024/001",
        "is_active": True,
        "verification_enabled": True
    }
    
    try:
        # Test 1: Register institution
        print("\n1. Testing institution registration...")
        institution = await institution_service.register_institution(
            test_institution,
            "test_admin_001"
        )
        print(f"✓ Institution registered: {institution.name}")
        
        # Test 2: Add a certificate
        print("\n2. Testing certificate addition...")
        certificate_data = {
            "certificate_id": "TEST_2024_CS_001",
            "student_name": "Test Student",
            "roll_number": "2024CS001",
            "institution_id": "TEST_UNIV_001",
            "course_name": "Bachelor of Computer Science",
            "degree_type": DegreeType.BACHELOR,
            "graduation_date": datetime(2024, 6, 15),
            "issue_date": datetime(2024, 7, 1),
            "certificate_number": "TEST/2024/CS/001",
            "grades": {
                "overall": "A",
                "cgpa": "8.5"
            },
            "file_hash": "test_hash_123"
        }
        
        certificate = await institution_service.add_certificate_record(
            certificate_data,
            "test_admin_001"
        )
        print(f"✓ Certificate added: {certificate.certificate_id}")
        
        # Test 3: Verify certificate
        print("\n3. Testing certificate verification...")
        result = await institution_service.verify_certificate_against_institution(
            "TEST_2024_CS_001",
            "TEST_UNIV_001"
        )
        print(f"✓ Verification result: {result['status']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Message: {result['message']}")
        
        # Test 4: Cross-reference
        print("\n4. Testing cross-reference...")
        extracted_data = {
            "certificate_number": "TEST/2024/CS/001",
            "student_name": "Test Student",
            "roll_number": "2024CS001"
        }
        
        result = await institution_service.cross_reference_certificate(extracted_data)
        print(f"✓ Cross-reference result: {result['status']}")
        print(f"  Found: {result['found']}")
        print(f"  Confidence: {result['confidence']}")
        
        # Test 5: Get institution
        print("\n5. Testing institution retrieval...")
        retrieved_institution = await institution_service.get_institution("TEST_UNIV_001")
        print(f"✓ Retrieved institution: {retrieved_institution.name}")
        print(f"  Total certificates: {retrieved_institution.total_certificates}")
        
        print("\n" + "=" * 60)
        print("✓ All basic tests passed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        await close_mongo_connection()
        print("Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())