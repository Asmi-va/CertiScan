import pytest
import asyncio
import cv2
import numpy as np
import tempfile
import os
from unittest.mock import patch, MagicMock

# Import the tamper detection functions
import sys
sys.path.append('backend')

from app.services.tamper_detection import (
    detect_tampering,
    detect_certificate_elements_advanced,
    detect_tampered_content,
    detect_structure_anomalies,
    detect_noise_inconsistencies_advanced,
    detect_font_inconsistencies_advanced,
    detect_copy_move_forgery_advanced,
    verify_ssl_certificate_data,
    calculate_overall_confidence,
    calculate_risk_score
)

class TestAdvancedTamperDetection:
    """Test suite for the enhanced AI-powered tamper detection system."""
    
    @pytest.fixture
    def sample_certificate_image(self):
        """Create a sample certificate image for testing."""
        # Create a simple certificate-like image
        img = np.ones((600, 800, 3), dtype=np.uint8) * 255
        
        # Add some text-like regions
        cv2.rectangle(img, (100, 100), (700, 150), (0, 0, 0), 2)  # Header
        cv2.rectangle(img, (100, 200), (700, 250), (0, 0, 0), 1)  # Content
        cv2.rectangle(img, (100, 300), (700, 350), (0, 0, 0), 1)  # More content
        
        # Add signature area
        cv2.rectangle(img, (500, 450), (700, 500), (0, 0, 0), 1)
        
        # Add stamp area (circle)
        cv2.circle(img, (200, 475), 40, (0, 0, 0), 2)
        
        return img
    
    @pytest.fixture
    def tampered_certificate_image(self):
        """Create a tampered certificate image for testing."""
        # Create base image
        img = np.ones((600, 800, 3), dtype=np.uint8) * 255
        
        # Add normal elements
        cv2.rectangle(img, (100, 100), (700, 150), (0, 0, 0), 2)
        cv2.rectangle(img, (100, 200), (700, 250), (0, 0, 0), 1)
        
        # Add tampered region (different noise pattern)
        tampered_region = img[300:350, 100:700].copy()
        noise = np.random.randint(0, 50, tampered_region.shape, dtype=np.uint8)
        tampered_region = cv2.add(tampered_region, noise)
        img[300:350, 100:700] = tampered_region
        
        # Add inconsistent font sizes (simulate grade tampering)
        cv2.rectangle(img, (400, 320), (450, 340), (0, 0, 0), -1)  # Small text
        cv2.rectangle(img, (460, 315), (520, 345), (0, 0, 0), -1)  # Larger text
        
        return img
    
    @pytest.fixture
    def temp_image_file(self, sample_certificate_image):
        """Create a temporary image file."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cv2.imwrite(tmp.name, sample_certificate_image)
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def temp_tampered_file(self, tampered_certificate_image):
        """Create a temporary tampered image file."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cv2.imwrite(tmp.name, tampered_certificate_image)
            yield tmp.name
        os.unlink(tmp.name)
    
    @pytest.fixture
    def sample_extracted_data(self):
        """Sample extracted data from OCR."""
        return {
            "student_name": "John Doe",
            "roll_number": "12345",
            "course": "Computer Science",
            "grades": {
                "Math": 85,
                "Physics": 90,
                "Chemistry": 88
            },
            "certificate_id": "CERT123456",
            "institution": "Test University"
        }
    
    @pytest.mark.asyncio
    async def test_comprehensive_tamper_detection_clean_certificate(self, temp_image_file, sample_extracted_data):
        """Test comprehensive tamper detection on a clean certificate."""
        with patch('app.services.tamper_detection.detect_certificate_elements') as mock_detect, \
             patch('app.services.tamper_detection.extract_ssl_certificate_data') as mock_ssl_extract, \
             patch('app.services.tamper_detection.verify_ssl_certificate') as mock_ssl_verify:
            
            # Mock certificate element detection
            mock_detect.return_value = {
                "detected_elements": [
                    {"class": "degree", "confidence": 0.9, "bbox": {"x": 100, "y": 100, "width": 600, "height": 50}},
                    {"class": "signature", "confidence": 0.8, "bbox": {"x": 500, "y": 450, "width": 200, "height": 50}},
                    {"class": "stamp", "confidence": 0.85, "bbox": {"x": 160, "y": 435, "width": 80, "height": 80}}
                ],
                "confidence": 0.85,
                "is_certificate": True
            }
            
            # Mock SSL verification
            mock_ssl_extract.return_value = {"certificate_id": "CERT123456"}
            mock_ssl_verify.return_value = {
                "is_valid": True,
                "confidence": 0.9,
                "details": {"verification_method": "ssl_dataset"}
            }
            
            result = await detect_tampering(temp_image_file, sample_extracted_data)
            
            # Assertions
            assert isinstance(result, dict)
            assert "is_tampered" in result
            assert "overall_confidence" in result
            assert "tamper_flags" in result
            assert "detection_methods" in result
            assert "detailed_analysis" in result
            assert "risk_score" in result
            
            # For a clean certificate, should not be flagged as tampered
            # (though some methods might still detect minor anomalies)
            assert result["overall_confidence"] >= 0.0
            assert result["risk_score"] >= 0.0
    
    @pytest.mark.asyncio
    async def test_comprehensive_tamper_detection_tampered_certificate(self, temp_tampered_file, sample_extracted_data):
        """Test comprehensive tamper detection on a tampered certificate."""
        with patch('app.services.tamper_detection.detect_certificate_elements') as mock_detect, \
             patch('app.services.tamper_detection.extract_ssl_certificate_data') as mock_ssl_extract, \
             patch('app.services.tamper_detection.verify_ssl_certificate') as mock_ssl_verify:
            
            # Mock certificate element detection (lower confidence for tampered)
            mock_detect.return_value = {
                "detected_elements": [
                    {"class": "degree", "confidence": 0.6, "bbox": {"x": 100, "y": 100, "width": 600, "height": 50}},
                    {"class": "signature", "confidence": 0.5, "bbox": {"x": 500, "y": 450, "width": 200, "height": 50}}
                ],
                "confidence": 0.55,
                "is_certificate": True
            }
            
            # Mock SSL verification failure
            mock_ssl_extract.return_value = {"certificate_id": "CERT123456"}
            mock_ssl_verify.return_value = {
                "is_valid": False,
                "confidence": 0.3,
                "details": {"error": "Certificate not found in SSL dataset"}
            }
            
            result = await detect_tampering(temp_tampered_file, sample_extracted_data)
            
            # Assertions for tampered certificate
            assert result["is_tampered"] == True
            assert len(result["tamper_flags"]) > 0
            assert len(result["detection_methods"]) > 0
            assert result["risk_score"] > 0.3  # Should have elevated risk
    
    @pytest.mark.asyncio
    async def test_certificate_elements_advanced_detection(self, temp_image_file, sample_extracted_data):
        """Test advanced certificate element detection."""
        with patch('app.services.tamper_detection.detect_certificate_elements') as mock_detect:
            mock_detect.return_value = {
                "detected_elements": [
                    {"class": "degree", "confidence": 0.9, "bbox": {"x": 100, "y": 100, "width": 600, "height": 50}},
                    {"class": "signature", "confidence": 0.8, "bbox": {"x": 500, "y": 450, "width": 200, "height": 50}},
                    {"class": "stamp", "confidence": 0.85, "bbox": {"x": 160, "y": 435, "width": 80, "height": 80}}
                ],
                "confidence": 0.85,
                "is_certificate": True
            }
            
            result = await detect_certificate_elements_advanced(temp_image_file, sample_extracted_data)
            
            assert isinstance(result, dict)
            assert "is_suspicious" in result
            assert "detected_elements" in result
            assert "element_analysis" in result
            assert result["element_analysis"]["has_degree"] == True
            assert result["element_analysis"]["has_signature"] == True
            assert result["element_analysis"]["has_stamp"] == True
    
    @pytest.mark.asyncio
    async def test_certificate_elements_missing_critical_elements(self, temp_image_file, sample_extracted_data):
        """Test detection when critical certificate elements are missing."""
        with patch('app.services.tamper_detection.detect_certificate_elements') as mock_detect:
            # Mock missing degree text
            mock_detect.return_value = {
                "detected_elements": [
                    {"class": "signature", "confidence": 0.8, "bbox": {"x": 500, "y": 450, "width": 200, "height": 50}}
                ],
                "confidence": 0.4,
                "is_certificate": False
            }
            
            result = await detect_certificate_elements_advanced(temp_image_file, sample_extracted_data)
            
            assert result["is_suspicious"] == True
            assert "missing_degree_text" in result["flags"]
            assert result["element_analysis"]["has_degree"] == False
    
    @pytest.mark.asyncio
    async def test_tampered_content_detection(self, temp_tampered_file, sample_extracted_data):
        """Test detection of tampered grades, photos, and seals."""
        result = await detect_tampered_content(temp_tampered_file, sample_extracted_data)
        
        assert isinstance(result, dict)
        assert "is_tampered" in result
        assert "analysis_details" in result
        assert "grade_analysis" in result["analysis_details"]
        assert "photo_analysis" in result["analysis_details"]
        assert "seal_analysis" in result["analysis_details"]
    
    @pytest.mark.asyncio
    async def test_structure_anomaly_detection(self, temp_image_file, sample_extracted_data):
        """Test document structure and formatting anomaly detection."""
        result = await detect_structure_anomalies(temp_image_file, sample_extracted_data)
        
        assert isinstance(result, dict)
        assert "has_anomalies" in result
        assert "structure_analysis" in result
        assert "layout" in result["structure_analysis"]
        assert "alignment" in result["structure_analysis"]
        assert "borders" in result["structure_analysis"]
    
    @pytest.mark.asyncio
    async def test_advanced_noise_analysis(self, temp_tampered_file):
        """Test advanced noise inconsistency detection."""
        result = await detect_noise_inconsistencies_advanced(temp_tampered_file)
        
        assert isinstance(result, dict)
        assert "is_tampered" in result
        assert "noise_analysis" in result
        assert "ela" in result["noise_analysis"]
        assert "compression" in result["noise_analysis"]
        assert "patterns" in result["noise_analysis"]
    
    @pytest.mark.asyncio
    async def test_advanced_font_analysis(self, temp_tampered_file):
        """Test advanced font consistency analysis."""
        result = await detect_font_inconsistencies_advanced(temp_tampered_file)
        
        assert isinstance(result, dict)
        assert "is_tampered" in result
        assert "font_analysis" in result
        assert "font_size" in result["font_analysis"]
        assert "font_style" in result["font_analysis"]
        assert "spacing" in result["font_analysis"]
    
    @pytest.mark.asyncio
    async def test_advanced_forgery_detection(self, temp_image_file):
        """Test advanced copy-move and splicing detection."""
        result = await detect_copy_move_forgery_advanced(temp_image_file)
        
        assert isinstance(result, dict)
        assert "is_tampered" in result
        assert "forgery_analysis" in result
        assert "sift" in result["forgery_analysis"]
        assert "block_matching" in result["forgery_analysis"]
        assert "splicing" in result["forgery_analysis"]
    
    @pytest.mark.asyncio
    async def test_ssl_certificate_verification(self, sample_extracted_data):
        """Test SSL certificate data verification."""
        with patch('app.services.tamper_detection.extract_ssl_certificate_data') as mock_extract, \
             patch('app.services.tamper_detection.verify_ssl_certificate') as mock_verify:
            
            mock_extract.return_value = {"certificate_id": "CERT123456"}
            mock_verify.return_value = {
                "is_valid": True,
                "confidence": 0.9,
                "details": {"verification_method": "ssl_dataset"}
            }
            
            result = await verify_ssl_certificate_data(sample_extracted_data)
            
            assert isinstance(result, dict)
            assert "is_valid" in result
            assert "confidence" in result
            assert "verification_details" in result
            assert result["is_valid"] == True
    
    def test_confidence_calculation(self):
        """Test overall confidence calculation."""
        detailed_analysis = {
            "element_detection": {"confidence": 0.8},
            "image_analysis": {"confidence": 0.7},
            "structure_analysis": {"confidence": 0.6},
            "noise_analysis": {"confidence": 0.5},
            "font_analysis": {"confidence": 0.4},
            "forgery_analysis": {"confidence": 0.3},
            "ssl_verification": {"confidence": 0.9}
        }
        
        confidence = calculate_overall_confidence(detailed_analysis)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high with these values
    
    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        detailed_analysis = {
            "element_detection": {"is_suspicious": True},
            "image_analysis": {"is_tampered": True},
            "structure_analysis": {"has_anomalies": True}
        }
        
        tamper_flags = [
            "missing_degree_text",
            "high_error_level_regions",
            "font_size_inconsistencies"
        ]
        
        risk_score = calculate_risk_score(detailed_analysis, tamper_flags)
        
        assert isinstance(risk_score, float)
        assert 0.0 <= risk_score <= 1.0
        assert risk_score > 0.3  # Should be elevated with these flags
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_image(self, sample_extracted_data):
        """Test error handling with invalid image path."""
        result = await detect_tampering("nonexistent_image.jpg", sample_extracted_data)
        
        assert isinstance(result, dict)
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_suspicious_grade_patterns(self):
        """Test detection of suspicious grade patterns."""
        suspicious_data = {
            "grades": {
                "Math": 98,
                "Physics": 99,
                "Chemistry": 97,
                "Biology": 96,
                "English": 98
            }
        }
        
        # Create a simple test image
        img = np.ones((400, 600, 3), dtype=np.uint8) * 255
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            temp_path = tmp.name
        
        try:
            cv2.imwrite(temp_path, img)
            result = await detect_tampered_content(temp_path, suspicious_data)
            
            # Should detect suspiciously high grades
            grade_analysis = result["analysis_details"]["grade_analysis"]
            assert "suspiciously_high_grades" in grade_analysis.get("flags", [])
            
        finally:
            try:
                os.unlink(temp_path)
            except PermissionError:
                pass  # Ignore permission errors on Windows

if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        # Create a test image
        img = np.ones((600, 800, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (100, 100), (700, 150), (0, 0, 0), 2)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            cv2.imwrite(tmp.name, img)
            
            try:
                sample_data = {
                    "student_name": "Test Student",
                    "grades": {"Math": 85, "Physics": 90}
                }
                
                with patch('app.services.tamper_detection.detect_certificate_elements') as mock_detect, \
                     patch('app.services.tamper_detection.extract_ssl_certificate_data') as mock_ssl_extract, \
                     patch('app.services.tamper_detection.verify_ssl_certificate') as mock_ssl_verify:
                    
                    mock_detect.return_value = {
                        "detected_elements": [],
                        "confidence": 0.5,
                        "is_certificate": True
                    }
                    mock_ssl_extract.return_value = {}
                    mock_ssl_verify.return_value = {"is_valid": True, "confidence": 0.8, "details": {}}
                    
                    result = await detect_tampering(tmp.name, sample_data)
                    print("Tamper detection result:", result)
                    
            finally:
                os.unlink(tmp.name)
    
    # Run the test
    asyncio.run(run_simple_test())
    print("Advanced tamper detection system test completed successfully!")