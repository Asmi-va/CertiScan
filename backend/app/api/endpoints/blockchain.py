"""
Blockchain and Digital Signature API endpoints.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from app.services.blockchain_service import blockchain_service, BlockchainNetwork, SignatureAlgorithm
from app.middleware.auth_middleware import (
    get_current_user, get_current_active_user, require_read_certificates,
    require_write_certificates, get_request_context
)
from app.db.models import (
    BlockchainVerificationRequest, BlockchainVerificationResponse,
    DigitalSignatureRequest, DigitalSignatureResponse,
    SignatureVerificationRequest, SignatureVerificationResponse,
    CertificateIntegrityRequest, CertificateIntegrityResponse,
    UserRole
)

router = APIRouter()

# Additional request/response models
class CreateCertificateHashRequest(BaseModel):
    certificate_data: Dict[str, Any]
    include_metadata: bool = True

class CertificateHashResponse(BaseModel):
    certificate_id: str
    sha256_hash: str
    merkle_root: str
    metadata_hash: str
    content_hash: str
    timestamp: str

class StoreOnBlockchainRequest(BaseModel):
    certificate_hash: str
    network: str = "PRIVATE"
    metadata: Optional[Dict[str, Any]] = None

class BlockchainTransactionResponse(BaseModel):
    transaction_id: str
    block_hash: str
    block_number: int
    network: str
    gas_used: Optional[int] = None
    transaction_fee: Optional[float] = None
    confirmation_count: int
    timestamp: str

class CompleteBlockchainCertificateRequest(BaseModel):
    certificate_data: Dict[str, Any]
    signer_id: str
    network: str = "PRIVATE"
    private_key_pem: Optional[str] = None

class CompleteBlockchainCertificateResponse(BaseModel):
    certificate_id: str
    cryptographic_hash: Dict[str, str]
    digital_signature: Dict[str, Any]
    blockchain_record: Dict[str, Any]
    immutability_status: str
    created_at: str

class BlockchainStatisticsResponse(BaseModel):
    total_records: int
    network_distribution: Dict[str, int]
    recent_activity: list
    average_confirmation_time: float
    immutable_certificates: int
    pending_confirmations: int

@router.post("/hash/create", response_model=CertificateHashResponse)
async def create_certificate_hash(
    request: CreateCertificateHashRequest,
    current_user: dict = Depends(require_write_certificates)
):
    """Create cryptographic hash for certificate data."""
    try:
        certificate_hash = await blockchain_service.create_certificate_hash(
            certificate_data=request.certificate_data,
            include_metadata=request.include_metadata
        )
        
        return CertificateHashResponse(
            certificate_id=certificate_hash.certificate_id,
            sha256_hash=certificate_hash.sha256_hash,
            merkle_root=certificate_hash.merkle_root,
            metadata_hash=certificate_hash.metadata_hash,
            content_hash=certificate_hash.content_hash,
            timestamp=certificate_hash.timestamp.isoformat()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create certificate hash: {str(e)}"
        )

@router.post("/signature/generate", response_model=DigitalSignatureResponse)
async def generate_digital_signature(
    request: DigitalSignatureRequest,
    current_user: dict = Depends(require_write_certificates)
):
    """Generate digital signature for certificate hash."""
    try:
        # Verify signer permissions
        if current_user["role"] not in [UserRole.ADMIN, UserRole.INSTITUTION]:
            if request.signer_id != current_user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Can only sign certificates with your own ID"
                )
        
        digital_signature = await blockchain_service.generate_digital_signature(
            certificate_hash=request.certificate_hash,
            signer_id=request.signer_id,
            private_key_pem=request.private_key_pem
        )
        
        return DigitalSignatureResponse(
            signature=digital_signature.signature,
            algorithm=digital_signature.algorithm.value,
            public_key=digital_signature.public_key,
            signer_id=digital_signature.signer_id,
            timestamp=digital_signature.timestamp.isoformat(),
            certificate_hash=digital_signature.certificate_hash
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate digital signature: {str(e)}"
        )

@router.post("/signature/verify", response_model=SignatureVerificationResponse)
async def verify_digital_signature(
    request: SignatureVerificationRequest,
    current_user: dict = Depends(require_read_certificates)
):
    """Verify digital signature authenticity."""
    try:
        from app.services.blockchain_service import DigitalSignature
        from datetime import datetime
        
        # Reconstruct signature object
        signature = DigitalSignature(
            signature=request.signature,
            algorithm=SignatureAlgorithm(request.algorithm),
            public_key=request.public_key,
            timestamp=datetime.fromisoformat(request.timestamp.replace('Z', '+00:00')),
            signer_id=request.signer_id,
            certificate_hash=request.certificate_hash
        )
        
        verification_result = await blockchain_service.verify_digital_signature(
            signature=signature,
            certificate_hash=request.certificate_hash
        )
        
        return SignatureVerificationResponse(**verification_result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify digital signature: {str(e)}"
        )

@router.post("/store", response_model=BlockchainTransactionResponse)
async def store_on_blockchain(
    request: StoreOnBlockchainRequest,
    current_user: dict = Depends(require_write_certificates)
):
    """Store certificate hash on blockchain."""
    try:
        # Validate network
        try:
            network = BlockchainNetwork(request.network.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain network: {request.network}"
            )
        
        blockchain_transaction = await blockchain_service.store_on_blockchain(
            certificate_hash=request.certificate_hash,
            network=network,
            metadata=request.metadata
        )
        
        return BlockchainTransactionResponse(
            transaction_id=blockchain_transaction.transaction_id,
            block_hash=blockchain_transaction.block_hash,
            block_number=blockchain_transaction.block_number,
            network=blockchain_transaction.network.value,
            gas_used=blockchain_transaction.gas_used,
            transaction_fee=blockchain_transaction.transaction_fee,
            confirmation_count=blockchain_transaction.confirmation_count,
            timestamp=blockchain_transaction.timestamp.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store on blockchain: {str(e)}"
        )

@router.post("/verify", response_model=BlockchainVerificationResponse)
async def verify_blockchain_record(
    request: BlockchainVerificationRequest,
    current_user: dict = Depends(require_read_certificates)
):
    """Verify certificate hash exists on blockchain."""
    try:
        verification_result = await blockchain_service.verify_blockchain_record(
            certificate_hash=request.certificate_hash,
            transaction_id=request.transaction_id
        )
        
        return BlockchainVerificationResponse(**verification_result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify blockchain record: {str(e)}"
        )

@router.post("/certificate/create-complete", response_model=CompleteBlockchainCertificateResponse)
async def create_complete_blockchain_certificate(
    request: CompleteBlockchainCertificateRequest,
    current_user: dict = Depends(require_write_certificates)
):
    """Complete workflow: Create certificate with hash, signature, and blockchain storage."""
    try:
        # Verify signer permissions
        if current_user["role"] not in [UserRole.ADMIN, UserRole.INSTITUTION]:
            if request.signer_id != current_user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Can only sign certificates with your own ID"
                )
        
        # Validate network
        try:
            network = BlockchainNetwork(request.network.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain network: {request.network}"
            )
        
        complete_result = await blockchain_service.create_certificate_with_blockchain(
            certificate_data=request.certificate_data,
            signer_id=request.signer_id,
            network=network,
            private_key_pem=request.private_key_pem
        )
        
        return CompleteBlockchainCertificateResponse(**complete_result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create complete blockchain certificate: {str(e)}"
        )

@router.post("/certificate/verify-integrity", response_model=CertificateIntegrityResponse)
async def verify_certificate_integrity(
    request: CertificateIntegrityRequest,
    current_user: dict = Depends(require_read_certificates)
):
    """Comprehensive certificate integrity verification."""
    try:
        # Convert signature dict to DigitalSignature object if provided
        signature_obj = None
        if request.signature:
            from app.services.blockchain_service import DigitalSignature
            from datetime import datetime
            
            signature_obj = DigitalSignature(
                signature=request.signature["signature"],
                algorithm=SignatureAlgorithm(request.signature["algorithm"]),
                public_key=request.signature["public_key"],
                timestamp=datetime.fromisoformat(request.signature["timestamp"].replace('Z', '+00:00')),
                signer_id=request.signature["signer_id"],
                certificate_hash=request.signature["certificate_hash"]
            )
        
        verification_results = await blockchain_service.verify_certificate_integrity(
            certificate_data=request.certificate_data,
            expected_hash=request.expected_hash,
            signature=signature_obj,
            blockchain_verification=request.blockchain_verification
        )
        
        return CertificateIntegrityResponse(**verification_results)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify certificate integrity: {str(e)}"
        )

@router.get("/statistics", response_model=BlockchainStatisticsResponse)
async def get_blockchain_statistics(
    current_user: dict = Depends(get_current_active_user)
):
    """Get blockchain integration statistics."""
    try:
        # Check permissions for statistics access
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or government access required for statistics"
            )
        
        statistics = await blockchain_service.get_blockchain_statistics()
        return BlockchainStatisticsResponse(**statistics)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blockchain statistics: {str(e)}"
        )

@router.get("/networks")
async def get_supported_networks(
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of supported blockchain networks."""
    networks = [
        {
            "name": network.value,
            "description": f"{network.value} blockchain network",
            "supported": True
        }
        for network in BlockchainNetwork
    ]
    
    return {
        "supported_networks": networks,
        "default_network": "PRIVATE",
        "message": "List of supported blockchain networks"
    }

@router.get("/algorithms")
async def get_supported_algorithms(
    current_user: dict = Depends(get_current_active_user)
):
    """Get list of supported digital signature algorithms."""
    algorithms = [
        {
            "name": algorithm.value,
            "description": f"{algorithm.value} digital signature algorithm",
            "supported": True
        }
        for algorithm in SignatureAlgorithm
    ]
    
    return {
        "supported_algorithms": algorithms,
        "default_algorithm": "RSA_SHA256",
        "message": "List of supported digital signature algorithms"
    }

# QR Code generation endpoints
@router.post("/qr-code/generate")
async def generate_qr_code(
    certificate_id: str,
    verification_url: Optional[str] = None,
    current_user: dict = Depends(require_write_certificates)
):
    """Generate QR code for certificate verification."""
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        # Create verification URL
        if not verification_url:
            verification_url = f"https://verify.certificates.gov.in/verify/{certificate_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "certificate_id": certificate_id,
            "qr_code": f"data:image/png;base64,{img_str}",
            "verification_url": verification_url,
            "message": "QR code generated successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate QR code: {str(e)}"
        )