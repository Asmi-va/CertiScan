"""
File Upload and Preprocessing Service

This service handles secure file uploads, validation, preprocessing, and queue management
for certificate documents according to requirements 1.1, 4.1, and 4.2.
"""

import os
import hashlib
import mimetypes
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageEnhance, ImageFilter
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available, using fallback MIME type detection")

import cv2
import numpy as np

from app.core.config import settings
from app.db.database import get_collection


class FileUploadService:
    """Service for handling secure file uploads and preprocessing."""
    
    # Allowed file types and their MIME types
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.tiff', '.tif'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/tiff', 'image/tif',
        'application/pdf'
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
    MAX_IMAGE_DIMENSION = 4096  # Maximum width or height in pixels
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.processed_dir = self.upload_dir / "processed"
        self.temp_dir = self.upload_dir / "temp"
        self.quarantine_dir = self.upload_dir / "quarantine"
        
        # Create directories if they don't exist
        for directory in [self.upload_dir, self.processed_dir, self.temp_dir, self.quarantine_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Validate uploaded file for security and format compliance.
        
        Args:
            file: The uploaded file object
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If file validation fails
        """
        validation_result = {
            "valid": False,
            "file_info": {},
            "security_checks": {},
            "errors": []
        }
        
        try:
            # Check file size
            file_size = 0
            content = await file.read()
            file_size = len(content)
            await file.seek(0)  # Reset file pointer
            
            if file_size == 0:
                validation_result["errors"].append("File is empty")
                return validation_result
            
            if file_size > self.MAX_FILE_SIZE:
                validation_result["errors"].append(
                    f"File size ({file_size} bytes) exceeds maximum allowed size ({self.MAX_FILE_SIZE} bytes)"
                )
                return validation_result
            
            # Check file extension
            if not file.filename:
                validation_result["errors"].append("Filename is required")
                return validation_result
            
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in self.ALLOWED_EXTENSIONS:
                validation_result["errors"].append(
                    f"File extension '{file_ext}' not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
                )
                return validation_result
            
            # Create temporary file for content validation
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Validate MIME type using python-magic or fallback
                if MAGIC_AVAILABLE:
                    try:
                        mime_type = magic.from_file(temp_file_path, mime=True)
                    except Exception as e:
                        # Fallback to mimetypes module
                        mime_type, _ = mimetypes.guess_type(temp_file_path)
                        if not mime_type:
                            mime_type = f"application/octet-stream"
                else:
                    # Use mimetypes module as fallback
                    mime_type, _ = mimetypes.guess_type(temp_file_path)
                    if not mime_type:
                        # Determine MIME type based on file extension
                        ext_to_mime = {
                            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                            '.png': 'image/png', '.pdf': 'application/pdf',
                            '.tiff': 'image/tiff', '.tif': 'image/tiff'
                        }
                        mime_type = ext_to_mime.get(file_ext, 'application/octet-stream')
                
                if mime_type not in self.ALLOWED_MIME_TYPES:
                    validation_result["errors"].append(
                        f"MIME type '{mime_type}' not allowed. File may be corrupted or malicious."
                    )
                    return validation_result
                
                # Additional security checks
                security_checks = await self._perform_security_checks(temp_file_path, file_ext)
                validation_result["security_checks"] = security_checks
                
                if not security_checks["safe"]:
                    validation_result["errors"].extend(security_checks["issues"])
                    return validation_result
                
                # Extract file metadata
                file_info = await self._extract_file_metadata(temp_file_path, file_ext, file_size)
                validation_result["file_info"] = file_info
                
                validation_result["valid"] = True
                return validation_result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            return validation_result
    
    async def _perform_security_checks(self, file_path: str, file_ext: str) -> Dict[str, Any]:
        """Perform security checks on the uploaded file."""
        security_result = {
            "safe": True,
            "issues": [],
            "checks_performed": []
        }
        
        try:
            # Check for embedded executables or scripts
            with open(file_path, 'rb') as f:
                content = f.read(1024)  # Read first 1KB
                
                # Look for executable signatures
                executable_signatures = [
                    b'MZ',  # Windows PE
                    b'\x7fELF',  # Linux ELF
                    b'#!/bin/',  # Shell script
                    b'<script',  # JavaScript
                    b'<?php',  # PHP
                ]
                
                for sig in executable_signatures:
                    if sig in content:
                        security_result["safe"] = False
                        security_result["issues"].append(f"Potentially malicious content detected: {sig}")
            
            security_result["checks_performed"].append("executable_signature_check")
            
            # For images, perform additional checks
            if file_ext in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
                image_checks = await self._check_image_security(file_path)
                security_result["checks_performed"].extend(image_checks["checks_performed"])
                if not image_checks["safe"]:
                    security_result["safe"] = False
                    security_result["issues"].extend(image_checks["issues"])
            
            return security_result
            
        except Exception as e:
            security_result["safe"] = False
            security_result["issues"].append(f"Security check failed: {str(e)}")
            return security_result
    
    async def _check_image_security(self, file_path: str) -> Dict[str, Any]:
        """Perform security checks specific to image files."""
        result = {
            "safe": True,
            "issues": [],
            "checks_performed": []
        }
        
        try:
            # Try to open and validate image
            with Image.open(file_path) as img:
                # Check image dimensions
                width, height = img.size
                if width > self.MAX_IMAGE_DIMENSION or height > self.MAX_IMAGE_DIMENSION:
                    result["safe"] = False
                    result["issues"].append(
                        f"Image dimensions ({width}x{height}) exceed maximum allowed ({self.MAX_IMAGE_DIMENSION}x{self.MAX_IMAGE_DIMENSION})"
                    )
                
                # Check for suspicious metadata
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    # Look for suspicious EXIF data (this is a basic check)
                    if len(str(exif_data)) > 10000:  # Unusually large EXIF data
                        result["issues"].append("Suspicious EXIF data detected")
                
                result["checks_performed"].append("image_validation")
                result["checks_performed"].append("dimension_check")
                result["checks_performed"].append("exif_check")
                
        except Exception as e:
            result["safe"] = False
            result["issues"].append(f"Image validation failed: {str(e)}")
        
        return result
    
    async def _extract_file_metadata(self, file_path: str, file_ext: str, file_size: int) -> Dict[str, Any]:
        """Extract metadata from the uploaded file."""
        # Determine MIME type
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_file(file_path, mime=True)
            except Exception:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    ext_to_mime = {
                        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                        '.png': 'image/png', '.pdf': 'application/pdf',
                        '.tiff': 'image/tiff', '.tif': 'image/tiff'
                    }
                    mime_type = ext_to_mime.get(file_ext, 'application/octet-stream')
        else:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                ext_to_mime = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.png': 'image/png', '.pdf': 'application/pdf',
                    '.tiff': 'image/tiff', '.tif': 'image/tiff'
                }
                mime_type = ext_to_mime.get(file_ext, 'application/octet-stream')
        
        metadata = {
            "file_size": file_size,
            "file_extension": file_ext,
            "mime_type": mime_type,
            "file_hash": await self._calculate_file_hash(file_path),
            "upload_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Extract image-specific metadata
        if file_ext in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
            try:
                with Image.open(file_path) as img:
                    metadata.update({
                        "image_width": img.width,
                        "image_height": img.height,
                        "image_mode": img.mode,
                        "image_format": img.format,
                    })
                    
                    # Extract EXIF data if available
                    if hasattr(img, '_getexif') and img._getexif():
                        exif_data = img._getexif()
                        # Extract relevant EXIF fields
                        relevant_exif = {}
                        for tag_id, value in exif_data.items():
                            if tag_id in [272, 306, 36867]:  # Make, DateTime, DateTimeOriginal
                                relevant_exif[str(tag_id)] = str(value)
                        metadata["exif_data"] = relevant_exif
                        
            except Exception as e:
                metadata["image_metadata_error"] = str(e)
        
        return metadata
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of the file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def preprocess_image(self, file_path: str, output_path: str) -> Dict[str, Any]:
        """
        Preprocess image for optimal OCR and analysis.
        
        Args:
            file_path: Path to the original image
            output_path: Path where processed image will be saved
            
        Returns:
            Dict containing preprocessing results
        """
        preprocessing_result = {
            "success": False,
            "original_size": None,
            "processed_size": None,
            "operations_applied": [],
            "quality_metrics": {},
            "error": None
        }
        
        try:
            # Run preprocessing in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._preprocess_image_sync, file_path, output_path
            )
            preprocessing_result.update(result)
            
        except Exception as e:
            preprocessing_result["error"] = str(e)
        
        return preprocessing_result
    
    def _preprocess_image_sync(self, file_path: str, output_path: str) -> Dict[str, Any]:
        """Synchronous image preprocessing operations."""
        result = {
            "success": False,
            "original_size": None,
            "processed_size": None,
            "operations_applied": [],
            "quality_metrics": {}
        }
        
        # Load image with OpenCV for advanced processing
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError("Could not load image")
        
        original_height, original_width = img.shape[:2]
        result["original_size"] = (original_width, original_height)
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        result["operations_applied"].append("grayscale_conversion")
        
        # Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)
        result["operations_applied"].append("noise_reduction")
        
        # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        result["operations_applied"].append("contrast_enhancement")
        
        # Sharpen the image
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        result["operations_applied"].append("sharpening")
        
        # Resize if image is too large (maintain aspect ratio)
        max_dimension = 2048
        if max(original_width, original_height) > max_dimension:
            scale = max_dimension / max(original_width, original_height)
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            sharpened = cv2.resize(sharpened, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            result["operations_applied"].append("resizing")
        
        # Calculate quality metrics
        result["quality_metrics"] = {
            "mean_brightness": float(np.mean(sharpened)),
            "contrast_std": float(np.std(sharpened)),
            "sharpness_variance": float(cv2.Laplacian(sharpened, cv2.CV_64F).var())
        }
        
        # Save processed image
        cv2.imwrite(output_path, sharpened)
        
        # Get processed image size
        processed_height, processed_width = sharpened.shape[:2]
        result["processed_size"] = (processed_width, processed_height)
        result["success"] = True
        
        return result
    
    async def save_upload(self, file: UploadFile, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save validated file to upload directory.
        
        Args:
            file: The uploaded file object
            validation_result: Result from file validation
            
        Returns:
            Dict containing save results and file paths
        """
        save_result = {
            "success": False,
            "file_id": None,
            "original_path": None,
            "processed_path": None,
            "metadata": {},
            "error": None
        }
        
        try:
            # Generate unique file ID
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_hash = validation_result["file_info"]["file_hash"][:8]
            file_id = f"{timestamp}_{file_hash}"
            
            # Determine file extension
            file_ext = Path(file.filename).suffix.lower()
            
            # Create file paths
            original_filename = f"{file_id}_original{file_ext}"
            processed_filename = f"{file_id}_processed{file_ext}"
            
            original_path = self.upload_dir / original_filename
            processed_path = self.processed_dir / processed_filename
            
            # Save original file
            content = await file.read()
            with open(original_path, "wb") as f:
                f.write(content)
            
            # Preprocess image if it's an image file
            preprocessing_result = None
            if file_ext in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
                preprocessing_result = await self.preprocess_image(
                    str(original_path), str(processed_path)
                )
            
            # Store metadata in database
            metadata = {
                "file_id": file_id,
                "original_filename": file.filename,
                "file_extension": file_ext,
                "file_size": validation_result["file_info"]["file_size"],
                "file_hash": validation_result["file_info"]["file_hash"],
                "mime_type": validation_result["file_info"]["mime_type"],
                "upload_timestamp": datetime.utcnow(),
                "original_path": str(original_path),
                "processed_path": str(processed_path) if preprocessing_result and preprocessing_result["success"] else None,
                "validation_result": validation_result,
                "preprocessing_result": preprocessing_result,
                "status": "uploaded",
                "processing_queue_status": "pending"
            }
            
            # Save metadata to database
            uploads_collection = await get_collection("uploads")
            await uploads_collection.insert_one(metadata)
            
            save_result.update({
                "success": True,
                "file_id": file_id,
                "original_path": str(original_path),
                "processed_path": str(processed_path) if preprocessing_result and preprocessing_result["success"] else None,
                "metadata": metadata
            })
            
        except Exception as e:
            save_result["error"] = str(e)
            # Clean up files on error
            for path in [original_path, processed_path]:
                if path and os.path.exists(path):
                    os.unlink(path)
        
        return save_result
    
    async def add_to_processing_queue(self, file_id: str, priority: int = 1) -> Dict[str, Any]:
        """
        Add uploaded file to processing queue.
        
        Args:
            file_id: Unique identifier for the uploaded file
            priority: Processing priority (1=high, 2=normal, 3=low)
            
        Returns:
            Dict containing queue operation results
        """
        queue_result = {
            "success": False,
            "queue_position": None,
            "estimated_processing_time": None,
            "error": None
        }
        
        try:
            # Get current queue size
            queue_collection = await get_collection("processing_queue")
            queue_size = await queue_collection.count_documents({"status": "pending"})
            
            # Create queue entry
            queue_entry = {
                "file_id": file_id,
                "priority": priority,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "estimated_processing_time": queue_size * 30,  # Estimate 30 seconds per file
                "retry_count": 0,
                "max_retries": 3
            }
            
            # Insert into queue
            result = await queue_collection.insert_one(queue_entry)
            
            # Update upload record
            uploads_collection = await get_collection("uploads")
            await uploads_collection.update_one(
                {"file_id": file_id},
                {
                    "$set": {
                        "processing_queue_status": "queued",
                        "queue_id": str(result.inserted_id),
                        "queued_at": datetime.utcnow()
                    }
                }
            )
            
            queue_result.update({
                "success": True,
                "queue_position": queue_size + 1,
                "estimated_processing_time": queue_entry["estimated_processing_time"]
            })
            
        except Exception as e:
            queue_result["error"] = str(e)
        
        return queue_result
    
    async def get_upload_status(self, file_id: str) -> Dict[str, Any]:
        """Get the current status of an uploaded file."""
        try:
            uploads_collection = await get_collection("uploads")
            upload_record = await uploads_collection.find_one({"file_id": file_id})
            
            if not upload_record:
                return {"error": "File not found"}
            
            # Get queue status if applicable
            queue_status = None
            if upload_record.get("queue_id"):
                queue_collection = await get_collection("processing_queue")
                queue_record = await queue_collection.find_one({"_id": upload_record["queue_id"]})
                if queue_record:
                    queue_status = {
                        "status": queue_record["status"],
                        "priority": queue_record["priority"],
                        "retry_count": queue_record["retry_count"],
                        "created_at": queue_record["created_at"]
                    }
            
            return {
                "file_id": file_id,
                "status": upload_record["status"],
                "upload_timestamp": upload_record["upload_timestamp"],
                "processing_queue_status": upload_record.get("processing_queue_status"),
                "queue_status": queue_status,
                "file_size": upload_record["file_size"],
                "original_filename": upload_record["original_filename"]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def cleanup_old_files(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old uploaded files and database records."""
        cleanup_result = {
            "files_deleted": 0,
            "records_deleted": 0,
            "errors": []
        }
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old upload records
            uploads_collection = await get_collection("uploads")
            old_uploads = uploads_collection.find({"upload_timestamp": {"$lt": cutoff_date}})
            
            async for upload in old_uploads:
                try:
                    # Delete files
                    for path_key in ["original_path", "processed_path"]:
                        if upload.get(path_key) and os.path.exists(upload[path_key]):
                            os.unlink(upload[path_key])
                            cleanup_result["files_deleted"] += 1
                    
                    # Delete database record
                    await uploads_collection.delete_one({"_id": upload["_id"]})
                    cleanup_result["records_deleted"] += 1
                    
                except Exception as e:
                    cleanup_result["errors"].append(f"Error cleaning up {upload.get('file_id', 'unknown')}: {str(e)}")
            
        except Exception as e:
            cleanup_result["errors"].append(f"Cleanup operation failed: {str(e)}")
        
        return cleanup_result


# Global service instance
upload_service = FileUploadService()