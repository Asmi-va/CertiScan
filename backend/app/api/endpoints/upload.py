"""
Upload API endpoints for certificate file uploads and preprocessing.

This module provides secure file upload endpoints with validation, virus scanning,
preprocessing, and queue management according to requirements 1.1, 4.1, and 4.2.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse

from app.services.upload_service import upload_service
from app.middleware.auth_middleware import get_current_user
from app.db.models import User

router = APIRouter()


@router.post("/upload", response_model=Dict[str, Any])
async def upload_certificate(
    file: UploadFile = File(..., description="Certificate file to upload (PDF, JPG, PNG, TIFF)"),
    priority: int = Form(default=1, description="Processing priority (1=high, 2=normal, 3=low)"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload a certificate file for verification.
    
    This endpoint handles secure file upload with comprehensive validation,
    preprocessing, and queue management.
    
    Args:
        file: The certificate file to upload
        priority: Processing priority for the queue
        current_user: Authenticated user making the request
        
    Returns:
        Dict containing upload results and file information
        
    Raises:
        HTTPException: If file validation fails or upload error occurs
    """
    try:
        # Validate the uploaded file
        validation_result = await upload_service.validate_file(file)
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "File validation failed",
                    "errors": validation_result["errors"],
                    "security_checks": validation_result.get("security_checks", {})
                }
            )
        
        # Save the validated file
        save_result = await upload_service.save_upload(file, validation_result)
        
        if not save_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Failed to save uploaded file",
                    "error": save_result["error"]
                }
            )
        
        # Add to processing queue
        queue_result = await upload_service.add_to_processing_queue(
            save_result["file_id"], priority
        )
        
        if not queue_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Failed to add file to processing queue",
                    "error": queue_result["error"]
                }
            )
        
        # Return comprehensive upload information
        return {
            "message": "File uploaded successfully",
            "file_id": save_result["file_id"],
            "original_filename": file.filename,
            "file_size": validation_result["file_info"]["file_size"],
            "file_hash": validation_result["file_info"]["file_hash"],
            "upload_timestamp": save_result["metadata"]["upload_timestamp"],
            "preprocessing_applied": bool(save_result["processed_path"]),
            "queue_position": queue_result["queue_position"],
            "estimated_processing_time": queue_result["estimated_processing_time"],
            "validation_summary": {
                "security_checks_passed": validation_result["security_checks"]["safe"],
                "file_type": validation_result["file_info"]["mime_type"],
                "image_dimensions": validation_result["file_info"].get("image_width") and 
                                 f"{validation_result['file_info']['image_width']}x{validation_result['file_info']['image_height']}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Internal server error during file upload",
                "error": str(e)
            }
        )


@router.get("/upload/{file_id}/status", response_model=Dict[str, Any])
async def get_upload_status(
    file_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of an uploaded file.
    
    Args:
        file_id: Unique identifier for the uploaded file
        current_user: Authenticated user making the request
        
    Returns:
        Dict containing current upload and processing status
        
    Raises:
        HTTPException: If file not found or access denied
    """
    try:
        status_result = await upload_service.get_upload_status(file_id)
        
        if "error" in status_result:
            if status_result["error"] == "File not found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=status_result["error"]
                )
        
        return {
            "file_id": file_id,
            "status": status_result["status"],
            "upload_timestamp": status_result["upload_timestamp"],
            "processing_queue_status": status_result.get("processing_queue_status"),
            "queue_details": status_result.get("queue_status"),
            "file_info": {
                "original_filename": status_result["original_filename"],
                "file_size": status_result["file_size"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving upload status: {str(e)}"
        )


@router.post("/upload/batch", response_model=Dict[str, Any])
async def upload_multiple_certificates(
    files: List[UploadFile] = File(..., description="Multiple certificate files to upload"),
    priority: int = Form(default=2, description="Processing priority for all files"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload multiple certificate files for batch processing.
    
    Args:
        files: List of certificate files to upload
        priority: Processing priority for all files
        current_user: Authenticated user making the request
        
    Returns:
        Dict containing batch upload results
        
    Raises:
        HTTPException: If batch upload fails
    """
    if len(files) > 10:  # Limit batch size
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files allowed per batch upload"
        )
    
    batch_results = {
        "total_files": len(files),
        "successful_uploads": 0,
        "failed_uploads": 0,
        "upload_results": [],
        "errors": []
    }
    
    for i, file in enumerate(files):
        try:
            # Validate file
            validation_result = await upload_service.validate_file(file)
            
            if not validation_result["valid"]:
                batch_results["failed_uploads"] += 1
                batch_results["errors"].append({
                    "file_index": i,
                    "filename": file.filename,
                    "errors": validation_result["errors"]
                })
                continue
            
            # Save file
            save_result = await upload_service.save_upload(file, validation_result)
            
            if not save_result["success"]:
                batch_results["failed_uploads"] += 1
                batch_results["errors"].append({
                    "file_index": i,
                    "filename": file.filename,
                    "error": save_result["error"]
                })
                continue
            
            # Add to queue
            queue_result = await upload_service.add_to_processing_queue(
                save_result["file_id"], priority
            )
            
            if queue_result["success"]:
                batch_results["successful_uploads"] += 1
                batch_results["upload_results"].append({
                    "file_index": i,
                    "filename": file.filename,
                    "file_id": save_result["file_id"],
                    "queue_position": queue_result["queue_position"]
                })
            else:
                batch_results["failed_uploads"] += 1
                batch_results["errors"].append({
                    "file_index": i,
                    "filename": file.filename,
                    "error": queue_result["error"]
                })
                
        except Exception as e:
            batch_results["failed_uploads"] += 1
            batch_results["errors"].append({
                "file_index": i,
                "filename": file.filename,
                "error": str(e)
            })
    
    return batch_results


@router.get("/upload/queue/status", response_model=Dict[str, Any])
async def get_queue_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current processing queue status.
    
    Args:
        current_user: Authenticated user making the request
        
    Returns:
        Dict containing queue statistics and status
    """
    try:
        from app.db.database import get_collection
        
        queue_collection = await get_collection("processing_queue")
        
        # Get queue statistics
        total_pending = await queue_collection.count_documents({"status": "pending"})
        total_processing = await queue_collection.count_documents({"status": "processing"})
        total_completed = await queue_collection.count_documents({"status": "completed"})
        total_failed = await queue_collection.count_documents({"status": "failed"})
        
        # Get recent queue entries
        recent_entries = []
        async for entry in queue_collection.find(
            {"status": {"$in": ["pending", "processing"]}},
            {"file_id": 1, "priority": 1, "status": 1, "created_at": 1}
        ).sort("created_at", 1).limit(10):
            recent_entries.append({
                "file_id": entry["file_id"],
                "priority": entry["priority"],
                "status": entry["status"],
                "created_at": entry["created_at"]
            })
        
        return {
            "queue_statistics": {
                "pending": total_pending,
                "processing": total_processing,
                "completed": total_completed,
                "failed": total_failed,
                "total": total_pending + total_processing + total_completed + total_failed
            },
            "recent_entries": recent_entries,
            "estimated_wait_time": total_pending * 30  # 30 seconds per file estimate
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving queue status: {str(e)}"
        )


@router.delete("/upload/{file_id}", response_model=Dict[str, Any])
async def delete_upload(
    file_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Delete an uploaded file and its associated data.
    
    Args:
        file_id: Unique identifier for the uploaded file
        current_user: Authenticated user making the request
        
    Returns:
        Dict containing deletion results
        
    Raises:
        HTTPException: If file not found or deletion fails
    """
    try:
        from app.db.database import get_collection
        import os
        
        # Get upload record
        uploads_collection = await get_collection("uploads")
        upload_record = await uploads_collection.find_one({"file_id": file_id})
        
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete physical files
        files_deleted = 0
        for path_key in ["original_path", "processed_path"]:
            if upload_record.get(path_key) and os.path.exists(upload_record[path_key]):
                os.unlink(upload_record[path_key])
                files_deleted += 1
        
        # Remove from processing queue
        queue_collection = await get_collection("processing_queue")
        await queue_collection.delete_many({"file_id": file_id})
        
        # Delete upload record
        await uploads_collection.delete_one({"file_id": file_id})
        
        return {
            "message": "File deleted successfully",
            "file_id": file_id,
            "files_deleted": files_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )


@router.post("/upload/cleanup", response_model=Dict[str, Any])
async def cleanup_old_uploads(
    days_old: int = Form(default=30, description="Delete files older than this many days"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Clean up old uploaded files and database records.
    
    This endpoint is typically used by admin users for maintenance.
    
    Args:
        days_old: Number of days after which files should be deleted
        current_user: Authenticated user making the request
        
    Returns:
        Dict containing cleanup results
        
    Raises:
        HTTPException: If user lacks admin permissions or cleanup fails
    """
    # Check if user has admin permissions
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required for cleanup operations"
        )
    
    if days_old < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days_old must be at least 1"
        )
    
    try:
        cleanup_result = await upload_service.cleanup_old_files(days_old)
        
        return {
            "message": "Cleanup completed",
            "files_deleted": cleanup_result["files_deleted"],
            "records_deleted": cleanup_result["records_deleted"],
            "errors": cleanup_result["errors"],
            "days_old_threshold": days_old
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup operation failed: {str(e)}"
        )