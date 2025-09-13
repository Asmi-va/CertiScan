"""
Test file for the upload service functionality.

This test verifies that the file upload and preprocessing service
meets the requirements 1.1, 4.1, and 4.2.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from PIL import Image
import io

from fastapi import UploadFile
from fastapi.testclient import TestClient

# Import the upload service
from backend.app.services.upload_service import upload_service
from backend.app.core.config import settings


class TestFileUploadService:
    """Test cases for the file upload and preprocessing service."""
    
    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        # Create a simple test image
        img = Image.new('RGB', (800, 600), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Create UploadFile object
        upload_file = UploadFile(
            filename="test_certificate.jpg",
            file=img_bytes,
            content_type="image/jpeg"
        )
        return upload_file
    
    @pytest.fixture
    def sample_pdf_file(self):
        """Create a sample PDF file for testing."""
        # Create a minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
181
%%EOF"""
        
        pdf_bytes = io.BytesIO(pdf_content)
        upload_file = UploadFile(
            filename="test_certificate.pdf",
            file=pdf_bytes,
            content_type="application/pdf"
        )
        return upload_file
    
    @pytest.fixture
    def malicious_file(self):
        """Create a malicious file for security testing."""
        # Create a file with executable signature
        malicious_content = b"MZ\x90\x00" + b"A" * 100  # PE header signature
        malicious_bytes = io.BytesIO(malicious_content)
        
        upload_file = UploadFile(
            filename="malicious.jpg",
            file=malicious_bytes,
            content_type="image/jpeg"
        )
        return upload_file
    
    async def test_file_validation_success(self, sample_image_file):
        """Test successful file validation."""
        validation_result = await upload_service.validate_file(sample_image_file)
        
        assert validation_result["valid"] is True
        assert "file_info" in validation_result
        assert "security_checks" in validation_result
        assert validation_result["security_checks"]["safe"] is True
        assert len(validation_result["errors"]) == 0
        
        # Check file info
        file_info = validation_result["file_info"]
        assert file_info["file_size"] > 0
        assert file_info["file_extension"] == ".jpg"
        assert file_info["mime_type"] == "image/jpeg"
        assert "file_hash" in file_info
        assert "image_width" in file_info
        assert "image_height" in file_info
    
    async def test_file_validation_pdf(self, sample_pdf_file):
        """Test PDF file validation."""
        validation_result = await upload_service.validate_file(sample_pdf_file)
        
        assert validation_result["valid"] is True
        assert validation_result["file_info"]["file_extension"] == ".pdf"
        assert validation_result["file_info"]["mime_type"] == "application/pdf"
        assert validation_result["security_checks"]["safe"] is True
    
    async def test_file_validation_security_failure(self, malicious_file):
        """Test security validation failure."""
        validation_result = await upload_service.validate_file(malicious_file)
        
        assert validation_result["valid"] is False
        assert validation_result["security_checks"]["safe"] is False
        assert len(validation_result["security_checks"]["issues"]) > 0
        assert "malicious content detected" in str(validation_result["security_checks"]["issues"]).lower()
    
    async def test_file_validation_empty_file(self):
        """Test validation of empty file."""
        empty_file = UploadFile(
            filename="empty.jpg",
            file=io.BytesIO(b""),
            content_type="image/jpeg"
        )
        
        validation_result = await upload_service.validate_file(empty_file)
        
        assert validation_result["valid"] is False
        assert "File is empty" in validation_result["errors"]
    
    async def test_file_validation_invalid_extension(self):
        """Test validation of file with invalid extension."""
        invalid_file = UploadFile(
            filename="test.exe",
            file=io.BytesIO(b"test content"),
            content_type="application/octet-stream"
        )
        
        validation_result = await upload_service.validate_file(invalid_file)
        
        assert validation_result["valid"] is False
        assert any("not allowed" in error for error in validation_result["errors"])
    
    async def test_image_preprocessing(self, sample_image_file):
        """Test image preprocessing functionality."""
        # First validate the file
        validation_result = await upload_service.validate_file(sample_image_file)
        assert validation_result["valid"] is True
        
        # Create temporary files for testing
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as input_file:
            content = await sample_image_file.read()
            input_file.write(content)
            input_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as output_file:
                try:
                    # Test preprocessing
                    preprocessing_result = await upload_service.preprocess_image(
                        input_file.name, output_file.name
                    )
                    
                    assert preprocessing_result["success"] is True
                    assert "operations_applied" in preprocessing_result
                    assert len(preprocessing_result["operations_applied"]) > 0
                    assert "quality_metrics" in preprocessing_result
                    
                    # Check that operations were applied
                    operations = preprocessing_result["operations_applied"]
                    expected_operations = [
                        "grayscale_conversion",
                        "noise_reduction", 
                        "contrast_enhancement",
                        "sharpening"
                    ]
                    
                    for op in expected_operations:
                        assert op in operations
                    
                    # Check quality metrics
                    metrics = preprocessing_result["quality_metrics"]
                    assert "mean_brightness" in metrics
                    assert "contrast_std" in metrics
                    assert "sharpness_variance" in metrics
                    
                    # Verify output file exists and has content
                    assert os.path.exists(output_file.name)
                    assert os.path.getsize(output_file.name) > 0
                    
                finally:
                    # Clean up temporary files
                    for temp_path in [input_file.name, output_file.name]:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
    
    async def test_file_hash_calculation(self, sample_image_file):
        """Test file hash calculation."""
        content = await sample_image_file.read()
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            
            try:
                file_hash = await upload_service._calculate_file_hash(temp_file.name)
                
                assert isinstance(file_hash, str)
                assert len(file_hash) == 64  # SHA-256 hash length
                assert all(c in '0123456789abcdef' for c in file_hash)
                
                # Test that same content produces same hash
                file_hash2 = await upload_service._calculate_file_hash(temp_file.name)
                assert file_hash == file_hash2
                
            finally:
                os.unlink(temp_file.name)
    
    async def test_save_upload_success(self, sample_image_file):
        """Test successful file save operation."""
        # First validate the file
        validation_result = await upload_service.validate_file(sample_image_file)
        assert validation_result["valid"] is True
        
        # Test save operation
        save_result = await upload_service.save_upload(sample_image_file, validation_result)
        
        try:
            assert save_result["success"] is True
            assert save_result["file_id"] is not None
            assert save_result["original_path"] is not None
            assert save_result["processed_path"] is not None
            assert save_result["metadata"] is not None
            
            # Verify files were created
            assert os.path.exists(save_result["original_path"])
            assert os.path.exists(save_result["processed_path"])
            
            # Verify metadata structure
            metadata = save_result["metadata"]
            assert metadata["file_id"] == save_result["file_id"]
            assert metadata["original_filename"] == sample_image_file.filename
            assert metadata["status"] == "uploaded"
            assert metadata["processing_queue_status"] == "pending"
            
        finally:
            # Clean up created files
            for path_key in ["original_path", "processed_path"]:
                if save_result.get(path_key) and os.path.exists(save_result[path_key]):
                    os.unlink(save_result[path_key])
    
    def test_upload_directory_creation(self):
        """Test that upload directories are created properly."""
        # The service should create directories on initialization
        service = upload_service
        
        assert service.upload_dir.exists()
        assert service.processed_dir.exists()
        assert service.temp_dir.exists()
        assert service.quarantine_dir.exists()
        
        # Check that directories are actually directories
        assert service.upload_dir.is_dir()
        assert service.processed_dir.is_dir()
        assert service.temp_dir.is_dir()
        assert service.quarantine_dir.is_dir()


def test_upload_service_configuration():
    """Test that upload service is configured correctly."""
    # Check that required settings are present
    assert hasattr(settings, 'UPLOAD_DIR')
    assert hasattr(settings, 'MAX_UPLOAD_SIZE')
    
    # Check that upload directory setting is valid
    upload_dir = Path(settings.UPLOAD_DIR)
    assert upload_dir.is_absolute() or str(upload_dir).startswith('./')
    
    # Check that max upload size is reasonable
    assert settings.MAX_UPLOAD_SIZE > 0
    assert settings.MAX_UPLOAD_SIZE <= 50 * 1024 * 1024  # Not more than 50MB


if __name__ == "__main__":
    # Run basic tests
    print("Testing upload service configuration...")
    test_upload_service_configuration()
    print("✓ Configuration tests passed")
    
    print("\nTesting directory creation...")
    test_service = TestFileUploadService()
    test_service.test_upload_directory_creation()
    print("✓ Directory creation tests passed")
    
    print("\nAll basic tests completed successfully!")
    print("\nTo run full async tests, use: pytest test_upload_service.py -v")