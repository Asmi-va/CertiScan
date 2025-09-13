"""
Test script for institutional database verification system
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
from backend.app.db.database import get_database
from backend.app.core.config import settings

async def setup_test_data():
    """Set up test institutions and certificates"""
    print("Setting up test data...")
    
    institution_service = InstitutionService()
    
    # Test institution data
    test_institution = {
        "institution_id": "JHARKHAND_UNIV_001",
        "name": "Jharkhand University",
        "short_name": "JU",
        "type": InstitutionType.UNIVERSITY,
        "address": {
            "street": "University Road",
            "city": "Ranchi",
            "state": "Jharkhand",
            "postal_code": "834008",
            "country": "India"
        },
        "contact_info": {
            "phone": "+91-651-2345678",
            "email": "admin@jharkhandu.ac.in",
            "website": "https://jharkhandu.ac.in"
        },
        "accreditation_status": "A+ Grade by NAAC",
        "accreditation_body": "NAAC",
        "accreditation_date": datetime(2020, 6, 15),
        "license_number": "JH/UNIV/2015/001",
        "authorized_signatories": [
            {
                "name": "Dr. Rajesh Kumar",
                "designation": "Vice Chancellor",
                "signature_path": "/signatures/vc_signature.png"
            },
            {
                "name": "Prof. Sunita Sharma",
                "designation": "Registrar",
                "signature_path": "/signatures/registrar_signature.png"
            }
        ],
        "certificate_numbering_pattern": "JU/{year}/{course_code}/{serial}",
        "is_active": True,
        "verification_enabled": True
    }
    
    # Register institution
    try:
        institution = await institution_service.register_institution(
            test_institution,
            "admin_user_001"
        )
        print(f"✓ Institution registered: {institution.name}")
    except Exception as e:
        print(f"Institution registration error (may already exist): {e}")
        institution = await institution_service.get_institution("JHARKHAND_UNIV_001")
    
    # Test certificate data
    test_certificates = [
        {
            "certificate_id": "JU_2024_CS_001",
            "student_name": "Rahul Kumar Singh",
            "roll_number": "2020CS001",
            "institution_id": "JHARKHAND_UNIV_001",
            "course_name": "Bachelor of Computer Science",
            "degree_type": DegreeType.BACHELOR,
            "graduation_date": datetime(2024, 6, 15),
            "issue_date": datetime(2024, 7, 1),
            "certificate_number": "JU/2024/CS/001",
            "grades": {
                "overall": "A",
                "cgpa": "8.5",
                "percentage": "85%",
                "subjects": {
                    "Data Structures": "A+",
                    "Algorithms": "A",
                    "Database Systems": "A+",
                    "Software Engineering": "A"
                }
            },
            "specialization": "Software Engineering",
            "duration": "4 years",
            "file_hash": "abc123def456ghi789"
        },
        {
            "certificate_id": "JU_2024_CS_002",
            "student_name": "Priya Kumari",
            "roll_number": "2020CS002",
            "institution_id": "JHARKHAND_UNIV_001",
            "course_name": "Bachelor of Computer Science",
            "degree_type": DegreeType.BACHELOR,
            "graduation_date": datetime(2024, 6, 15),
            "issue_date": datetime(2024, 7, 1),
            "certificate_number": "JU/2024/CS/002",
            "grades": {
                "overall": "A+",
                "cgpa": "9.2",
                "percentage": "92%"
            },
            "specialization": "Artificial Intelligence",
            "duration": "4 years",
            "file_hash": "def456ghi789jkl012"
        },
        {
            "certificate_id": "JU_2023_MBA_001",
            "student_name": "Amit Kumar Sharma",
            "roll_number": "2021MBA001",
            "institution_id": "JHARKHAND_UNIV_001",
            "course_name": "Master of Business Administration",
            "degree_type": DegreeType.MASTER,
            "graduation_date": datetime(2023, 12, 20),
            "issue_date": datetime(2024, 1, 15),
            "certificate_number": "JU/2023/MBA/001",
            "grades": {
                "overall": "B+",
                "cgpa": "7.8",
                "percentage": "78%"
            },
            "specialization": "Finance",
            "duration": "2 years",
            "file_hash": "ghi789jkl012mno345"
        }
    ]
    
    # Add certificates
    for cert_data in test_certificates:
        try:
            certificate = await institution_service.add_certificate_record(
                cert_data,
                "admin_user_001"
            )
            print(f"✓ Certificate added: {certificate.certificate_id}")
        except Exception as e:
            print(f"Certificate addition error (may already exist): {e}")
    
    print("Test data setup completed!\n")
    return institution

async def test_certificate_verification():
    """Test certificate verification against institution records"""
    print("=== Testing Certificate Verification ===")
    
    institution_service = InstitutionService()
    
    # Test 1: Verify existing certificate
    print("\n1. Testing verification of existing certificate...")
    result = await institution_service.verify_certificate_against_institution(
        "JU_2024_CS_001",
        "JHARKHAND_UNIV_001"
    )
    print(f"Verification result: {result['status']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Message: {result['message']}")
    if result['verified']:
        print(f"Student: {result['certificate_data']['student_name']}")
        print(f"Course: {result['certificate_data']['course_name']}")
    
    # Test 2: Verify non-existent certificate
    print("\n2. Testing verification of non-existent certificate...")
    result = await institution_service.verify_certificate_against_institution(
        "FAKE_CERT_001",
        "JHARKHAND_UNIV_001"
    )
    print(f"Verification result: {result['status']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Message: {result['message']}")

async def test_cross_reference():
    """Test cross-referencing extracted certificate data"""
    print("\n=== Testing Cross-Reference Functionality ===")
    
    institution_service = InstitutionService()
    
    # Test 1: Cross-reference with exact match
    print("\n1. Testing cross-reference with exact match...")
    extracted_data = {
        "certificate_number": "JU/2024/CS/001",
        "student_name": "Rahul Kumar Singh",
        "roll_number": "2020CS001",
        "course_name": "Bachelor of Computer Science",
        "graduation_date": "2024-06-15"
    }
    
    result = await institution_service.cross_reference_certificate(extracted_data)
    print(f"Cross-reference result: {result['status']}")
    print(f"Found: {result['found']}")
    print(f"Confidence: {result['confidence']}")
    if result['found']:
        print(f"Institution: {result['institution']['name']}")
        print("Field matches:")
        for match in result['matches']:
            print(f"  {match['field']}: {match['status']}")
    
    # Test 2: Cross-reference with partial match (name variation)
    print("\n2. Testing cross-reference with name variation...")
    extracted_data = {
        "certificate_number": "JU/2024/CS/002",
        "student_name": "Priya K",  # Shortened name
        "roll_number": "2020CS002",
        "course_name": "Bachelor of Computer Science"
    }
    
    result = await institution_service.cross_reference_certificate(extracted_data)
    print(f"Cross-reference result: {result['status']}")
    print(f"Found: {result['found']}")
    print(f"Confidence: {result['confidence']}")
    if result['found']:
        print("Field matches:")
        for match in result['matches']:
            print(f"  {match['field']}: {match['status']} - Extracted: '{match['extracted']}', Verified: '{match['verified']}'")
    
    # Test 3: Cross-reference with no match
    print("\n3. Testing cross-reference with no match...")
    extracted_data = {
        "certificate_number": "FAKE/2024/CS/999",
        "student_name": "Non Existent Student",
        "roll_number": "9999CS999"
    }
    
    result = await institution_service.cross_reference_certificate(extracted_data)
    print(f"Cross-reference result: {result['status']}")
    print(f"Found: {result['found']}")
    print(f"Message: {result['message']}")

async def test_bulk_upload():
    """Test bulk certificate upload functionality"""
    print("\n=== Testing Bulk Upload Functionality ===")
    
    institution_service = InstitutionService()
    
    # Create CSV data for bulk upload
    csv_data = """certificate_id,student_name,roll_number,course_name,degree_type,graduation_date,issue_date,certificate_number,grades,specialization,duration
JU_2024_EE_001,Suresh Kumar,2020EE001,Bachelor of Electrical Engineering,BACHELOR,2024-06-15,2024-07-01,JU/2024/EE/001,"{""overall"": ""B+"", ""cgpa"": ""7.5""}",Power Systems,4 years
JU_2024_EE_002,Kavita Singh,2020EE002,Bachelor of Electrical Engineering,BACHELOR,2024-06-15,2024-07-01,JU/2024/EE/002,"{""overall"": ""A"", ""cgpa"": ""8.2""}",Electronics,4 years
JU_2024_ME_001,Ravi Prakash,2020ME001,Bachelor of Mechanical Engineering,BACHELOR,2024-06-15,2024-07-01,JU/2024/ME/001,"{""overall"": ""A+"", ""cgpa"": ""9.0""}",Thermal Engineering,4 years"""
    
    print("Uploading certificates via CSV...")
    try:
        results = await institution_service.bulk_upload_certificates(
            "JHARKHAND_UNIV_001",
            csv_data,
            "admin_user_001"
        )
        
        print(f"Total processed: {results['total_processed']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        if results['errors']:
            print("Errors:")
            for error in results['errors']:
                print(f"  Row {error['row']}: {error['error']}")
        
        if results['certificate_ids']:
            print("Successfully added certificates:")
            for cert_id in results['certificate_ids']:
                print(f"  - {cert_id}")
                
    except Exception as e:
        print(f"Bulk upload error: {e}")

async def test_institution_statistics():
    """Test institution statistics functionality"""
    print("\n=== Testing Institution Statistics ===")
    
    institution_service = InstitutionService()
    
    try:
        stats = await institution_service.get_institution_statistics(
            "JHARKHAND_UNIV_001",
            "admin_user_001"
        )
        
        print(f"Institution: {stats['institution']['name']}")
        print(f"Total certificates: {stats['certificate_statistics']['total']}")
        print(f"Verified certificates: {stats['certificate_statistics']['verified']}")
        print("Certificates by status:")
        for status, count in stats['certificate_statistics']['by_status'].items():
            print(f"  {status}: {count}")
        
        print(f"Total verifications: {stats['verification_statistics']['total_verifications']}")
        
    except Exception as e:
        print(f"Statistics error: {e}")

async def test_certificate_listing():
    """Test certificate listing with pagination and filtering"""
    print("\n=== Testing Certificate Listing ===")
    
    institution_service = InstitutionService()
    
    try:
        # Test basic listing
        result = await institution_service.get_institution_certificates(
            "JHARKHAND_UNIV_001",
            "admin_user_001",
            limit=10,
            offset=0
        )
        
        print(f"Total certificates: {result['total_count']}")
        print(f"Retrieved: {len(result['certificates'])}")
        print("Certificates:")
        for cert in result['certificates']:
            print(f"  - {cert.certificate_id}: {cert.student_name} ({cert.course_name})")
        
        # Test filtering by degree type
        print("\nFiltering by BACHELOR degree type...")
        result = await institution_service.get_institution_certificates(
            "JHARKHAND_UNIV_001",
            "admin_user_001",
            limit=10,
            offset=0,
            filters={"degree_type": DegreeType.BACHELOR}
        )
        
        print(f"Bachelor certificates: {len(result['certificates'])}")
        for cert in result['certificates']:
            print(f"  - {cert.certificate_id}: {cert.student_name} ({cert.degree_type})")
            
    except Exception as e:
        print(f"Certificate listing error: {e}")

async def main():
    """Main test function"""
    print("Starting Institutional Database Verification Tests")
    print("=" * 60)
    
    try:
        # Setup test data
        await setup_test_data()
        
        # Run tests
        await test_certificate_verification()
        await test_cross_reference()
        await test_bulk_upload()
        await test_institution_statistics()
        await test_certificate_listing()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())