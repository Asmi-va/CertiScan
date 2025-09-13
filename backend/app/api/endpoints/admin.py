"""
Admin Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ...services.admin_dashboard_service import AdminDashboardService, AlertSeverity
from ...services.auth_service import AuthService
from ...db.models import UserRole, BlacklistType, BlacklistStatus
from ...core.security import get_current_user
from ...utils.exceptions import ProcessingError, UnauthorizedError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()

# Initialize services
admin_service = AdminDashboardService()
auth_service = AuthService()

@router.get("/dashboard-overview")
async def get_dashboard_overview(
    hours: int = Query(24, ge=1, le=168, description="Time period in hours"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive admin dashboard overview
    """
    try:
        # Only admin and government users can access dashboard
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to access admin dashboard")
        
        overview = await admin_service.get_dashboard_overview(hours)
        
        return {
            "success": True,
            "dashboard_overview": overview,
            "message": f"Dashboard overview retrieved for {hours} hours"
        }
        
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard overview")

@router.get("/fraud-analysis")
async def get_detailed_fraud_analysis(
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed fraud analysis and trends
    """
    try:
        # Only admin and government users can access fraud analysis
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to access fraud analysis")
        
        fraud_analysis = await admin_service.get_detailed_fraud_analysis(days)
        
        return {
            "success": True,
            "fraud_analysis": fraud_analysis,
            "message": f"Fraud analysis retrieved for {days} days"
        }
        
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting fraud analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fraud analysis")

@router.get("/blacklist")
async def get_blacklist_entries(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    entry_type: Optional[BlacklistType] = Query(None),
    status: Optional[BlacklistStatus] = Query(None),
    severity: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get blacklist entries with pagination and filtering
    """
    try:
        # Only admin users can manage blacklist
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can access blacklist")
        
        filters = {}
        if entry_type:
            filters["type"] = entry_type.value
        if status:
            filters["status"] = status.value
        if severity:
            filters["severity"] = severity
        
        blacklist_data = await admin_service.get_blacklist_entries(
            limit=limit,
            offset=offset,
            filters=filters if filters else None
        )
        
        return {
            "success": True,
            "blacklist": blacklist_data,
            "message": "Blacklist entries retrieved successfully"
        }
        
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting blacklist entries: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve blacklist entries")

@router.post("/blacklist")
async def manage_blacklist_entry(
    action_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Manage blacklist entries (add, update, remove)
    """
    try:
        # Only admin users can manage blacklist
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can manage blacklist")
        
        action = action_data.get("action")
        if not action or action not in ["add", "update", "remove"]:
            raise HTTPException(status_code=422, detail="Invalid or missing action")
        
        result = await admin_service.manage_blacklist(
            action=action,
            blacklist_data=action_data,
            admin_user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "result": result,
            "message": f"Blacklist {action} completed successfully"
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error managing blacklist: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to manage blacklist entry")

@router.post("/generate-report")
async def generate_system_report(
    report_request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Generate comprehensive system reports
    """
    try:
        # Only admin and government users can generate reports
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to generate reports")
        
        report_type = report_request.get("report_type")
        time_period_days = report_request.get("time_period_days", 30)
        
        if not report_type:
            raise HTTPException(status_code=422, detail="Report type is required")
        
        valid_report_types = ["verification_summary", "fraud_analysis", "institution_performance", "system_performance"]
        if report_type not in valid_report_types:
            raise HTTPException(status_code=422, detail=f"Invalid report type. Valid types: {valid_report_types}")
        
        report = await admin_service.generate_system_report(
            report_type=report_type,
            time_period_days=time_period_days,
            admin_user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "report": report,
            "message": f"{report_type} report generated successfully"
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

@router.get("/system-health")
async def get_system_health(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current system health status
    """
    try:
        # Only admin users can view detailed system health
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can view system health")
        
        # Get system health from dashboard overview
        overview = await admin_service.get_dashboard_overview(1)  # Last 1 hour
        system_health = overview.get("system_health", {})
        
        return {
            "success": True,
            "system_health": system_health,
            "message": "System health status retrieved"
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")

@router.post("/create-alert")
async def create_system_alert(
    alert_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new system alert
    """
    try:
        # Only admin users can create system alerts
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can create system alerts")
        
        severity = alert_data.get("severity")
        component = alert_data.get("component")
        message = alert_data.get("message")
        
        if not all([severity, component, message]):
            raise HTTPException(status_code=422, detail="Severity, component, and message are required")
        
        try:
            severity_enum = AlertSeverity(severity.upper())
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid severity level")
        
        alert = await admin_service.create_system_alert(
            severity=severity_enum,
            component=component,
            message=message
        )
        
        return {
            "success": True,
            "alert": {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "component": alert.component,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat()
            },
            "message": "System alert created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating system alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create system alert")

@router.get("/verification-statistics")
async def get_verification_statistics(
    days: int = Query(7, ge=1, le=90, description="Statistics period in days"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed verification statistics
    """
    try:
        # Admin and government users can view statistics
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view statistics")
        
        # Get verification statistics from dashboard
        overview = await admin_service.get_dashboard_overview(days * 24)
        verification_stats = overview.get("verification_statistics", {})
        
        return {
            "success": True,
            "verification_statistics": verification_stats,
            "period_days": days,
            "message": f"Verification statistics retrieved for {days} days"
        }
        
    except Exception as e:
        logger.error(f"Error getting verification statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve verification statistics")

@router.get("/institution-statistics")
async def get_institution_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get institution statistics and performance metrics
    """
    try:
        # Admin and government users can view institution statistics
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view institution statistics")
        
        # Get institution statistics from dashboard
        overview = await admin_service.get_dashboard_overview(24)
        institution_stats = overview.get("institution_statistics", {})
        
        return {
            "success": True,
            "institution_statistics": institution_stats,
            "message": "Institution statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting institution statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve institution statistics")

@router.get("/user-activity")
async def get_user_activity_statistics(
    hours: int = Query(24, ge=1, le=168, description="Activity period in hours"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user activity statistics
    """
    try:
        # Admin users can view user activity
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can view user activity")
        
        # Get user activity from dashboard
        overview = await admin_service.get_dashboard_overview(hours)
        user_activity = overview.get("user_activity", {})
        
        return {
            "success": True,
            "user_activity": user_activity,
            "period_hours": hours,
            "message": f"User activity statistics retrieved for {hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user activity statistics")

@router.get("/performance-metrics")
async def get_performance_metrics(
    hours: int = Query(24, ge=1, le=168, description="Metrics period in hours"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get system performance metrics and trends
    """
    try:
        # Admin users can view performance metrics
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can view performance metrics")
        
        # Get performance trends from dashboard
        overview = await admin_service.get_dashboard_overview(hours)
        performance_trends = overview.get("performance_trends", {})
        system_health = overview.get("system_health", {})
        
        return {
            "success": True,
            "performance_metrics": {
                "trends": performance_trends,
                "current_health": system_health
            },
            "period_hours": hours,
            "message": f"Performance metrics retrieved for {hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")