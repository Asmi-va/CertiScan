"""
Blockchain and Digital Signature Service

Implements blockchain integration for certificate immutability, digital signature verification,
cryptographic hash validation, and distributed ledger support for certificate authenticity.

Requirements: 2.4, 4.3, 4.4
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import base64
import secrets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidSignature

from ..db.database import get_database
from ..db.models import Certificate, Institution, BlockchainRecord
from ..core.config import settings
from ..utils.exceptions import ProcessingError, ValidationError, SecurityError

logger = logging.getLogger(__name__)

class BlockchainNetwork(Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ETHEREUM"
    POLYGON = "POLYGON"
    HYPERLEDGER = "HYPERLEDGER"
    PRIVATE = "PRIVATE"

class SignatureAlgorithm(Enum):
    """Supported digital signature algorithms"""
    RSA_SHA256 = "RSA_SHA256"
    ECDSA_SHA256 = "ECDSA_SHA256"
    ED25519 = "ED25519"

@dataclass
class DigitalSignature:
    """Digital signature data structure"""
    signature: str
    algorithm: SignatureAlgorithm
    public_key: str
    timestamp: datetime
    signer_id: str
    certificate_hash: str

@dataclass
class BlockchainTransaction:
    """Blockchain transaction data structure"""
    transaction_id: str
    block_hash: str
    block_number: int
    network: BlockchainNetwork
    gas_used: Optional[int]
    transaction_fee: Optional[float]
    confirmation_count: int
    timestamp: datetime

@dataclass
class CertificateHash:
    """Certificate cryptographic hash data"""
    certificate_id: str
    sha256_hash: str
    merkle_root: str
    metadata_hash: str
    content_hash: str
    timestamp: datetime

class BlockchainService:
    """Comprehensive blockchain and digital signature service"""
    
    def __init__(self):
        self.db = None
        self.blockchain_records_collection = None
        self.certificates_collection = None
        self.institutions_collection = None
        
        # Blockchain configuration
        self.config = {
            "networks": {
                "ethereum": {
                    "rpc_url": settings.ETHEREUM_RPC_URL if hasattr(settings, 'ETHEREUM_RPC_URL') else None,
                    "contract_address": settings.ETHEREUM_CONTRACT if hasattr(settings, 'ETHEREUM_CONTRACT') else None,
                    "gas_limit": 100000
                },
                "polygon": {
                    "rpc_url": settings.POLYGON_RPC_URL if hasattr(settings, 'POLYGON_RPC_URL') else None,
                    "contract_address": settings.POLYGON_CONTRACT if hasattr(settings, 'POLYGON_CONTRACT') else None,
                    "gas_limit": 80000
                }
            },
            "signature_settings": {
                "key_size": 2048,
                "hash_algorithm": "SHA256",
                "signature_validity_days": 365
            },
            "hash_settings": {
                "algorithms": ["SHA256", "SHA3-256", "BLAKE2b"],
                "merkle_tree_depth": 10
            }
        }
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = await get_database()
            self.blockchain_records_collection = self.db.blockchain_records
            self.certificates_collection = self.db.certificates
            self.institutions_collection = self.db.institutions
    
    async def create_certificate_hash(
        self,
        certificate_data: Dict[str, Any],
        include_metadata: bool = True
    ) -> CertificateHash:
        """
        Create comprehensive cryptographic hash for certificate
        """
        try:
            certificate_id = certificate_data.get("certificate_id", "")
            
            # Extract core certificate content
            core_content = {
                "student_name": certificate_data.get("student_name", ""),
                "roll_number": certificate_data.get("roll_number", ""),
                "course_name": certificate_data.get("course_name", ""),
                "degree_type": certificate_data.get("degree_type", ""),
                "graduation_date": certificate_data.get("graduation_date", ""),
                "institution_id": certificate_data.get("institution_id", ""),
                "certificate_number": certificate_data.get("certificate_number", "")
            }
            
            # Create content hash
            content_json = json.dumps(core_content, sort_keys=True)
            content_hash = hashlib.sha256(content_json.encode()).hexdigest()
            
            # Create metadata hash if requested
            metadata_hash = ""
            if include_metadata:
                metadata = {
                    "grades": certificate_data.get("grades", {}),
                    "specialization": certificate_data.get("specialization", ""),
                    "duration": certificate_data.get("duration", ""),
                    "issue_date": certificate_data.get("issue_date", ""),
                    "file_hash": certificate_data.get("file_hash", "")
                }
                metadata_json = json.dumps(metadata, sort_keys=True)
                metadata_hash = hashlib.sha256(metadata_json.encode()).hexdigest()
            
            # Create combined hash
            combined_data = content_hash + metadata_hash
            sha256_hash = hashlib.sha256(combined_data.encode()).hexdigest()
            
            # Create Merkle root (simplified - in production, use proper Merkle tree)
            merkle_components = [content_hash, metadata_hash, certificate_id]
            merkle_data = "|".join(merkle_components)
            merkle_root = hashlib.sha256(merkle_data.encode()).hexdigest()
            
            certificate_hash = CertificateHash(
                certificate_id=certificate_id,
                sha256_hash=sha256_hash,
                merkle_root=merkle_root,
                metadata_hash=metadata_hash,
                content_hash=content_hash,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"Certificate hash created for {certificate_id}: {sha256_hash[:16]}...")
            return certificate_hash
            
        except Exception as e:
            logger.error(f"Error creating certificate hash: {str(e)}")
            raise ProcessingError(f"Failed to create certificate hash: {str(e)}")
    
    async def generate_digital_signature(
        self,
        certificate_hash: str,
        signer_id: str,
        private_key_pem: Optional[str] = None
    ) -> DigitalSignature:
        """
        Generate digital signature for certificate hash
        """
        try:
            # Generate or use provided private key
            if private_key_pem:
                private_key = load_pem_private_key(
                    private_key_pem.encode(),
                    password=None
                )
            else:
                # Generate new RSA key pair
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=self.config["signature_settings"]["key_size"]
                )
            
            # Get public key
            public_key = private_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            # Create signature
            signature_bytes = private_key.sign(
                certificate_hash.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Encode signature
            signature_b64 = base64.b64encode(signature_bytes).decode()
            
            digital_signature = DigitalSignature(
                signature=signature_b64,
                algorithm=SignatureAlgorithm.RSA_SHA256,
                public_key=public_key_pem,
                timestamp=datetime.utcnow(),
                signer_id=signer_id,
                certificate_hash=certificate_hash
            )
            
            logger.info(f"Digital signature generated for hash {certificate_hash[:16]}... by {signer_id}")
            return digital_signature
            
        except Exception as e:
            logger.error(f"Error generating digital signature: {str(e)}")
            raise SecurityError(f"Failed to generate digital signature: {str(e)}")
    
    async def verify_digital_signature(
        self,
        signature: DigitalSignature,
        certificate_hash: str
    ) -> Dict[str, Any]:
        """
        Verify digital signature authenticity
        """
        try:
            # Load public key
            public_key = load_pem_public_key(signature.public_key.encode())
            
            # Decode signature
            signature_bytes = base64.b64decode(signature.signature)
            
            # Verify signature
            try:
                public_key.verify(
                    signature_bytes,
                    certificate_hash.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                signature_valid = True
                verification_message = "Digital signature is valid"
            except InvalidSignature:
                signature_valid = False
                verification_message = "Digital signature is invalid"
            
            # Check signature age
            signature_age = datetime.utcnow() - signature.timestamp
            max_age = timedelta(days=self.config["signature_settings"]["signature_validity_days"])
            signature_expired = signature_age > max_age
            
            # Check hash match
            hash_match = signature.certificate_hash == certificate_hash
            
            verification_result = {
                "signature_valid": signature_valid,
                "hash_match": hash_match,
                "signature_expired": signature_expired,
                "signature_age_days": signature_age.days,
                "signer_id": signature.signer_id,
                "algorithm": signature.algorithm.value,
                "verification_message": verification_message,
                "verification_timestamp": datetime.utcnow().isoformat(),
                "overall_valid": signature_valid and hash_match and not signature_expired
            }
            
            logger.info(f"Signature verification completed: {verification_result['overall_valid']}")
            return verification_result
            
        except Exception as e:
            logger.error(f"Error verifying digital signature: {str(e)}")
            return {
                "signature_valid": False,
                "hash_match": False,
                "signature_expired": True,
                "verification_message": f"Verification error: {str(e)}",
                "overall_valid": False
            }
    
    async def store_on_blockchain(
        self,
        certificate_hash: str,
        network: BlockchainNetwork = BlockchainNetwork.PRIVATE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BlockchainTransaction:
        """
        Store certificate hash on blockchain (simulated for demo)
        """
        try:
            await self._ensure_db_connection()
            
            # In production, this would interact with actual blockchain networks
            # For demo purposes, we simulate blockchain storage
            
            # Generate transaction details
            transaction_id = self._generate_transaction_id()
            block_number = await self._get_next_block_number(network)
            block_hash = self._generate_block_hash(certificate_hash, block_number)
            
            # Simulate network-specific parameters
            gas_used = None
            transaction_fee = None
            
            if network in [BlockchainNetwork.ETHEREUM, BlockchainNetwork.POLYGON]:
                gas_used = secrets.randbelow(50000) + 21000  # Simulate gas usage
                transaction_fee = gas_used * 0.00000002  # Simulate fee calculation
            
            blockchain_transaction = BlockchainTransaction(
                transaction_id=transaction_id,
                block_hash=block_hash,
                block_number=block_number,
                network=network,
                gas_used=gas_used,
                transaction_fee=transaction_fee,
                confirmation_count=1,  # Start with 1 confirmation
                timestamp=datetime.utcnow()
            )
            
            # Store blockchain record in database
            blockchain_record = BlockchainRecord(
                record_id=f"BC_{transaction_id}",
                certificate_hash=certificate_hash,
                transaction_id=transaction_id,
                block_hash=block_hash,
                block_number=block_number,
                network=network.value,
                confirmation_count=1,
                metadata=metadata or {},
                created_at=datetime.utcnow()
            )
            
            result = await self.blockchain_records_collection.insert_one(
                blockchain_record.model_dump(by_alias=True)
            )
            blockchain_record.id = result.inserted_id
            
            logger.info(f"Certificate hash stored on {network.value} blockchain: {transaction_id}")
            return blockchain_transaction
            
        except Exception as e:
            logger.error(f"Error storing on blockchain: {str(e)}")
            raise ProcessingError(f"Failed to store on blockchain: {str(e)}")
    
    # Private helper methods
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(8)
        return f"TX_{timestamp}_{random_part}"
    
    async def _get_next_block_number(self, network: BlockchainNetwork) -> int:
        """Get next block number for network"""
        await self._ensure_db_connection()
        
        # Get latest block number for network
        latest_record = await self.blockchain_records_collection.find_one(
            {"network": network.value},
            sort=[("block_number", -1)]
        )
        
        if latest_record:
            return latest_record["block_number"] + 1
        else:
            return 1  # Genesis block
    
    def _generate_block_hash(self, certificate_hash: str, block_number: int) -> str:
        """Generate block hash"""
        block_data = f"{certificate_hash}_{block_number}_{datetime.utcnow().isoformat()}"
        return hashlib.sha256(block_data.encode()).hexdigest()
    
    async def verify_blockchain_record(
        self,
        certificate_hash: str,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify certificate hash exists on blockchain
        """
        try:
            await self._ensure_db_connection()
            
            # Build query
            query = {"certificate_hash": certificate_hash}
            if transaction_id:
                query["transaction_id"] = transaction_id
            
            # Find blockchain record
            blockchain_record = await self.blockchain_records_collection.find_one(query)
            
            if not blockchain_record:
                return {
                    "found_on_blockchain": False,
                    "verification_status": "NOT_FOUND",
                    "message": "Certificate hash not found on blockchain",
                    "verification_timestamp": datetime.utcnow().isoformat()
                }
            
            # Simulate confirmation count increase over time
            record_age = datetime.utcnow() - blockchain_record["created_at"]
            simulated_confirmations = min(100, blockchain_record["confirmation_count"] + (record_age.seconds // 60))
            
            # Update confirmation count
            await self.blockchain_records_collection.update_one(
                {"_id": blockchain_record["_id"]},
                {"$set": {"confirmation_count": simulated_confirmations}}
            )
            
            verification_result = {
                "found_on_blockchain": True,
                "verification_status": "VERIFIED",
                "transaction_id": blockchain_record["transaction_id"],
                "block_hash": blockchain_record["block_hash"],
                "block_number": blockchain_record["block_number"],
                "network": blockchain_record["network"],
                "confirmation_count": simulated_confirmations,
                "created_at": blockchain_record["created_at"].isoformat(),
                "immutable": simulated_confirmations >= 6,  # Consider immutable after 6 confirmations
                "verification_timestamp": datetime.utcnow().isoformat(),
                "message": f"Certificate hash verified on {blockchain_record['network']} blockchain"
            }
            
            logger.info(f"Blockchain verification completed: {verification_result['verification_status']}")
            return verification_result
            
        except Exception as e:
            logger.error(f"Error verifying blockchain record: {str(e)}")
            return {
                "found_on_blockchain": False,
                "verification_status": "ERROR",
                "message": f"Blockchain verification error: {str(e)}",
                "verification_timestamp": datetime.utcnow().isoformat()
            }
    
    async def create_certificate_with_blockchain(
        self,
        certificate_data: Dict[str, Any],
        signer_id: str,
        network: BlockchainNetwork = BlockchainNetwork.PRIVATE,
        private_key_pem: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: Create certificate with hash, signature, and blockchain storage
        """
        try:
            # Step 1: Create certificate hash
            certificate_hash = await self.create_certificate_hash(certificate_data)
            
            # Step 2: Generate digital signature
            digital_signature = await self.generate_digital_signature(
                certificate_hash.sha256_hash,
                signer_id,
                private_key_pem
            )
            
            # Step 3: Store on blockchain
            blockchain_transaction = await self.store_on_blockchain(
                certificate_hash.sha256_hash,
                network,
                {
                    "certificate_id": certificate_data.get("certificate_id", ""),
                    "institution_id": certificate_data.get("institution_id", ""),
                    "signer_id": signer_id
                }
            )
            
            # Step 4: Update certificate with blockchain data
            await self._update_certificate_with_blockchain_data(
                certificate_data.get("certificate_id", ""),
                certificate_hash,
                digital_signature,
                blockchain_transaction
            )
            
            complete_result = {
                "certificate_id": certificate_data.get("certificate_id", ""),
                "cryptographic_hash": {
                    "sha256_hash": certificate_hash.sha256_hash,
                    "merkle_root": certificate_hash.merkle_root,
                    "content_hash": certificate_hash.content_hash,
                    "metadata_hash": certificate_hash.metadata_hash
                },
                "digital_signature": {
                    "signature": digital_signature.signature,
                    "algorithm": digital_signature.algorithm.value,
                    "signer_id": digital_signature.signer_id,
                    "timestamp": digital_signature.timestamp.isoformat()
                },
                "blockchain_record": {
                    "transaction_id": blockchain_transaction.transaction_id,
                    "block_hash": blockchain_transaction.block_hash,
                    "block_number": blockchain_transaction.block_number,
                    "network": blockchain_transaction.network.value,
                    "confirmation_count": blockchain_transaction.confirmation_count
                },
                "immutability_status": "PENDING_CONFIRMATIONS",
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Certificate with blockchain created: {certificate_data.get('certificate_id', '')}")
            return complete_result
            
        except Exception as e:
            logger.error(f"Error creating certificate with blockchain: {str(e)}")
            raise ProcessingError(f"Failed to create certificate with blockchain: {str(e)}")
    
    async def verify_certificate_integrity(
        self,
        certificate_data: Dict[str, Any],
        expected_hash: Optional[str] = None,
        signature: Optional[DigitalSignature] = None,
        blockchain_verification: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive certificate integrity verification
        """
        try:
            verification_results = {
                "certificate_id": certificate_data.get("certificate_id", ""),
                "hash_verification": {},
                "signature_verification": {},
                "blockchain_verification": {},
                "overall_integrity": False,
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
            # Step 1: Hash verification
            current_hash = await self.create_certificate_hash(certificate_data)
            
            if expected_hash:
                hash_match = current_hash.sha256_hash == expected_hash
                verification_results["hash_verification"] = {
                    "current_hash": current_hash.sha256_hash,
                    "expected_hash": expected_hash,
                    "hash_match": hash_match,
                    "message": "Hash verification passed" if hash_match else "Hash mismatch detected"
                }
            else:
                verification_results["hash_verification"] = {
                    "current_hash": current_hash.sha256_hash,
                    "message": "No expected hash provided for comparison"
                }
            
            # Step 2: Digital signature verification
            if signature:
                sig_verification = await self.verify_digital_signature(
                    signature,
                    current_hash.sha256_hash
                )
                verification_results["signature_verification"] = sig_verification
            else:
                verification_results["signature_verification"] = {
                    "message": "No digital signature provided for verification"
                }
            
            # Step 3: Blockchain verification
            if blockchain_verification:
                blockchain_result = await self.verify_blockchain_record(
                    current_hash.sha256_hash
                )
                verification_results["blockchain_verification"] = blockchain_result
            else:
                verification_results["blockchain_verification"] = {
                    "message": "Blockchain verification skipped"
                }
            
            # Step 4: Overall integrity assessment
            hash_valid = verification_results["hash_verification"].get("hash_match", True)
            signature_valid = verification_results["signature_verification"].get("overall_valid", True)
            blockchain_valid = verification_results["blockchain_verification"].get("found_on_blockchain", True)
            
            verification_results["overall_integrity"] = hash_valid and signature_valid and blockchain_valid
            
            # Generate integrity score
            score_components = []
            if "hash_match" in verification_results["hash_verification"]:
                score_components.append(1.0 if hash_valid else 0.0)
            if "overall_valid" in verification_results["signature_verification"]:
                score_components.append(1.0 if signature_valid else 0.0)
            if "found_on_blockchain" in verification_results["blockchain_verification"]:
                score_components.append(1.0 if blockchain_valid else 0.0)
            
            integrity_score = sum(score_components) / len(score_components) if score_components else 0.0
            verification_results["integrity_score"] = integrity_score
            
            logger.info(f"Certificate integrity verification completed: {integrity_score:.2f}")
            return verification_results
            
        except Exception as e:
            logger.error(f"Error verifying certificate integrity: {str(e)}")
            return {
                "certificate_id": certificate_data.get("certificate_id", ""),
                "overall_integrity": False,
                "integrity_score": 0.0,
                "error": str(e),
                "verification_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _update_certificate_with_blockchain_data(
        self,
        certificate_id: str,
        certificate_hash: CertificateHash,
        digital_signature: DigitalSignature,
        blockchain_transaction: BlockchainTransaction
    ):
        """Update certificate record with blockchain data"""
        await self._ensure_db_connection()
        
        blockchain_data = {
            "blockchain_hash": certificate_hash.sha256_hash,
            "merkle_root": certificate_hash.merkle_root,
            "digital_signature": {
                "signature": digital_signature.signature,
                "algorithm": digital_signature.algorithm.value,
                "signer_id": digital_signature.signer_id,
                "public_key": digital_signature.public_key,
                "timestamp": digital_signature.timestamp
            },
            "blockchain_record": {
                "transaction_id": blockchain_transaction.transaction_id,
                "block_hash": blockchain_transaction.block_hash,
                "block_number": blockchain_transaction.block_number,
                "network": blockchain_transaction.network.value,
                "confirmation_count": blockchain_transaction.confirmation_count
            },
            "immutability_timestamp": datetime.utcnow()
        }
        
        await self.certificates_collection.update_one(
            {"certificate_id": certificate_id},
            {"$set": {"blockchain_data": blockchain_data}}
        )
    
    async def get_blockchain_statistics(self) -> Dict[str, Any]:
        """Get blockchain integration statistics"""
        try:
            await self._ensure_db_connection()
            
            # Get total blockchain records
            total_records = await self.blockchain_records_collection.count_documents({})
            
            # Get records by network
            network_pipeline = [
                {"$group": {"_id": "$network", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            
            network_stats = {}
            async for result in self.blockchain_records_collection.aggregate(network_pipeline):
                network_stats[result["_id"]] = result["count"]
            
            # Get recent activity
            recent_records = []
            async for record in self.blockchain_records_collection.find({}).sort("created_at", -1).limit(10):
                recent_records.append({
                    "transaction_id": record["transaction_id"],
                    "network": record["network"],
                    "block_number": record["block_number"],
                    "confirmation_count": record["confirmation_count"],
                    "created_at": record["created_at"].isoformat()
                })
            
            # Calculate average confirmation time (simulated)
            avg_confirmation_time = 2.5  # minutes (simulated)
            
            # Count immutable certificates (6+ confirmations)
            immutable_count = await self.blockchain_records_collection.count_documents({
                "confirmation_count": {"$gte": 6}
            })
            
            # Count pending confirmations
            pending_count = await self.blockchain_records_collection.count_documents({
                "confirmation_count": {"$lt": 6}
            })
            
            statistics = {
                "total_records": total_records,
                "network_distribution": network_stats,
                "recent_activity": recent_records,
                "average_confirmation_time": avg_confirmation_time,
                "immutable_certificates": immutable_count,
                "pending_confirmations": pending_count
            }
            
            logger.info(f"Blockchain statistics retrieved: {total_records} total records")
            return statistics
            
        except Exception as e:
            logger.error(f"Error getting blockchain statistics: {str(e)}")
            return {
                "total_records": 0,
                "network_distribution": {},
                "recent_activity": [],
                "average_confirmation_time": 0.0,
                "immutable_certificates": 0,
                "pending_confirmations": 0,
                "error": str(e)
            }
# Global blockchain service instance
blockchain_service = BlockchainService()