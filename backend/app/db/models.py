from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
from bson import ObjectId

# Custom ObjectId field for MongoDB compatibility
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, field_schema):
        field_schema.update(type="string")
        return field_schema

# Base model with MongoDB ID handling
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    
    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

# Enums for better type safety
class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    SUSPICIOUS = "SUSPICIOUS"
    EXPIRED = "EXPIRED"

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    INSTITUTION = "INSTITUTION"
    EMPLOYER = "EMPLOYER"
    GOVERNMENT = "GOVERNMENT"
    STUDENT = "STUDENT"

class InstitutionType(str, Enum):
    UNIVERSITY = "UNIVERSITY"
    COLLEGE = "COLLEGE"
    INSTITUTE = "INSTITUTE"
    SCHOOL = "SCHOOL"
    TRAINING_CENTER = "TRAINING_CENTER"

class DegreeType(str, Enum):
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    DOCTORATE = "DOCTORATE"
    DIPLOMA = "DIPLOMA"
    CERTIFICATE = "CERTIFICATE"
    PROFESSIONAL = "PROFESSIONAL"

class BlacklistType(str, Enum):
    CERTIFICATE = "CERTIFICATE"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    INSTITUTION = "INSTITUTION"

class BlacklistStatus(str, Enum):
    ACTIVE = "ACTIVE"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"

# Certificate model - comprehensive certificate data
class Certificate(MongoBaseModel):
    certificate_id: str = Field(..., description="Unique certificate identifier")
    student_name: str = Field(..., description="Full name of the student")
    roll_number: str = Field(..., description="Student roll number or ID")
    institution_id: str = Field(..., description="Institution that issued the certificate")
    course_name: str = Field(..., description="Name of the course or program")
    degree_type: DegreeType = Field(..., description="Type of degree or certification")
    graduation_date: datetime = Field(..., description="Date of graduation or completion")
    issue_date: datetime = Field(..., description="Date when certificate was issued")
    
    # Academic details
    grades: Dict[str, Any] = Field(default_factory=dict, description="Grades, marks, or GPA details")
    duration: Optional[str] = Field(None, description="Course duration (e.g., '4 years')")
    specialization: Optional[str] = Field(None, description="Area of specialization")
    honors: Optional[List[str]] = Field(default_factory=list, description="Honors or distinctions")
    
    # Certificate metadata
    certificate_number: str = Field(..., description="Official certificate number")
    serial_number: Optional[str] = Field(None, description="Serial number if different from certificate number")
    batch_year: Optional[int] = Field(None, description="Batch or academic year")
    
    # Verification details
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    verification_score: float = Field(default=0.0, description="Confidence score (0-1)")
    tamper_flags: List[str] = Field(default_factory=list, description="List of detected tampering indicators")
    verification_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed verification results")
    
    # File information
    file_hash: str = Field(..., description="SHA-256 hash of the certificate file")
    file_path: Optional[str] = Field(None, description="Path to stored certificate file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_type: Optional[str] = Field(None, description="File MIME type")
    
    # Digital signatures and blockchain
    digital_signature: Optional[str] = Field(None, description="Digital signature if available")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain transaction hash")
    qr_code_data: Optional[str] = Field(None, description="QR code data for verification")
    
    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User ID who created the record")
    last_verified_at: Optional[datetime] = Field(None, description="Last verification timestamp")
    verification_count: int = Field(default=0, description="Number of times verified")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional certificate metadata")
    
    @validator('verification_score')
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Verification score must be between 0 and 1')
        return v

# Institution model - educational institutions
class Institution(MongoBaseModel):
    institution_id: str = Field(..., description="Unique institution identifier")
    name: str = Field(..., description="Official institution name")
    short_name: Optional[str] = Field(None, description="Short name or abbreviation")
    type: InstitutionType = Field(..., description="Type of institution")
    
    # Contact and location information
    address: Dict[str, str] = Field(default_factory=dict, description="Complete address details")
    contact_info: Dict[str, str] = Field(default_factory=dict, description="Contact information")
    website: Optional[str] = Field(None, description="Official website URL")
    
    # Accreditation and authorization
    accreditation_status: str = Field(..., description="Accreditation status")
    accreditation_body: Optional[str] = Field(None, description="Accrediting organization")
    accreditation_date: Optional[datetime] = Field(None, description="Date of accreditation")
    license_number: Optional[str] = Field(None, description="Government license number")
    
    # Authorized personnel
    authorized_signatories: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of authorized signatories with their details"
    )
    admin_users: List[str] = Field(default_factory=list, description="Institution admin user IDs")
    
    # Certificate management
    certificate_templates: List[str] = Field(
        default_factory=list, 
        description="List of certificate template IDs"
    )
    certificate_numbering_pattern: Optional[str] = Field(
        None, 
        description="Pattern for certificate numbering"
    )
    
    # API and integration settings
    api_endpoints: Optional[Dict[str, str]] = Field(
        None, 
        description="API endpoints for external verification"
    )
    api_key: Optional[str] = Field(None, description="API key for external access")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    
    # Status and settings
    is_active: bool = Field(default=True, description="Whether institution is active")
    verification_enabled: bool = Field(default=True, description="Whether verification is enabled")
    auto_verify: bool = Field(default=False, description="Whether to auto-verify certificates")
    
    # Statistics
    total_certificates: int = Field(default=0, description="Total certificates issued")
    verified_certificates: int = Field(default=0, description="Number of verified certificates")
    
    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User ID who created the institution")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional institution metadata")

# Verification record model - detailed verification logs
class VerificationRecord(MongoBaseModel):
    verification_id: str = Field(..., description="Unique verification identifier")
    certificate_id: str = Field(..., description="Certificate ID that was verified")
    
    # Requester information
    requester_id: Optional[str] = Field(None, description="User ID of the requester")
    requester_type: UserRole = Field(..., description="Type of entity requesting verification")
    requester_organization: Optional[str] = Field(None, description="Organization of the requester")
    
    # Verification details
    verification_method: str = Field(..., description="Method used for verification")
    verification_steps: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Detailed steps performed during verification"
    )
    
    # Results
    result: Dict[str, Any] = Field(..., description="Comprehensive verification results")
    status: VerificationStatus = Field(..., description="Overall verification status")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    processing_time: float = Field(..., description="Processing time in seconds")
    
    # Detected issues
    flags_detected: List[str] = Field(default_factory=list, description="List of issues detected")
    tamper_indicators: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Specific tampering indicators found"
    )
    anomalies: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Anomalies detected during verification"
    )
    
    # Technical details
    ocr_confidence: Optional[float] = Field(None, description="OCR extraction confidence")
    ai_model_version: Optional[str] = Field(None, description="AI model version used")
    verification_algorithms: List[str] = Field(
        default_factory=list, 
        description="Algorithms used in verification"
    )
    
    # Request metadata
    verification_date: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None, description="IP address of requester")
    user_agent: Optional[str] = Field(None, description="User agent string")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # Additional context
    purpose: Optional[str] = Field(None, description="Purpose of verification")
    notes: Optional[str] = Field(None, description="Additional notes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v

# User model - system users with role-based access
class User(MongoBaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    hashed_password: str = Field(..., description="Hashed password")
    
    # Personal information
    full_name: str = Field(..., description="Full name of the user")
    phone_number: Optional[str] = Field(None, description="Phone number")
    
    # Role and permissions
    role: UserRole = Field(..., description="User role in the system")
    permissions: List[str] = Field(default_factory=list, description="Specific permissions")
    organization: Optional[str] = Field(None, description="Organization or company name")
    institution_id: Optional[str] = Field(None, description="Associated institution ID")
    
    # Account status
    is_active: bool = Field(default=True, description="Whether account is active")
    is_verified: bool = Field(default=False, description="Whether email is verified")
    email_verified_at: Optional[datetime] = Field(None, description="Email verification timestamp")
    
    # Security settings
    two_factor_enabled: bool = Field(default=False, description="Whether 2FA is enabled")
    two_factor_secret: Optional[str] = Field(None, description="2FA secret key")
    failed_login_attempts: int = Field(default=0, description="Number of failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Account lock expiration")
    
    # Usage statistics
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(default=0, description="Total number of logins")
    verification_count: int = Field(default=0, description="Number of verifications performed")
    monthly_verification_limit: int = Field(default=100, description="Monthly verification limit")
    
    # Audit trail
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User ID who created this account")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")

# Blacklist model - for flagged certificates, persons, or organizations
class BlacklistEntry(MongoBaseModel):
    entry_id: str = Field(..., description="Unique blacklist entry identifier")
    type: BlacklistType = Field(..., description="Type of blacklist entry")
    identifier: str = Field(..., description="The identifier being blacklisted")
    
    # Blacklist details
    reason: str = Field(..., description="Reason for blacklisting")
    description: Optional[str] = Field(None, description="Detailed description")
    severity: str = Field(default="MEDIUM", description="Severity level (LOW, MEDIUM, HIGH, CRITICAL)")
    
    # Evidence and documentation
    evidence: List[str] = Field(default_factory=list, description="List of evidence file paths or URLs")
    supporting_documents: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Supporting documents with metadata"
    )
    related_cases: List[str] = Field(default_factory=list, description="Related blacklist entry IDs")
    
    # Administrative details
    reported_by: str = Field(..., description="User ID who reported/created the entry")
    reviewed_by: Optional[str] = Field(None, description="User ID who reviewed the entry")
    approved_by: Optional[str] = Field(None, description="User ID who approved the blacklisting")
    
    # Status and lifecycle
    status: BlacklistStatus = Field(default=BlacklistStatus.UNDER_REVIEW)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    # Impact tracking
    affected_certificates: List[str] = Field(
        default_factory=list, 
        description="List of certificate IDs affected"
    )
    verification_blocks: int = Field(default=0, description="Number of verifications blocked")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional blacklist metadata")

# Additional system models

# Certificate template model - for institution certificate templates
class CertificateTemplate(MongoBaseModel):
    template_id: str = Field(..., description="Unique template identifier")
    institution_id: str = Field(..., description="Institution that owns this template")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    
    # Template structure
    fields: List[Dict[str, Any]] = Field(..., description="Template field definitions")
    layout: Dict[str, Any] = Field(..., description="Template layout configuration")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Field validation rules")
    
    # Template metadata
    version: str = Field(default="1.0", description="Template version")
    is_active: bool = Field(default=True, description="Whether template is active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# System audit log model
class AuditLog(MongoBaseModel):
    log_id: str = Field(..., description="Unique log entry identifier")
    user_id: Optional[str] = Field(None, description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of the affected resource")
    
    # Action details
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changes made")
    
    # Request metadata
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    session_id: Optional[str] = Field(None, description="Session ID")
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

# System configuration model
class SystemConfig(MongoBaseModel):
    config_id: str = Field(..., description="Configuration identifier")
    category: str = Field(..., description="Configuration category")
    key: str = Field(..., description="Configuration key")
    value: Union[str, int, float, bool, Dict, List] = Field(..., description="Configuration value")
    
    # Metadata
    description: Optional[str] = Field(None, description="Configuration description")
    is_sensitive: bool = Field(default=False, description="Whether value is sensitive")
    is_system: bool = Field(default=False, description="Whether it's a system configuration")
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = Field(None, description="User who last updated")

# Request and response models

class CertificateCreate(BaseModel):
    certificate_id: str
    student_name: str
    roll_number: str
    institution_id: str
    course_name: str
    degree_type: DegreeType
    graduation_date: datetime
    issue_date: datetime
    grades: Optional[Dict[str, Any]] = None
    certificate_number: str
    file_hash: str
    metadata: Optional[Dict[str, Any]] = None

class CertificateUpdate(BaseModel):
    student_name: Optional[str] = None
    course_name: Optional[str] = None
    grades: Optional[Dict[str, Any]] = None
    verification_status: Optional[VerificationStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class CertificateResponse(BaseModel):
    certificate_id: str
    student_name: str
    roll_number: str
    institution_id: str
    course_name: str
    degree_type: DegreeType
    graduation_date: datetime
    issue_date: datetime
    grades: Optional[Dict[str, Any]] = None
    certificate_number: str
    verification_status: VerificationStatus
    verification_score: float
    tamper_flags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class InstitutionCreate(BaseModel):
    institution_id: str
    name: str
    type: InstitutionType
    address: Dict[str, str]
    contact_info: Dict[str, str]
    accreditation_status: str

class InstitutionResponse(BaseModel):
    institution_id: str
    name: str
    type: InstitutionType
    address: Dict[str, str]
    contact_info: Dict[str, str]
    accreditation_status: str
    is_active: bool
    verification_enabled: bool
    total_certificates: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    user_id: str
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    organization: Optional[str] = None
    institution_id: Optional[str] = None

class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    role: UserRole
    organization: Optional[str] = None
    institution_id: Optional[str] = None
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    verification_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VerificationRequest(BaseModel):
    certificate_id: Optional[str] = None
    file_upload: Optional[str] = None  # File path or base64 data
    requester_type: UserRole
    purpose: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class VerificationResult(BaseModel):
    verification_id: str
    status: VerificationStatus
    confidence_score: float
    certificate_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    flags_detected: List[str] = Field(default_factory=list)
    tamper_indicators: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time: float
    verification_date: datetime
    
    class Config:
        from_attributes = True

class BlacklistCreate(BaseModel):
    type: BlacklistType
    identifier: str
    reason: str
    description: Optional[str] = None
    severity: str = "MEDIUM"
    evidence: Optional[List[str]] = None

class BlacklistResponse(BaseModel):
    entry_id: str
    type: BlacklistType
    identifier: str
    reason: str
    severity: str
    status: BlacklistStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
# Blockchain and Digital Signature Models

class BlockchainRecord(MongoBaseModel):
    """Blockchain record for certificate hash storage"""
    record_id: str = Field(..., description="Unique blockchain record ID")
    certificate_hash: str = Field(..., description="SHA256 hash of certificate")
    transaction_id: str = Field(..., description="Blockchain transaction ID")
    block_hash: str = Field(..., description="Block hash containing the transaction")
    block_number: int = Field(..., description="Block number in blockchain")
    network: str = Field(..., description="Blockchain network (ETHEREUM, POLYGON, etc.)")
    confirmation_count: int = Field(default=0, description="Number of confirmations")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection = "blockchain_records"

class DigitalSignatureRecord(MongoBaseModel):
    """Digital signature record for certificates"""
    signature_id: str = Field(..., description="Unique signature ID")
    certificate_id: str = Field(..., description="Associated certificate ID")
    signature: str = Field(..., description="Base64 encoded digital signature")
    algorithm: str = Field(..., description="Signature algorithm used")
    public_key: str = Field(..., description="Public key for verification")
    signer_id: str = Field(..., description="ID of the signer")
    certificate_hash: str = Field(..., description="Hash of signed certificate")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_valid: bool = Field(default=True, description="Signature validity status")
    
    class Config:
        collection = "digital_signatures"

class QRCodeRecord(MongoBaseModel):
    """QR code record for certificate verification"""
    qr_id: str = Field(..., description="Unique QR code ID")
    certificate_id: str = Field(..., description="Associated certificate ID")
    qr_data: str = Field(..., description="QR code data/content")
    verification_url: str = Field(..., description="URL for verification")
    expiry_date: Optional[datetime] = Field(None, description="QR code expiry date")
    scan_count: int = Field(default=0, description="Number of times scanned")
    is_active: bool = Field(default=True, description="QR code active status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection = "qr_codes"

# Request/Response models for blockchain operations

class BlockchainVerificationRequest(BaseModel):
    certificate_hash: str
    transaction_id: Optional[str] = None
    network: Optional[str] = None

class BlockchainVerificationResponse(BaseModel):
    found_on_blockchain: bool
    verification_status: str
    transaction_id: Optional[str] = None
    block_hash: Optional[str] = None
    block_number: Optional[int] = None
    network: Optional[str] = None
    confirmation_count: int = 0
    immutable: bool = False
    verification_timestamp: str
    message: str

class DigitalSignatureRequest(BaseModel):
    certificate_hash: str
    signer_id: str
    private_key_pem: Optional[str] = None

class DigitalSignatureResponse(BaseModel):
    signature: str
    algorithm: str
    public_key: str
    signer_id: str
    timestamp: str
    certificate_hash: str

class SignatureVerificationRequest(BaseModel):
    signature: str
    algorithm: str
    public_key: str
    certificate_hash: str
    signer_id: str
    timestamp: str

class SignatureVerificationResponse(BaseModel):
    signature_valid: bool
    hash_match: bool
    signature_expired: bool
    signature_age_days: int
    signer_id: str
    algorithm: str
    verification_message: str
    verification_timestamp: str
    overall_valid: bool

class CertificateIntegrityRequest(BaseModel):
    certificate_data: Dict[str, Any]
    expected_hash: Optional[str] = None
    signature: Optional[Dict[str, Any]] = None
    blockchain_verification: bool = True

class CertificateIntegrityResponse(BaseModel):
    certificate_id: str
    hash_verification: Dict[str, Any]
    signature_verification: Dict[str, Any]
    blockchain_verification: Dict[str, Any]
    overall_integrity: bool
    integrity_score: float
    verification_timestamp: str