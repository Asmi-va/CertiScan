from typing import Dict, Any, Optional
from datetime import datetime

from app.db.database import get_collection
from app.db.models import VerificationResult

async def verify_certificate_data(
    extracted_data: Dict[str, Any],
    file_path: str,
    institution_id: Optional[str] = None,
    tamper_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Verify extracted certificate data against database records."""
    result = {
        "status": "FLAG",  # Default to FLAG, change to PASS if verified
        "details": {},
        "tampered_areas": []
    }
    
    # Extract certificate ID
    cert_id = extracted_data.get("cert_id")
    if not cert_id:
        result["details"]["cert_id_missing"] = "Certificate ID could not be extracted"
        return result
    
    result["cert_id"] = cert_id
    
    # Check if certificate is blacklisted
    blacklist_collection = await get_collection("blacklist")
    blacklisted = await blacklist_collection.find_one({"cert_id": cert_id})
    
    if blacklisted:
        result["details"]["blacklisted"] = {
            "reason": blacklisted.get("reason", "Unknown reason"),
            "blacklisted_at": blacklisted.get("blacklisted_at", datetime.utcnow())
        }
        return result
    
    # Get certificate from database
    certificates_collection = await get_collection("certificates")
    db_certificate = await certificates_collection.find_one({"cert_id": cert_id})
    
    if not db_certificate:
        result["details"]["not_found"] = "Certificate not found in database"
        return result
    
    # If institution_id is provided, check if it matches
    if institution_id and db_certificate.get("institution_id") != institution_id:
        result["details"]["institution_mismatch"] = "Certificate belongs to a different institution"
        return result
    
    # Compare extracted data with database record
    mismatches = []
    
    # Check name
    if extracted_data.get("name") and db_certificate.get("name"):
        if not strings_similar(extracted_data["name"], db_certificate["name"]):
            mismatches.append("name")
            result["details"]["name_mismatch"] = {
                "extracted": extracted_data["name"],
                "expected": db_certificate["name"]
            }
    
    # Check roll number
    if extracted_data.get("roll_no") and db_certificate.get("roll_no"):
        if not strings_similar(extracted_data["roll_no"], db_certificate["roll_no"]):
            mismatches.append("roll_no")
            result["details"]["roll_no_mismatch"] = {
                "extracted": extracted_data["roll_no"],
                "expected": db_certificate["roll_no"]
            }
    
    # Check course
    if extracted_data.get("course") and db_certificate.get("course"):
        if not strings_similar(extracted_data["course"], db_certificate["course"]):
            mismatches.append("course")
            result["details"]["course_mismatch"] = {
                "extracted": extracted_data["course"],
                "expected": db_certificate["course"]
            }
    
    # Check marks
    if extracted_data.get("marks") and db_certificate.get("marks"):
        if not strings_similar(extracted_data["marks"], db_certificate["marks"]):
            mismatches.append("marks")
            result["details"]["marks_mismatch"] = {
                "extracted": extracted_data["marks"],
                "expected": db_certificate["marks"]
            }
    
    # Check file hash if available
    if db_certificate.get("file_hash") and tamper_result and tamper_result.get("details", {}).get("file_hash"):
        if db_certificate["file_hash"] != tamper_result["details"]["file_hash"]:
            mismatches.append("file_hash")
            result["details"]["hash_mismatch"] = {
                "extracted": tamper_result["details"]["file_hash"],
                "expected": db_certificate["file_hash"]
            }
    
    # Check for tampering
    if tamper_result and tamper_result.get("is_tampered", False):
        result["details"]["tamper_detection"] = {
            "is_tampered": True,
            "confidence": tamper_result.get("confidence", 0.0),
            "methods": tamper_result.get("methods", [])
        }
        result["tampered_areas"] = tamper_result.get("tampered_areas", [])
        mismatches.append("tampered")
    
    # Determine final result
    if not mismatches:
        result["status"] = "PASS"
        result["details"]["message"] = "Certificate verified successfully"
    else:
        result["details"]["message"] = f"Certificate verification failed: {', '.join(mismatches)}"
    
    # Add certificate data to result
    result["details"]["certificate"] = {
        "cert_id": db_certificate.get("cert_id"),
        "name": db_certificate.get("name"),
        "roll_no": db_certificate.get("roll_no"),
        "course": db_certificate.get("course"),
        "issue_date": db_certificate.get("issue_date"),
        "institution_id": db_certificate.get("institution_id")
    }
    
    return result

def strings_similar(str1: str, str2: str, threshold: float = 0.8) -> bool:
    """Check if two strings are similar using Levenshtein distance."""
    # Convert to lowercase and strip whitespace
    s1 = str1.lower().strip()
    s2 = str2.lower().strip()
    
    # If strings are identical, return True
    if s1 == s2:
        return True
    
    # Calculate Levenshtein distance
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    # Calculate similarity ratio
    if max_len == 0:
        return True  # Both strings are empty
    
    similarity = 1.0 - (distance / max_len)
    
    return similarity >= threshold

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]