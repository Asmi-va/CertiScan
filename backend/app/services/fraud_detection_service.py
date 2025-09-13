"""
Fraud Detection and Pattern Recognition Service

Implements machine learning models for fraud pattern detection, behavioral analysis,
suspicious activity flagging, and risk scoring algorithms.

Requirements: 3.2, 3.3, 4.1, 4.2
"""

import logging
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

from ..db.database import get_database
from ..db.models import (
    VerificationRecord, Certificate, User, BlacklistEntry,
    VerificationStatus, UserRole, BlacklistType, BlacklistStatus
)
from ..core.config import settings
from ..utils.exceptions import ProcessingError, ValidationError

logger = logging.getLogger(__name__)

class FraudRiskLevel(Enum):
    """Risk levels for fraud detection"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class FraudPattern(Enum):
    """Types of fraud patterns detected"""
    DUPLICATE_SUBMISSION = "DUPLICATE_SUBMISSION"
    RAPID_FIRE_VERIFICATION = "RAPID_FIRE_VERIFICATION"
    SUSPICIOUS_TIMING = "SUSPICIOUS_TIMING"
    GEOGRAPHIC_ANOMALY = "GEOGRAPHIC_ANOMALY"
    BEHAVIORAL_ANOMALY = "BEHAVIORAL_ANOMALY"
    CERTIFICATE_FARMING = "CERTIFICATE_FARMING"
    INSTITUTIONAL_MISMATCH = "INSTITUTIONAL_MISMATCH"
    GRADE_INFLATION_PATTERN = "GRADE_INFLATION_PATTERN"
    TEMPLATE_REUSE = "TEMPLATE_REUSE"
    COORDINATED_FRAUD = "COORDINATED_FRAUD"

@dataclass
class FraudAlert:
    """Fraud detection alert"""
    alert_id: str
    pattern_type: FraudPattern
    risk_level: FraudRiskLevel
    confidence: float
    description: str
    evidence: List[Dict[str, Any]]
    affected_entities: List[str]
    timestamp: datetime
    recommended_actions: List[str]

@dataclass
class BehavioralProfile:
    """User behavioral profile for anomaly detection"""
    user_id: str
    verification_frequency: float
    avg_processing_time: float
    common_verification_hours: List[int]
    institution_preferences: List[str]
    geographic_patterns: List[str]
    success_rate: float
    suspicious_activity_score: float

class FraudDetectionService:
    """Advanced fraud detection and pattern recognition service"""
    
    def __init__(self):
        self.db = None
        self.verification_records_collection = None
        self.certificates_collection = None
        self.users_collection = None
        self.blacklist_collection = None
        self.fraud_alerts_collection = None
        
        # Fraud detection configuration
        self.config = {
            "thresholds": {
                "rapid_fire_minutes": 5,
                "rapid_fire_count": 10,
                "duplicate_similarity": 0.95,
                "suspicious_success_rate": 0.95,
                "geographic_radius_km": 100,
                "behavioral_anomaly_threshold": 0.8
            },
            "time_windows": {
                "short_term_hours": 1,
                "medium_term_hours": 24,
                "long_term_days": 30
            },
            "ml_models": {
                "behavioral_model_version": "1.0",
                "pattern_detection_version": "1.0",
                "risk_scoring_version": "1.0"
            }
        }
        
        # Pattern detection rules
        self.pattern_rules = self._initialize_pattern_rules()
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = await get_database()
            self.verification_records_collection = self.db.verification_records
            self.certificates_collection = self.db.certificates
            self.users_collection = self.db.users
            self.blacklist_collection = self.db.blacklist_entries
            self.fraud_alerts_collection = self.db.fraud_alerts
    
    async def analyze_verification_for_fraud(
        self,
        verification_record: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a verification request for fraud patterns
        
        Args:
            verification_record: The verification record to analyze
            user_context: Context about the user making the request
            
        Returns:
            Fraud analysis results with risk assessment
        """
        try:
            await self._ensure_db_connection()
            
            fraud_analysis = {
                "fraud_risk_level": FraudRiskLevel.LOW,
                "fraud_score": 0.0,
                "detected_patterns": [],
                "behavioral_anomalies": [],
                "risk_factors": [],
                "recommended_actions": [],
                "alerts_generated": []
            }
            
            user_id = verification_record.get("requester_id")
            
            # 1. Behavioral Analysis
            behavioral_analysis = await self._analyze_user_behavior(user_id, verification_record)
            fraud_analysis["behavioral_anomalies"] = behavioral_analysis["anomalies"]
            
            # 2. Pattern Detection
            pattern_analysis = await self._detect_fraud_patterns(verification_record, user_context)
            fraud_analysis["detected_patterns"] = pattern_analysis["patterns"]
            
            # 3. Duplicate and Similarity Analysis
            duplicate_analysis = await self._analyze_duplicates_and_similarity(verification_record)
            fraud_analysis["duplicate_analysis"] = duplicate_analysis
            
            # 4. Temporal Pattern Analysis
            temporal_analysis = await self._analyze_temporal_patterns(user_id, verification_record)
            fraud_analysis["temporal_patterns"] = temporal_analysis
            
            # 5. Geographic Analysis
            geographic_analysis = await self._analyze_geographic_patterns(user_id, user_context)
            fraud_analysis["geographic_analysis"] = geographic_analysis
            
            # 6. Calculate Overall Fraud Score
            fraud_score = self._calculate_fraud_score(
                behavioral_analysis, pattern_analysis, duplicate_analysis,
                temporal_analysis, geographic_analysis
            )
            fraud_analysis["fraud_score"] = fraud_score
            
            # 7. Determine Risk Level
            fraud_analysis["fraud_risk_level"] = self._determine_risk_level(fraud_score)
            
            # 8. Generate Risk Factors
            fraud_analysis["risk_factors"] = self._compile_risk_factors(
                behavioral_analysis, pattern_analysis, duplicate_analysis,
                temporal_analysis, geographic_analysis
            )
            
            # 9. Generate Recommendations
            fraud_analysis["recommended_actions"] = self._generate_fraud_recommendations(
                fraud_analysis["fraud_risk_level"], fraud_analysis["detected_patterns"]
            )
            
            # 10. Generate Alerts if Necessary
            if fraud_score >= 0.7:  # High risk threshold
                alerts = await self._generate_fraud_alerts(verification_record, fraud_analysis)
                fraud_analysis["alerts_generated"] = alerts
            
            # 11. Update User Risk Profile
            await self._update_user_risk_profile(user_id, fraud_analysis)
            
            logger.info(f"Fraud analysis completed for user {user_id}: Risk={fraud_analysis['fraud_risk_level']}, Score={fraud_score:.2f}")
            
            return fraud_analysis
            
        except Exception as e:
            logger.error(f"Fraud analysis failed: {str(e)}")
            raise ProcessingError(f"Fraud analysis failed: {str(e)}")
    
    async def _analyze_user_behavior(
        self,
        user_id: str,
        current_verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze user behavioral patterns for anomalies"""
        
        # Get user's historical verification data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.config["time_windows"]["long_term_days"])
        
        historical_records = []
        async for record in self.verification_records_collection.find({
            "requester_id": user_id,
            "verification_date": {"$gte": start_date, "$lte": end_date}
        }):
            historical_records.append(record)
        
        if len(historical_records) < 5:  # Not enough data for behavioral analysis
            return {
                "anomalies": [],
                "behavioral_score": 0.0,
                "profile": None
            }
        
        # Build behavioral profile
        profile = self._build_behavioral_profile(user_id, historical_records)
        
        # Detect anomalies in current verification
        anomalies = []
        
        # 1. Frequency Anomaly
        recent_count = len([r for r in historical_records 
                           if (end_date - r["verification_date"]).total_seconds() < 3600])
        if recent_count > 5:  # More than 5 verifications in last hour
            anomalies.append({
                "type": "HIGH_FREQUENCY",
                "severity": "HIGH",
                "description": f"Unusually high verification frequency: {recent_count} in last hour",
                "evidence": {"recent_count": recent_count, "threshold": 5}
            })
        
        # 2. Timing Anomaly
        current_hour = datetime.utcnow().hour
        if current_hour not in profile.common_verification_hours:
            anomalies.append({
                "type": "UNUSUAL_TIMING",
                "severity": "MEDIUM",
                "description": f"Verification at unusual hour: {current_hour}",
                "evidence": {"current_hour": current_hour, "common_hours": profile.common_verification_hours}
            })
        
        # 3. Success Rate Anomaly
        if profile.success_rate > self.config["thresholds"]["suspicious_success_rate"]:
            anomalies.append({
                "type": "SUSPICIOUS_SUCCESS_RATE",
                "severity": "HIGH",
                "description": f"Unusually high success rate: {profile.success_rate:.2f}",
                "evidence": {"success_rate": profile.success_rate, "threshold": self.config["thresholds"]["suspicious_success_rate"]}
            })
        
        # 4. Institution Pattern Anomaly
        current_institution = current_verification.get("result", {}).get("verification_results", {}).get("institutional", {}).get("institution", {}).get("id")
        if current_institution and current_institution not in profile.institution_preferences:
            anomalies.append({
                "type": "UNUSUAL_INSTITUTION",
                "severity": "MEDIUM",
                "description": f"Verification for unusual institution: {current_institution}",
                "evidence": {"current_institution": current_institution, "preferred_institutions": profile.institution_preferences}
            })
        
        behavioral_score = len(anomalies) * 0.2  # Simple scoring based on anomaly count
        
        return {
            "anomalies": anomalies,
            "behavioral_score": min(behavioral_score, 1.0),
            "profile": profile
        }
    
    async def _detect_fraud_patterns(
        self,
        verification_record: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect specific fraud patterns"""
        
        patterns = []
        user_id = verification_record.get("requester_id")
        
        # 1. Rapid Fire Pattern
        rapid_fire_pattern = await self._detect_rapid_fire_pattern(user_id)
        if rapid_fire_pattern:
            patterns.append(rapid_fire_pattern)
        
        # 2. Certificate Farming Pattern
        farming_pattern = await self._detect_certificate_farming(user_id)
        if farming_pattern:
            patterns.append(farming_pattern)
        
        # 3. Template Reuse Pattern
        template_pattern = await self._detect_template_reuse(verification_record)
        if template_pattern:
            patterns.append(template_pattern)
        
        # 4. Coordinated Fraud Pattern
        coordinated_pattern = await self._detect_coordinated_fraud(verification_record, user_context)
        if coordinated_pattern:
            patterns.append(coordinated_pattern)
        
        # 5. Grade Inflation Pattern
        grade_pattern = await self._detect_grade_inflation_pattern(verification_record)
        if grade_pattern:
            patterns.append(grade_pattern)
        
        pattern_score = len(patterns) * 0.25  # Weight each pattern
        
        return {
            "patterns": patterns,
            "pattern_score": min(pattern_score, 1.0)
        }
    
    async def _analyze_duplicates_and_similarity(
        self,
        verification_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze for duplicate submissions and similar certificates"""
        
        # Extract certificate data for comparison
        cert_data = verification_record.get("result", {}).get("verification_results", {}).get("ocr", {}).get("extracted_data", {})
        
        if not cert_data:
            return {"duplicate_score": 0.0, "similar_certificates": []}
        
        # Search for similar certificates
        similar_certs = []
        
        # Check by certificate number
        cert_number = cert_data.get("certificate_number")
        if cert_number:
            async for existing in self.certificates_collection.find({
                "certificate_number": cert_number
            }):
                similar_certs.append({
                    "certificate_id": existing["certificate_id"],
                    "similarity_type": "EXACT_NUMBER_MATCH",
                    "similarity_score": 1.0,
                    "match_field": "certificate_number"
                })
        
        # Check by student name and roll number combination
        student_name = cert_data.get("student_name")
        roll_number = cert_data.get("roll_number")
        if student_name and roll_number:
            async for existing in self.certificates_collection.find({
                "student_name": {"$regex": f"^{student_name}$", "$options": "i"},
                "roll_number": roll_number
            }):
                similar_certs.append({
                    "certificate_id": existing["certificate_id"],
                    "similarity_type": "STUDENT_MATCH",
                    "similarity_score": 0.9,
                    "match_field": "student_name_roll_number"
                })
        
        # Calculate duplicate score
        duplicate_score = 0.0
        if similar_certs:
            max_similarity = max(cert["similarity_score"] for cert in similar_certs)
            if max_similarity >= self.config["thresholds"]["duplicate_similarity"]:
                duplicate_score = max_similarity
        
        return {
            "duplicate_score": duplicate_score,
            "similar_certificates": similar_certs,
            "has_duplicates": duplicate_score >= self.config["thresholds"]["duplicate_similarity"]
        }
    
    async def _analyze_temporal_patterns(
        self,
        user_id: str,
        verification_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze temporal patterns for suspicious timing"""
        
        current_time = datetime.utcnow()
        
        # Get recent verifications
        recent_verifications = []
        async for record in self.verification_records_collection.find({
            "requester_id": user_id,
            "verification_date": {
                "$gte": current_time - timedelta(hours=self.config["time_windows"]["medium_term_hours"])
            }
        }).sort("verification_date", -1):
            recent_verifications.append(record)
        
        temporal_anomalies = []
        
        # 1. Rapid succession pattern
        if len(recent_verifications) >= 2:
            time_gaps = []
            for i in range(1, len(recent_verifications)):
                gap = (recent_verifications[i-1]["verification_date"] - recent_verifications[i]["verification_date"]).total_seconds()
                time_gaps.append(gap)
            
            avg_gap = sum(time_gaps) / len(time_gaps) if time_gaps else 0
            if avg_gap < 300:  # Less than 5 minutes average
                temporal_anomalies.append({
                    "type": "RAPID_SUCCESSION",
                    "severity": "HIGH",
                    "description": f"Verifications in rapid succession (avg {avg_gap:.0f}s apart)",
                    "evidence": {"average_gap_seconds": avg_gap, "verification_count": len(recent_verifications)}
                })
        
        # 2. Off-hours pattern
        if current_time.hour < 6 or current_time.hour > 22:
            temporal_anomalies.append({
                "type": "OFF_HOURS_ACTIVITY",
                "severity": "MEDIUM",
                "description": f"Verification during off-hours: {current_time.hour}:00",
                "evidence": {"hour": current_time.hour}
            })
        
        # 3. Weekend pattern (if unusual for user)
        if current_time.weekday() >= 5:  # Saturday or Sunday
            weekend_count = len([r for r in recent_verifications if r["verification_date"].weekday() >= 5])
            if weekend_count > len(recent_verifications) * 0.7:  # More than 70% on weekends
                temporal_anomalies.append({
                    "type": "WEEKEND_HEAVY_ACTIVITY",
                    "severity": "MEDIUM",
                    "description": "Unusually high weekend verification activity",
                    "evidence": {"weekend_percentage": weekend_count / len(recent_verifications) if recent_verifications else 0}
                })
        
        temporal_score = len(temporal_anomalies) * 0.2
        
        return {
            "anomalies": temporal_anomalies,
            "temporal_score": min(temporal_score, 1.0),
            "recent_verification_count": len(recent_verifications)
        }
    
    async def _analyze_geographic_patterns(
        self,
        user_id: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze geographic patterns for location-based anomalies"""
        
        current_ip = user_context.get("ip_address", "unknown")
        
        # Get recent IP addresses for this user
        recent_ips = []
        async for record in self.verification_records_collection.find({
            "requester_id": user_id,
            "verification_date": {"$gte": datetime.utcnow() - timedelta(days=7)}
        }):
            if record.get("ip_address"):
                recent_ips.append(record["ip_address"])
        
        geographic_anomalies = []
        
        # 1. IP Address Diversity
        unique_ips = set(recent_ips)
        if len(unique_ips) > 5:  # More than 5 different IPs in a week
            geographic_anomalies.append({
                "type": "HIGH_IP_DIVERSITY",
                "severity": "MEDIUM",
                "description": f"High IP address diversity: {len(unique_ips)} unique IPs in 7 days",
                "evidence": {"unique_ip_count": len(unique_ips), "total_verifications": len(recent_ips)}
            })
        
        # 2. New IP Address
        if current_ip != "unknown" and current_ip not in recent_ips:
            geographic_anomalies.append({
                "type": "NEW_IP_ADDRESS",
                "severity": "LOW",
                "description": f"Verification from new IP address: {current_ip}",
                "evidence": {"current_ip": current_ip, "known_ips": list(unique_ips)[:5]}  # Limit for privacy
            })
        
        geographic_score = len(geographic_anomalies) * 0.15
        
        return {
            "anomalies": geographic_anomalies,
            "geographic_score": min(geographic_score, 1.0),
            "ip_diversity": len(unique_ips)
        }
    
    def _calculate_fraud_score(
        self,
        behavioral_analysis: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
        duplicate_analysis: Dict[str, Any],
        temporal_analysis: Dict[str, Any],
        geographic_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall fraud score using weighted components"""
        
        weights = {
            "behavioral": 0.25,
            "patterns": 0.30,
            "duplicates": 0.25,
            "temporal": 0.15,
            "geographic": 0.05
        }
        
        scores = {
            "behavioral": behavioral_analysis.get("behavioral_score", 0.0),
            "patterns": pattern_analysis.get("pattern_score", 0.0),
            "duplicates": duplicate_analysis.get("duplicate_score", 0.0),
            "temporal": temporal_analysis.get("temporal_score", 0.0),
            "geographic": geographic_analysis.get("geographic_score", 0.0)
        }
        
        fraud_score = sum(scores[component] * weights[component] for component in weights)
        
        return min(fraud_score, 1.0)
    
    def _determine_risk_level(self, fraud_score: float) -> FraudRiskLevel:
        """Determine risk level based on fraud score"""
        
        if fraud_score >= 0.8:
            return FraudRiskLevel.CRITICAL
        elif fraud_score >= 0.6:
            return FraudRiskLevel.HIGH
        elif fraud_score >= 0.3:
            return FraudRiskLevel.MEDIUM
        else:
            return FraudRiskLevel.LOW
    
    def _build_behavioral_profile(
        self,
        user_id: str,
        historical_records: List[Dict[str, Any]]
    ) -> BehavioralProfile:
        """Build behavioral profile from historical data"""
        
        if not historical_records:
            return BehavioralProfile(
                user_id=user_id,
                verification_frequency=0.0,
                avg_processing_time=0.0,
                common_verification_hours=[],
                institution_preferences=[],
                geographic_patterns=[],
                success_rate=0.0,
                suspicious_activity_score=0.0
            )
        
        # Calculate metrics
        total_days = (max(r["verification_date"] for r in historical_records) - 
                     min(r["verification_date"] for r in historical_records)).days + 1
        verification_frequency = len(historical_records) / max(total_days, 1)
        
        processing_times = [r.get("processing_time", 0) for r in historical_records]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        verification_hours = [r["verification_date"].hour for r in historical_records]
        hour_counts = Counter(verification_hours)
        common_verification_hours = [hour for hour, count in hour_counts.most_common(5)]
        
        # Extract institutions
        institutions = []
        for record in historical_records:
            inst_id = record.get("result", {}).get("verification_results", {}).get("institutional", {}).get("institution", {}).get("id")
            if inst_id:
                institutions.append(inst_id)
        
        institution_counts = Counter(institutions)
        institution_preferences = [inst for inst, count in institution_counts.most_common(3)]
        
        # Calculate success rate
        successful_verifications = len([r for r in historical_records if r.get("status") == VerificationStatus.VERIFIED])
        success_rate = successful_verifications / len(historical_records)
        
        # Simple suspicious activity score
        suspicious_activity_score = 0.0
        if success_rate > 0.95:
            suspicious_activity_score += 0.3
        if verification_frequency > 5:  # More than 5 per day
            suspicious_activity_score += 0.2
        
        return BehavioralProfile(
            user_id=user_id,
            verification_frequency=verification_frequency,
            avg_processing_time=avg_processing_time,
            common_verification_hours=common_verification_hours,
            institution_preferences=institution_preferences,
            geographic_patterns=[],  # Would need IP geolocation data
            success_rate=success_rate,
            suspicious_activity_score=min(suspicious_activity_score, 1.0)
        )
    
    async def _detect_rapid_fire_pattern(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Detect rapid fire verification pattern"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.config["thresholds"]["rapid_fire_minutes"])
        
        recent_count = await self.verification_records_collection.count_documents({
            "requester_id": user_id,
            "verification_date": {"$gte": cutoff_time}
        })
        
        if recent_count >= self.config["thresholds"]["rapid_fire_count"]:
            return {
                "pattern_type": FraudPattern.RAPID_FIRE_VERIFICATION,
                "severity": "HIGH",
                "confidence": min(recent_count / self.config["thresholds"]["rapid_fire_count"], 1.0),
                "description": f"Rapid fire pattern: {recent_count} verifications in {self.config['thresholds']['rapid_fire_minutes']} minutes",
                "evidence": {
                    "verification_count": recent_count,
                    "time_window_minutes": self.config["thresholds"]["rapid_fire_minutes"]
                }
            }
        
        return None
    
    async def _detect_certificate_farming(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Detect certificate farming pattern"""
        
        # Look for pattern of verifying many certificates from same institution
        pipeline = [
            {"$match": {"requester_id": user_id}},
            {"$group": {
                "_id": "$result.verification_results.institutional.institution.id",
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gte": 20}}},  # 20+ certificates from same institution
            {"$sort": {"count": -1}}
        ]
        
        results = []
        async for result in self.verification_records_collection.aggregate(pipeline):
            if result["_id"]:  # Skip null institution IDs
                results.append(result)
        
        if results:
            top_institution = results[0]
            return {
                "pattern_type": FraudPattern.CERTIFICATE_FARMING,
                "severity": "HIGH",
                "confidence": min(top_institution["count"] / 50, 1.0),  # Scale to 50 as max
                "description": f"Certificate farming: {top_institution['count']} certificates from institution {top_institution['_id']}",
                "evidence": {
                    "institution_id": top_institution["_id"],
                    "certificate_count": top_institution["count"]
                }
            }
        
        return None
    
    async def _detect_template_reuse(self, verification_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect template reuse pattern"""
        
        # This would require image similarity analysis
        # For now, implement basic text similarity check
        
        cert_data = verification_record.get("result", {}).get("verification_results", {}).get("ocr", {})
        raw_text = cert_data.get("raw_text", "")
        
        if not raw_text or len(raw_text) < 50:
            return None
        
        # Simple text similarity check (in production, use more sophisticated methods)
        text_hash = hashlib.md5(raw_text.encode()).hexdigest()
        
        # Check for similar text patterns in recent verifications
        similar_count = await self.verification_records_collection.count_documents({
            "result.verification_results.ocr.raw_text": {"$regex": raw_text[:100], "$options": "i"},
            "verification_date": {"$gte": datetime.utcnow() - timedelta(days=30)}
        })
        
        if similar_count > 5:  # More than 5 similar texts
            return {
                "pattern_type": FraudPattern.TEMPLATE_REUSE,
                "severity": "MEDIUM",
                "confidence": min(similar_count / 10, 1.0),
                "description": f"Template reuse pattern: {similar_count} similar certificates detected",
                "evidence": {
                    "similar_count": similar_count,
                    "text_hash": text_hash
                }
            }
        
        return None
    
    async def _detect_coordinated_fraud(
        self,
        verification_record: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect coordinated fraud pattern"""
        
        current_ip = user_context.get("ip_address")
        if not current_ip:
            return None
        
        # Look for multiple users from same IP with similar verification patterns
        recent_users_same_ip = []
        async for record in self.verification_records_collection.find({
            "ip_address": current_ip,
            "verification_date": {"$gte": datetime.utcnow() - timedelta(hours=24)}
        }):
            recent_users_same_ip.append(record["requester_id"])
        
        unique_users = set(recent_users_same_ip)
        
        if len(unique_users) > 5:  # More than 5 different users from same IP
            return {
                "pattern_type": FraudPattern.COORDINATED_FRAUD,
                "severity": "HIGH",
                "confidence": min(len(unique_users) / 10, 1.0),
                "description": f"Coordinated fraud: {len(unique_users)} users from same IP in 24h",
                "evidence": {
                    "ip_address": current_ip,
                    "unique_user_count": len(unique_users),
                    "total_verifications": len(recent_users_same_ip)
                }
            }
        
        return None
    
    async def _detect_grade_inflation_pattern(self, verification_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect grade inflation pattern"""
        
        # Extract grades from verification
        cert_data = verification_record.get("result", {}).get("verification_results", {}).get("ocr", {}).get("extracted_data", {})
        grades = cert_data.get("grades", {})
        
        if not grades:
            return None
        
        # Look for suspiciously high grades
        suspicious_indicators = []
        
        # Check for perfect scores
        if isinstance(grades, dict):
            for subject, grade in grades.items():
                if isinstance(grade, str):
                    if any(perfect in grade.upper() for perfect in ["100%", "A+", "10.0", "DISTINCTION"]):
                        suspicious_indicators.append(f"Perfect score in {subject}: {grade}")
        
        # Check overall grade
        overall = grades.get("overall", "")
        if isinstance(overall, str) and any(perfect in overall.upper() for perfect in ["A+", "DISTINCTION", "100%"]):
            suspicious_indicators.append(f"Perfect overall grade: {overall}")
        
        if len(suspicious_indicators) >= 2:  # Multiple perfect scores
            return {
                "pattern_type": FraudPattern.GRADE_INFLATION_PATTERN,
                "severity": "MEDIUM",
                "confidence": min(len(suspicious_indicators) / 5, 1.0),
                "description": f"Grade inflation pattern: {len(suspicious_indicators)} perfect scores detected",
                "evidence": {
                    "suspicious_grades": suspicious_indicators,
                    "grade_data": grades
                }
            }
        
        return None
    
    def _compile_risk_factors(
        self,
        behavioral_analysis: Dict[str, Any],
        pattern_analysis: Dict[str, Any],
        duplicate_analysis: Dict[str, Any],
        temporal_analysis: Dict[str, Any],
        geographic_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compile all risk factors from different analyses"""
        
        risk_factors = []
        
        # Add behavioral anomalies
        for anomaly in behavioral_analysis.get("anomalies", []):
            risk_factors.append({
                "category": "BEHAVIORAL",
                "type": anomaly["type"],
                "severity": anomaly["severity"],
                "description": anomaly["description"],
                "evidence": anomaly["evidence"]
            })
        
        # Add detected patterns
        for pattern in pattern_analysis.get("patterns", []):
            risk_factors.append({
                "category": "FRAUD_PATTERN",
                "type": pattern["pattern_type"],
                "severity": pattern["severity"],
                "description": pattern["description"],
                "evidence": pattern["evidence"]
            })
        
        # Add duplicate issues
        if duplicate_analysis.get("has_duplicates"):
            risk_factors.append({
                "category": "DUPLICATE",
                "type": "DUPLICATE_CERTIFICATE",
                "severity": "CRITICAL",
                "description": f"Duplicate certificate detected with {duplicate_analysis['duplicate_score']:.2f} similarity",
                "evidence": duplicate_analysis["similar_certificates"]
            })
        
        # Add temporal anomalies
        for anomaly in temporal_analysis.get("anomalies", []):
            risk_factors.append({
                "category": "TEMPORAL",
                "type": anomaly["type"],
                "severity": anomaly["severity"],
                "description": anomaly["description"],
                "evidence": anomaly["evidence"]
            })
        
        # Add geographic anomalies
        for anomaly in geographic_analysis.get("anomalies", []):
            risk_factors.append({
                "category": "GEOGRAPHIC",
                "type": anomaly["type"],
                "severity": anomaly["severity"],
                "description": anomaly["description"],
                "evidence": anomaly["evidence"]
            })
        
        return risk_factors
    
    def _generate_fraud_recommendations(
        self,
        risk_level: FraudRiskLevel,
        detected_patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on fraud analysis"""
        
        recommendations = []
        
        if risk_level == FraudRiskLevel.CRITICAL:
            recommendations.extend([
                "IMMEDIATE ACTION: Block user account pending investigation",
                "Escalate to fraud investigation team",
                "Review all recent verifications from this user",
                "Consider legal action if fraud is confirmed"
            ])
        elif risk_level == FraudRiskLevel.HIGH:
            recommendations.extend([
                "Flag user account for enhanced monitoring",
                "Require additional verification steps for future requests",
                "Manual review of verification results",
                "Contact user to verify identity"
            ])
        elif risk_level == FraudRiskLevel.MEDIUM:
            recommendations.extend([
                "Increase monitoring frequency for this user",
                "Apply additional verification checks",
                "Review verification patterns periodically"
            ])
        else:
            recommendations.append("Continue normal monitoring")
        
        # Pattern-specific recommendations
        pattern_types = [p.get("pattern_type") for p in detected_patterns]
        
        if FraudPattern.RAPID_FIRE_VERIFICATION in pattern_types:
            recommendations.append("Implement rate limiting for this user")
        
        if FraudPattern.CERTIFICATE_FARMING in pattern_types:
            recommendations.append("Investigate relationship with institution")
        
        if FraudPattern.COORDINATED_FRAUD in pattern_types:
            recommendations.append("Investigate all users from same IP address")
        
        return recommendations
    
    async def _generate_fraud_alerts(
        self,
        verification_record: Dict[str, Any],
        fraud_analysis: Dict[str, Any]
    ) -> List[FraudAlert]:
        """Generate fraud alerts for high-risk cases"""
        
        alerts = []
        
        for pattern in fraud_analysis.get("detected_patterns", []):
            if pattern.get("severity") in ["HIGH", "CRITICAL"]:
                alert = FraudAlert(
                    alert_id=f"FRAUD_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{verification_record.get('verification_id', 'unknown')}",
                    pattern_type=FraudPattern(pattern["pattern_type"]),
                    risk_level=fraud_analysis["fraud_risk_level"],
                    confidence=pattern.get("confidence", 0.0),
                    description=pattern["description"],
                    evidence=[pattern.get("evidence", {})],
                    affected_entities=[verification_record.get("requester_id", "unknown")],
                    timestamp=datetime.utcnow(),
                    recommended_actions=fraud_analysis["recommended_actions"]
                )
                alerts.append(alert)
                
                # Store alert in database
                await self.fraud_alerts_collection.insert_one({
                    "alert_id": alert.alert_id,
                    "pattern_type": alert.pattern_type.value,
                    "risk_level": alert.risk_level.value,
                    "confidence": alert.confidence,
                    "description": alert.description,
                    "evidence": alert.evidence,
                    "affected_entities": alert.affected_entities,
                    "timestamp": alert.timestamp,
                    "recommended_actions": alert.recommended_actions,
                    "status": "ACTIVE"
                })
        
        return alerts
    
    async def _update_user_risk_profile(
        self,
        user_id: str,
        fraud_analysis: Dict[str, Any]
    ):
        """Update user's risk profile based on fraud analysis"""
        
        # Update user record with risk information
        risk_update = {
            "fraud_risk_level": fraud_analysis["fraud_risk_level"].value,
            "fraud_score": fraud_analysis["fraud_score"],
            "last_fraud_analysis": datetime.utcnow(),
            "total_risk_factors": len(fraud_analysis["risk_factors"])
        }
        
        await self.users_collection.update_one(
            {"user_id": user_id},
            {"$set": risk_update}
        )
    
    def _initialize_pattern_rules(self) -> Dict[str, Any]:
        """Initialize fraud pattern detection rules"""
        
        return {
            "rapid_fire": {
                "time_window_minutes": 5,
                "threshold_count": 10,
                "severity": "HIGH"
            },
            "certificate_farming": {
                "institution_threshold": 20,
                "time_window_days": 30,
                "severity": "HIGH"
            },
            "coordinated_fraud": {
                "ip_user_threshold": 5,
                "time_window_hours": 24,
                "severity": "HIGH"
            },
            "behavioral_anomaly": {
                "success_rate_threshold": 0.95,
                "frequency_threshold": 5.0,
                "severity": "MEDIUM"
            }
        }
    
    async def get_fraud_statistics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Get fraud detection statistics"""
        
        await self._ensure_db_connection()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=time_period_days)
        
        # Get fraud alerts in time period
        fraud_alerts = []
        async for alert in self.fraud_alerts_collection.find({
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }):
            fraud_alerts.append(alert)
        
        # Calculate statistics
        total_alerts = len(fraud_alerts)
        alerts_by_risk = Counter(alert["risk_level"] for alert in fraud_alerts)
        alerts_by_pattern = Counter(alert["pattern_type"] for alert in fraud_alerts)
        
        # Get verification statistics for comparison
        total_verifications = await self.verification_records_collection.count_documents({
            "verification_date": {"$gte": start_date, "$lte": end_date}
        })
        
        fraud_rate = (total_alerts / total_verifications * 100) if total_verifications > 0 else 0
        
        return {
            "time_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": time_period_days
            },
            "summary": {
                "total_fraud_alerts": total_alerts,
                "total_verifications": total_verifications,
                "fraud_detection_rate": fraud_rate
            },
            "alerts_by_risk_level": dict(alerts_by_risk),
            "alerts_by_pattern_type": dict(alerts_by_pattern),
            "top_risk_factors": self._get_top_risk_factors(fraud_alerts),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_top_risk_factors(self, fraud_alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top risk factors from fraud alerts"""
        
        risk_factor_counts = Counter()
        
        for alert in fraud_alerts:
            pattern_type = alert.get("pattern_type", "UNKNOWN")
            risk_factor_counts[pattern_type] += 1
        
        return [
            {"risk_factor": factor, "count": count, "percentage": count / len(fraud_alerts) * 100}
            for factor, count in risk_factor_counts.most_common(10)
        ]