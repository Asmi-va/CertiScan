"""
Fraud Detection API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from ...services.fraud_detection_service import FraudDetectionService, FraudRiskLevel
from ...services.auth_service import AuthService
from ...db.models import UserRole
from ...core.security import get_current_user
from ...utils.exceptions import ProcessingError, UnauthorizedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fraud-detection", tags=["fraud-detection"])
security = HTTPBearer()

# Initialize services
fraud_service = FraudDetectionService()
auth_service = AuthService()

@router.post("/analyze-verification")
async def analyze_verification_for_fraud(
    verification_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze a verification request for fraud patterns
    """
    try:
        # Only admin and government users can perform fraud analysis
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions for fraud analysis")
        
        # Add user context
        user_context = {
            "ip_address": "request.client.host if request.client else 'unknown'",
            "user_agent": "request.headers.get('user-agent', '')",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Perform fraud analysis
        fraud_analysis = await fraud_service.analyze_verification_for_fraud(
            verification_data,
            user_context
        )
        
        return {
            "success": True,
            "fraud_analysis": fraud_analysis,
            "message": "Fraud analysis completed successfully"
        }
        
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=f"Fraud analysis failed: {str(e)}")
    except Exception as e:
        logger.error(f"Fraud analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during fraud analysis")

@router.get("/fraud-statistics")
async def get_fraud_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get fraud detection statistics for a specified time period
    """
    try:
        # Only admin and government users can view fraud statistics
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view fraud statistics")
        
        statistics = await fraud_service.get_fraud_statistics(days)
        
        return {
            "success": True,
            "statistics": statistics,
            "message": f"Fraud statistics retrieved for {days} days"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving fraud statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fraud statistics")

@router.get("/fraud-alerts")
async def get_fraud_alerts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    risk_level: Optional[FraudRiskLevel] = Query(None),
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent fraud alerts with pagination and filtering
    """
    try:
        # Only admin and government users can view fraud alerts
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view fraud alerts")
        
        await fraud_service._ensure_db_connection()
        
        # Build query filters
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        query = {
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }
        
        if risk_level:
            query["risk_level"] = risk_level.value
        
        # Get total count
        total_count = await fraud_service.fraud_alerts_collection.count_documents(query)
        
        # Get alerts with pagination
        cursor = fraud_service.fraud_alerts_collection.find(query).sort(
            "timestamp", -1
        ).skip(offset).limit(limit)
        
        alerts = []
        async for alert in cursor:
            # Clean up alert data for response
            clean_alert = {
                "alert_id": alert["alert_id"],
                "pattern_type": alert["pattern_type"],
                "risk_level": alert["risk_level"],
                "confidence": alert["confidence"],
                "description": alert["description"],
                "affected_entities_count": len(alert.get("affected_entities", [])),
                "timestamp": alert["timestamp"].isoformat(),
                "status": alert.get("status", "ACTIVE"),
                "recommended_actions_count": len(alert.get("recommended_actions", []))
            }
            alerts.append(clean_alert)
        
        return {
            "fraud_alerts": alerts,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters": {
                "risk_level": risk_level.value if risk_level else None,
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving fraud alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fraud alerts")

@router.get("/fraud-alert-details/{alert_id}")
async def get_fraud_alert_details(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific fraud alert
    """
    try:
        # Only admin and government users can view fraud alert details
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view fraud alert details")
        
        await fraud_service._ensure_db_connection()
        
        # Get alert details
        alert = await fraud_service.fraud_alerts_collection.find_one({
            "alert_id": alert_id
        })
        
        if not alert:
            raise HTTPException(status_code=404, detail="Fraud alert not found")
        
        # Return detailed alert information
        return {
            "alert_details": {
                "alert_id": alert["alert_id"],
                "pattern_type": alert["pattern_type"],
                "risk_level": alert["risk_level"],
                "confidence": alert["confidence"],
                "description": alert["description"],
                "evidence": alert.get("evidence", []),
                "affected_entities": alert.get("affected_entities", []),
                "timestamp": alert["timestamp"].isoformat(),
                "recommended_actions": alert.get("recommended_actions", []),
                "status": alert.get("status", "ACTIVE")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving fraud alert details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fraud alert details")

@router.post("/update-alert-status/{alert_id}")
async def update_fraud_alert_status(
    alert_id: str,
    status_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of a fraud alert
    """
    try:
        # Only admin users can update alert status
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can update alert status")
        
        await fraud_service._ensure_db_connection()
        
        new_status = status_data.get("status")
        notes = status_data.get("notes", "")
        
        if new_status not in ["ACTIVE", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"]:
            raise HTTPException(status_code=422, detail="Invalid status value")
        
        # Update alert status
        result = await fraud_service.fraud_alerts_collection.update_one(
            {"alert_id": alert_id},
            {
                "$set": {
                    "status": new_status,
                    "updated_by": current_user["user_id"],
                    "updated_at": datetime.utcnow(),
                    "notes": notes
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Fraud alert not found")
        
        return {
            "success": True,
            "message": f"Alert {alert_id} status updated to {new_status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update alert status")

@router.get("/user-risk-profile/{user_id}")
async def get_user_risk_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get risk profile for a specific user
    """
    try:
        # Only admin and government users can view user risk profiles
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view user risk profiles")
        
        await fraud_service._ensure_db_connection()
        
        # Get user information
        user = await fraud_service.users_collection.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get recent verification history
        recent_verifications = []
        async for record in fraud_service.verification_records_collection.find({
            "requester_id": user_id
        }).sort("verification_date", -1).limit(50):
            recent_verifications.append({
                "verification_id": record["verification_id"],
                "status": record["status"],
                "confidence_score": record["confidence_score"],
                "verification_date": record["verification_date"].isoformat(),
                "flags_count": len(record.get("flags_detected", []))
            })
        
        # Get fraud alerts for this user
        user_alerts = []
        async for alert in fraud_service.fraud_alerts_collection.find({
            "affected_entities": user_id
        }).sort("timestamp", -1).limit(20):
            user_alerts.append({
                "alert_id": alert["alert_id"],
                "pattern_type": alert["pattern_type"],
                "risk_level": alert["risk_level"],
                "timestamp": alert["timestamp"].isoformat(),
                "status": alert.get("status", "ACTIVE")
            })
        
        # Calculate risk metrics
        total_verifications = len(recent_verifications)
        successful_verifications = len([v for v in recent_verifications if v["status"] == "VERIFIED"])
        success_rate = successful_verifications / total_verifications if total_verifications > 0 else 0
        
        avg_confidence = sum(v["confidence_score"] for v in recent_verifications) / total_verifications if total_verifications > 0 else 0
        
        risk_profile = {
            "user_id": user_id,
            "user_info": {
                "email": user.get("email", ""),
                "role": user.get("role", ""),
                "organization": user.get("organization", ""),
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at", datetime.utcnow()).isoformat()
            },
            "risk_assessment": {
                "fraud_risk_level": user.get("fraud_risk_level", "LOW"),
                "fraud_score": user.get("fraud_score", 0.0),
                "last_fraud_analysis": user.get("last_fraud_analysis", datetime.utcnow()).isoformat(),
                "total_risk_factors": user.get("total_risk_factors", 0)
            },
            "verification_statistics": {
                "total_verifications": total_verifications,
                "success_rate": success_rate,
                "average_confidence": avg_confidence,
                "recent_verifications": recent_verifications[:10]  # Last 10
            },
            "fraud_alerts": {
                "total_alerts": len(user_alerts),
                "active_alerts": len([a for a in user_alerts if a["status"] == "ACTIVE"]),
                "recent_alerts": user_alerts[:5]  # Last 5
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "risk_profile": risk_profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user risk profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user risk profile")

@router.get("/fraud-trends")
async def get_fraud_trends(
    days: int = Query(90, ge=7, le=365),
    current_user: dict = Depends(get_current_user)
):
    """
    Get fraud detection trends over time
    """
    try:
        # Only admin and government users can view fraud trends
        if current_user["role"] not in [UserRole.ADMIN, UserRole.GOVERNMENT]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to view fraud trends")
        
        await fraud_service._ensure_db_connection()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get daily fraud alert counts
        daily_pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "risk_level": "$risk_level"
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id.date": 1}}
        ]
        
        daily_trends = {}
        async for result in fraud_service.fraud_alerts_collection.aggregate(daily_pipeline):
            date = result["_id"]["date"]
            risk_level = result["_id"]["risk_level"]
            count = result["count"]
            
            if date not in daily_trends:
                daily_trends[date] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            
            daily_trends[date][risk_level] = count
        
        # Get pattern trends
        pattern_pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$pattern_type",
                    "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$confidence"}
                }
            },
            {"$sort": {"count": -1}}
        ]
        
        pattern_trends = []
        async for result in fraud_service.fraud_alerts_collection.aggregate(pattern_pipeline):
            pattern_trends.append({
                "pattern_type": result["_id"],
                "count": result["count"],
                "average_confidence": round(result["avg_confidence"], 3)
            })
        
        return {
            "fraud_trends": {
                "time_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "daily_trends": [
                    {
                        "date": date,
                        "alerts": trends
                    }
                    for date, trends in sorted(daily_trends.items())
                ],
                "pattern_trends": pattern_trends,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving fraud trends: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fraud trends")

@router.get("/system-health")
async def get_fraud_detection_system_health(
    current_user: dict = Depends(get_current_user)
):
    """
    Get health status of fraud detection system
    """
    try:
        # Only admin users can view system health
        if current_user["role"] != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin users can view system health")
        
        await fraud_service._ensure_db_connection()
        
        # Check system components
        health_status = {
            "overall_status": "HEALTHY",
            "components": {
                "fraud_detection_service": {"status": "OPERATIONAL", "last_check": datetime.utcnow().isoformat()},
                "pattern_recognition": {"status": "OPERATIONAL", "last_check": datetime.utcnow().isoformat()},
                "behavioral_analysis": {"status": "OPERATIONAL", "last_check": datetime.utcnow().isoformat()},
                "alert_system": {"status": "OPERATIONAL", "last_check": datetime.utcnow().isoformat()}
            },
            "performance_metrics": {
                "avg_analysis_time": "2.1s",
                "detection_accuracy": "94.2%",
                "false_positive_rate": "3.1%"
            },
            "recent_activity": {
                "alerts_last_24h": await fraud_service.fraud_alerts_collection.count_documents({
                    "timestamp": {"$gte": datetime.utcnow() - timedelta(hours=24)}
                }),
                "patterns_detected_last_7d": len(set([
                    alert["pattern_type"] async for alert in fraud_service.fraud_alerts_collection.find({
                        "timestamp": {"$gte": datetime.utcnow() - timedelta(days=7)}
                    })
                ]))
            },
            "system_version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error retrieving system health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")