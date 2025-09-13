"""
Admin Dashboard and Monitoring Service

Provides comprehensive admin dashboard with verification statistics, fraud trend analysis,
reporting functionality, blacklist management, and real-time monitoring with alert system.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
import json
from dataclasses import dataclass
from enum import Enum

from ..db.database import get_database
from ..db.models import (
    VerificationRecord, Certificate, Institution, User, BlacklistEntry,
    VerificationStatus, UserRole, BlacklistType, BlacklistStatus
)
from ..services.fraud_detection_service import FraudDetectionService
from ..core.config import settings
from ..utils.exceptions import ProcessingError, UnauthorizedError, ValidationError

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SystemStatus(Enum):
    """System component status"""
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    MAINTENANCE = "MAINTENANCE"

@dataclass
class SystemAlert:
    """System monitoring alert"""
    alert_id: str
    severity: AlertSeverity
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_notes: Optional[str] = None

@dataclass
class PerformanceMetric:
    """Performance monitoring metric"""
    metric_name: str
    current_value: float
    threshold_warning: float
    threshold_critical: float
    unit: str
    timestamp: datetime

class AdminDashboardService:
    """Comprehensive admin dashboard and monitoring service"""
    
    def __init__(self):
        self.db = None
        self.verification_records_collection = None
        self.certificates_collection = None
        self.institutions_collection = None
        self.users_collection = None
        self.blacklist_collection = None
        self.system_alerts_collection = None
        self.performance_metrics_collection = None
        
        # Initialize fraud detection service
        self.fraud_service = FraudDetectionService()
        
        # Dashboard configuration
        self.config = {
            "performance_thresholds": {
                "response_time_warning": 5.0,  # seconds
                "response_time_critical": 10.0,
                "error_rate_warning": 0.05,  # 5%
                "error_rate_critical": 0.10,  # 10%
                "cpu_usage_warning": 0.80,  # 80%
                "cpu_usage_critical": 0.95,  # 95%
                "memory_usage_warning": 0.85,  # 85%
                "memory_usage_critical": 0.95  # 95%
            },
            "alert_retention_days": 30,
            "metrics_retention_days": 90
        }
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = await get_database()
            self.verification_records_collection = self.db.verification_records
            self.certificates_collection = self.db.certificates
            self.institutions_collection = self.db.institutions
            self.users_collection = self.db.users
            self.blacklist_collection = self.db.blacklist_entries
            self.system_alerts_collection = self.db.system_alerts
            self.performance_metrics_collection = self.db.performance_metrics
    
    async def get_dashboard_overview(self, admin_user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard overview with key metrics and statistics
        """
        try:
            await self._ensure_db_connection()
            
            # Verify admin permissions
            await self._verify_admin_permissions(admin_user_id)
            
            # Get time ranges for analysis
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            month_start = now - timedelta(days=30)
            
            # Collect overview statistics
            overview = {
                "summary_statistics": await self._get_summary_statistics(now),
                "verification_trends": await self._get_verification_trends(month_start, now),
                "fraud_statistics": await self._get_fraud_overview(week_start, now),
                "system_health": await self._get_system_health_overview(),
                "recent_alerts": await self._get_recent_alerts(limit=10),
                "top_institutions": await self._get_top_institutions(month_start, now),
                "performance_metrics": await self._get_current_performance_metrics(),
                "generated_at": now.isoformat()
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Error generating dashboard overview: {str(e)}")
            raise ProcessingError(f"Failed to generate dashboard overview: {str(e)}")
    
    async def get_verification_statistics(
        self,
        admin_user_id: str,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "daily"
    ) -> Dict[str, Any]:
        """
        Get detailed verification statistics with customizable time range and granularity
        """
        try:
            await self._ensure_db_connection()
            await self._verify_admin_permissions(admin_user_id)
            
            # Validation
            if end_date <= start_date:
                raise ValidationError("End date must be after start date")
            
            if granularity not in ["hourly", "daily", "weekly", "monthly"]:
                raise ValidationError("Granularity must be one of: hourly, daily, weekly, monthly")
            
            # Get verification statistics
            statistics = {
                "time_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "granularity": granularity
                },
                "overall_statistics": await self._get_overall_verification_stats(start_date, end_date),
                "time_series_data": await self._get_verification_time_series(start_date, end_date, granularity),
                "status_breakdown": await self._get_verification_status_breakdown(start_date, end_date),
                "institution_statistics": await self._get_institution_verification_stats(start_date, end_date),
                "user_type_statistics": await self._get_user_type_verification_stats(start_date, end_date),
                "performance_statistics": await self._get_verification_performance_stats(start_date, end_date),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error generating verification statistics: {str(e)}")
            raise ProcessingError(f"Failed to generate verification statistics: {str(e)}")
    
    async def get_fraud_trend_analysis(
        self,
        admin_user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive fraud trend analysis and reporting
        """
        try:
            await self._ensure_db_connection()
            await self._verify_admin_permissions(admin_user_id)
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get fraud statistics from fraud detection service
            fraud_stats = await self.fraud_service.get_fraud_statistics(days)
            
            # Enhanced fraud analysis
            fraud_analysis = {
                "time_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "fraud_overview": fraud_stats,
                "trend_analysis": await self._analyze_fraud_trends(start_date, end_date),
                "risk_assessment": await self._get_current_risk_assessment(),
                "top_fraud_patterns": await self._get_top_fraud_patterns(start_date, end_date),
                "affected_institutions": await self._get_fraud_affected_institutions(start_date, end_date),
                "geographic_analysis": await self._get_fraud_geographic_analysis(start_date, end_date),
                "recommendations": await self._generate_fraud_prevention_recommendations(),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return fraud_analysis
            
        except Exception as e:
            logger.error(f"Error generating fraud trend analysis: {str(e)}")
            raise ProcessingError(f"Failed to generate fraud trend analysis: {str(e)}")
    
    async def manage_blacklist(
        self,
        admin_user_id: str,
        action: str,
        entry_data: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive blacklist management system
        """
        try:
            await self._ensure_db_connection()
            await self._verify_admin_permissions(admin_user_id)
            
            if action == "create":
                return await self._create_blacklist_entry(admin_user_id, entry_data)
            elif action == "update":
                return await self._update_blacklist_entry(admin_user_id, entry_id, entry_data)
            elif action == "delete":
                return await self._delete_blacklist_entry(admin_user_id, entry_id)
            elif action == "list":
                return await self._list_blacklist_entries(entry_data or {})
            elif action == "search":
                return await self._search_blacklist_entries(entry_data or {})
            else:
                raise ValidationError(f"Invalid action: {action}")
                
        except Exception as e:
            logger.error(f"Error managing blacklist: {str(e)}")
            raise ProcessingError(f"Failed to manage blacklist: {str(e)}")
    
    async def get_system_monitoring_data(self, admin_user_id: str) -> Dict[str, Any]:
        """
        Get real-time system monitoring data and alerts
        """
        try:
            await self._ensure_db_connection()
            await self._verify_admin_permissions(admin_user_id)
            
            monitoring_data = {
                "system_status": await self._get_detailed_system_status(),
                "performance_metrics": await self._get_detailed_performance_metrics(),
                "active_alerts": await self._get_active_system_alerts(),
                "component_health": await self._get_component_health_status(),
                "resource_usage": await self._get_resource_usage_metrics(),
                "service_availability": await self._get_service_availability_metrics(),
                "recent_incidents": await self._get_recent_incidents(),
                "uptime_statistics": await self._get_uptime_statistics(),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return monitoring_data
            
        except Exception as e:
            logger.error(f"Error getting system monitoring data: {str(e)}")
            raise ProcessingError(f"Failed to get system monitoring data: {str(e)}")
    
    async def generate_comprehensive_report(
        self,
        admin_user_id: str,
        report_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive reports for various aspects of the system
        """
        try:
            await self._ensure_db_connection()
            await self._verify_admin_permissions(admin_user_id)
            
            if report_type == "verification_summary":
                return await self._generate_verification_summary_report(parameters)
            elif report_type == "fraud_analysis":
                return await self._generate_fraud_analysis_report(parameters)
            elif report_type == "institution_performance":
                return await self._generate_institution_performance_report(parameters)
            elif report_type == "system_health":
                return await self._generate_system_health_report(parameters)
            elif report_type == "user_activity":
                return await self._generate_user_activity_report(parameters)
            else:
                raise ValidationError(f"Invalid report type: {report_type}")
                
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise ProcessingError(f"Failed to generate report: {str(e)}")
    
    # Private helper methods
    
    async def _verify_admin_permissions(self, user_id: str):
        """Verify user has admin permissions"""
        user = await self.users_collection.find_one({"user_id": user_id})
        if not user or user.get("role") not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise UnauthorizedError("Insufficient permissions for admin dashboard access")
    
    async def _get_summary_statistics(self, reference_time: datetime) -> Dict[str, Any]:
        """Get high-level summary statistics"""
        
        today_start = reference_time.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = reference_time - timedelta(days=7)
        month_start = reference_time - timedelta(days=30)
        
        # Total counts
        total_verifications = await self.verification_records_collection.count_documents({})
        total_certificates = await self.certificates_collection.count_documents({})
        total_institutions = await self.institutions_collection.count_documents({})
        total_users = await self.users_collection.count_documents({})
        
        # Today's activity
        today_verifications = await self.verification_records_collection.count_documents({
            "verification_date": {"$gte": today_start}
        })
        
        # Yesterday's activity for comparison
        yesterday_verifications = await self.verification_records_collection.count_documents({
            "verification_date": {"$gte": yesterday_start, "$lt": today_start}
        })
        
        # Success rates
        successful_today = await self.verification_records_collection.count_documents({
            "verification_date": {"$gte": today_start},
            "status": VerificationStatus.VERIFIED
        })
        
        success_rate_today = (successful_today / today_verifications * 100) if today_verifications > 0 else 0
        
        # Growth calculations
        verification_growth = ((today_verifications - yesterday_verifications) / yesterday_verifications * 100) if yesterday_verifications > 0 else 0
        
        return {
            "totals": {
                "verifications": total_verifications,
                "certificates": total_certificates,
                "institutions": total_institutions,
                "users": total_users
            },
            "today": {
                "verifications": today_verifications,
                "success_rate": round(success_rate_today, 1),
                "verification_growth": round(verification_growth, 1)
            },
            "active_alerts": await self.system_alerts_collection.count_documents({
                "resolved": False,
                "severity": {"$in": ["ERROR", "CRITICAL"]}
            })
        }
    
    async def _get_verification_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get verification trends over time period"""
        
        pipeline = [
            {
                "$match": {
                    "verification_date": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$verification_date"}},
                        "status": "$status"
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id.date": 1}}
        ]
        
        daily_data = defaultdict(lambda: {"VERIFIED": 0, "INVALID": 0, "SUSPICIOUS": 0, "PENDING": 0})
        
        async for result in self.verification_records_collection.aggregate(pipeline):
            date = result["_id"]["date"]
            status = result["_id"]["status"]
            count = result["count"]
            daily_data[date][status] = count
        
        # Convert to list format
        trend_data = []
        for date in sorted(daily_data.keys()):
            data = daily_data[date]
            trend_data.append({
                "date": date,
                "verified": data["VERIFIED"],
                "invalid": data["INVALID"],
                "suspicious": data["SUSPICIOUS"],
                "pending": data["PENDING"],
                "total": sum(data.values())
            })
        
        return {
            "daily_trends": trend_data,
            "summary": {
                "total_days": len(trend_data),
                "avg_daily_verifications": sum(d["total"] for d in trend_data) / len(trend_data) if trend_data else 0,
                "peak_day": max(trend_data, key=lambda x: x["total"]) if trend_data else None
            }
        }
    
    async def _get_fraud_overview(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get fraud detection overview"""
        
        # Get fraud alerts from fraud service
        await self.fraud_service._ensure_db_connection()
        
        total_alerts = await self.fraud_service.fraud_alerts_collection.count_documents({
            "timestamp": {"$gte": start_date, "$lte": end_date}
        })
        
        critical_alerts = await self.fraud_service.fraud_alerts_collection.count_documents({
            "timestamp": {"$gte": start_date, "$lte": end_date},
            "risk_level": "CRITICAL"
        })
        
        high_alerts = await self.fraud_service.fraud_alerts_collection.count_documents({
            "timestamp": {"$gte": start_date, "$lte": end_date},
            "risk_level": "HIGH"
        })
        
        return {
            "total_fraud_alerts": total_alerts,
            "critical_alerts": critical_alerts,
            "high_risk_alerts": high_alerts,
            "fraud_detection_rate": round(total_alerts / 1000 * 100, 2) if total_alerts > 0 else 0  # Mock calculation
        }
    
    async def _get_system_health_overview(self) -> Dict[str, Any]:
        """Get system health overview"""
        
        # Mock system health data (in production, this would come from actual monitoring)
        components = {
            "api_server": SystemStatus.OPERATIONAL,
            "database": SystemStatus.OPERATIONAL,
            "ocr_service": SystemStatus.OPERATIONAL,
            "tamper_detection": SystemStatus.OPERATIONAL,
            "fraud_detection": SystemStatus.OPERATIONAL,
            "file_storage": SystemStatus.OPERATIONAL
        }
        
        # Count active alerts
        active_alerts = await self.system_alerts_collection.count_documents({
            "resolved": False
        }) if self.system_alerts_collection else 0
        
        # Overall system status
        if any(status == SystemStatus.DOWN for status in components.values()):
            overall_status = SystemStatus.DOWN
        elif any(status == SystemStatus.DEGRADED for status in components.values()):
            overall_status = SystemStatus.DEGRADED
        else:
            overall_status = SystemStatus.OPERATIONAL
        
        return {
            "overall_status": overall_status.value,
            "components": {name: status.value for name, status in components.items()},
            "active_alerts": active_alerts,
            "uptime_percentage": 99.9  # Mock uptime
        }
    
    async def _get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent system alerts"""
        
        alerts = []
        if self.system_alerts_collection:
            async for alert in self.system_alerts_collection.find({}).sort("timestamp", -1).limit(limit):
                alerts.append({
                    "alert_id": alert["alert_id"],
                    "severity": alert["severity"],
                    "component": alert["component"],
                    "message": alert["message"],
                    "timestamp": alert["timestamp"].isoformat(),
                    "resolved": alert.get("resolved", False)
                })
        
        return alerts
    
    async def _get_top_institutions(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get top institutions by verification volume"""
        
        pipeline = [
            {
                "$match": {
                    "verification_date": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$result.verification_results.institutional.institution.id",
                    "verification_count": {"$sum": 1},
                    "success_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "VERIFIED"]}, 1, 0]}
                    }
                }
            },
            {"$sort": {"verification_count": -1}},
            {"$limit": 10}
        ]
        
        top_institutions = []
        async for result in self.verification_records_collection.aggregate(pipeline):
            institution_id = result["_id"]
            if institution_id:  # Skip null institution IDs
                verification_count = result["verification_count"]
                success_count = result["success_count"]
                success_rate = (success_count / verification_count * 100) if verification_count > 0 else 0
                
                # Get institution name
                institution = await self.institutions_collection.find_one({"institution_id": institution_id})
                institution_name = institution.get("name", institution_id) if institution else institution_id
                
                top_institutions.append({
                    "institution_id": institution_id,
                    "institution_name": institution_name,
                    "verification_count": verification_count,
                    "success_rate": round(success_rate, 1)
                })
        
        return top_institutions
    
    async def _get_current_performance_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        
        # Mock performance metrics (in production, these would come from actual monitoring)
        return {
            "avg_response_time": 2.1,  # seconds
            "error_rate": 0.02,  # 2%
            "throughput": 150,  # requests per minute
            "cpu_usage": 0.45,  # 45%
            "memory_usage": 0.67,  # 67%
            "disk_usage": 0.34,  # 34%
            "active_connections": 23
        }
    
    async def _create_blacklist_entry(self, admin_user_id: str, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new blacklist entry"""
        
        # Validate required fields
        required_fields = ["type", "identifier", "reason"]
        for field in required_fields:
            if field not in entry_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Create blacklist entry
        entry = BlacklistEntry(
            entry_id=f"BL_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{entry_data['identifier'][:10]}",
            type=BlacklistType(entry_data["type"]),
            identifier=entry_data["identifier"],
            reason=entry_data["reason"],
            description=entry_data.get("description", ""),
            severity=entry_data.get("severity", "MEDIUM"),
            evidence=entry_data.get("evidence", []),
            reported_by=admin_user_id,
            status=BlacklistStatus.ACTIVE
        )
        
        # Insert into database
        result = await self.blacklist_collection.insert_one(entry.model_dump(by_alias=True))
        entry.id = result.inserted_id
        
        logger.info(f"Blacklist entry created: {entry.entry_id} by {admin_user_id}")
        
        return {
            "success": True,
            "entry_id": entry.entry_id,
            "message": "Blacklist entry created successfully"
        }
    
    async def _update_blacklist_entry(self, admin_user_id: str, entry_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing blacklist entry"""
        
        # Update entry
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = admin_user_id
        
        result = await self.blacklist_collection.update_one(
            {"entry_id": entry_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise ValidationError(f"Blacklist entry not found: {entry_id}")
        
        return {
            "success": True,
            "entry_id": entry_id,
            "message": "Blacklist entry updated successfully"
        }
    
    async def _delete_blacklist_entry(self, admin_user_id: str, entry_id: str) -> Dict[str, Any]:
        """Delete blacklist entry"""
        
        result = await self.blacklist_collection.delete_one({"entry_id": entry_id})
        
        if result.deleted_count == 0:
            raise ValidationError(f"Blacklist entry not found: {entry_id}")
        
        logger.info(f"Blacklist entry deleted: {entry_id} by {admin_user_id}")
        
        return {
            "success": True,
            "entry_id": entry_id,
            "message": "Blacklist entry deleted successfully"
        }
    
    async def _list_blacklist_entries(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """List blacklist entries with filtering"""
        
        # Build query
        query = {}
        if "type" in filters:
            query["type"] = filters["type"]
        if "status" in filters:
            query["status"] = filters["status"]
        if "severity" in filters:
            query["severity"] = filters["severity"]
        
        # Get entries
        entries = []
        limit = filters.get("limit", 50)
        offset = filters.get("offset", 0)
        
        async for entry in self.blacklist_collection.find(query).skip(offset).limit(limit):
            entries.append({
                "entry_id": entry["entry_id"],
                "type": entry["type"],
                "identifier": entry["identifier"],
                "reason": entry["reason"],
                "severity": entry["severity"],
                "status": entry["status"],
                "created_at": entry["created_at"].isoformat(),
                "reported_by": entry["reported_by"]
            })
        
        total_count = await self.blacklist_collection.count_documents(query)
        
        return {
            "entries": entries,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    async def _search_blacklist_entries(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search blacklist entries"""
        
        query = {}
        search_term = search_params.get("search_term", "")
        
        if search_term:
            query["$or"] = [
                {"identifier": {"$regex": search_term, "$options": "i"}},
                {"reason": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        
        entries = []
        async for entry in self.blacklist_collection.find(query).limit(20):
            entries.append({
                "entry_id": entry["entry_id"],
                "type": entry["type"],
                "identifier": entry["identifier"],
                "reason": entry["reason"],
                "status": entry["status"]
            })
        
        return {
            "search_results": entries,
            "search_term": search_term,
            "result_count": len(entries)
        }