import cv2
import numpy as np
import hashlib
from typing import Dict, Any, List, Optional, Tuple
import os
import logging
from pathlib import Path

from app.core.config import settings
from app.services.certificate_detection import detect_certificate_elements, verify_certificate_authenticity
from app.services.ssl_verification import extract_ssl_certificate_data, verify_ssl_certificate

# Set up logging
logger = logging.getLogger(__name__)


async def detect_tampering(image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive tamper detection system for certificates.
    
    Implements multiple detection methods:
    1. YOLOv5-based certificate element detection
    2. Image analysis for tampered grades, photos, and seals
    3. Document structure and formatting anomaly detection
    4. Confidence scoring and detailed tamper flag reporting
    """
    result = {
        "is_tampered": False,
        "overall_confidence": 0.0,
        "tamper_flags": [],
        "detection_methods": [],
        "tampered_areas": [],
        "detailed_analysis": {},
        "risk_score": 0.0
    }
    
    logger.info(f"Starting comprehensive tamper detection for: {image_path}")
    
    try:
        # Method 1: YOLOv5 Certificate Element Detection
        element_result = await detect_certificate_elements_advanced(image_path, extracted_data)
        result["detailed_analysis"]["element_detection"] = element_result
        if element_result["is_suspicious"]:
            result["is_tampered"] = True
            result["detection_methods"].append("yolov5_element_detection")
            result["tamper_flags"].extend(element_result["flags"])
            result["tampered_areas"].extend(element_result["suspicious_areas"])
        
        # Method 2: Advanced Image Analysis for Tampered Content
        image_analysis_result = await detect_tampered_content(image_path, extracted_data)
        result["detailed_analysis"]["image_analysis"] = image_analysis_result
        if image_analysis_result["is_tampered"]:
            result["is_tampered"] = True
            result["detection_methods"].append("advanced_image_analysis")
            result["tamper_flags"].extend(image_analysis_result["flags"])
            result["tampered_areas"].extend(image_analysis_result["tampered_areas"])
        
        # Method 3: Document Structure and Formatting Anomaly Detection
        structure_result = await detect_structure_anomalies(image_path, extracted_data)
        result["detailed_analysis"]["structure_analysis"] = structure_result
        if structure_result["has_anomalies"]:
            result["is_tampered"] = True
            result["detection_methods"].append("structure_anomaly_detection")
            result["tamper_flags"].extend(structure_result["anomaly_flags"])
            result["tampered_areas"].extend(structure_result["anomalous_areas"])
        
        # Method 4: Enhanced Noise and Compression Analysis
        noise_result = await detect_noise_inconsistencies_advanced(image_path)
        result["detailed_analysis"]["noise_analysis"] = noise_result
        if noise_result["is_tampered"]:
            result["is_tampered"] = True
            result["detection_methods"].append("advanced_noise_analysis")
            result["tamper_flags"].extend(noise_result["flags"])
            result["tampered_areas"].extend(noise_result["tampered_areas"])
        
        # Method 5: Font and Text Consistency Analysis
        font_result = await detect_font_inconsistencies_advanced(image_path)
        result["detailed_analysis"]["font_analysis"] = font_result
        if font_result["is_tampered"]:
            result["is_tampered"] = True
            result["detection_methods"].append("advanced_font_analysis")
            result["tamper_flags"].extend(font_result["flags"])
            result["tampered_areas"].extend(font_result["tampered_areas"])
        
        # Method 6: Copy-Move and Splicing Detection
        forgery_result = await detect_copy_move_forgery_advanced(image_path)
        result["detailed_analysis"]["forgery_analysis"] = forgery_result
        if forgery_result["is_tampered"]:
            result["is_tampered"] = True
            result["detection_methods"].append("advanced_forgery_detection")
            result["tamper_flags"].extend(forgery_result["flags"])
            result["tampered_areas"].extend(forgery_result["tampered_areas"])
        
        # Method 7: SSL Certificate Data Verification
        try:
            ssl_result = await verify_ssl_certificate_data(extracted_data)
            result["detailed_analysis"]["ssl_verification"] = ssl_result
            if not ssl_result["is_valid"]:
                result["is_tampered"] = True
                result["detection_methods"].append("ssl_data_verification")
                result["tamper_flags"].extend(ssl_result["flags"])
        except Exception as e:
            logger.error(f"SSL verification error: {str(e)}")
            result["detailed_analysis"]["ssl_verification"] = {
                "is_valid": False,
                "confidence": 0.0,
                "flags": ["ssl_verification_error"],
                "verification_details": {"error": str(e)}
            }
        
        # Calculate overall confidence and risk score
        result["overall_confidence"] = calculate_overall_confidence(result["detailed_analysis"])
        result["risk_score"] = calculate_risk_score(result["detailed_analysis"], result["tamper_flags"])
        
        # Generate file hash for integrity checking
        result["file_hash"] = calculate_file_hash(image_path)
        
        logger.info(f"Tamper detection completed. Is tampered: {result['is_tampered']}, "
                   f"Confidence: {result['overall_confidence']:.2f}, "
                   f"Risk Score: {result['risk_score']:.2f}")
        
    except Exception as e:
        logger.error(f"Error in tamper detection: {str(e)}")
        result["error"] = f"Tamper detection failed: {str(e)}"
    
    return result


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# Enhanced Detection Methods for Task 6

async def detect_certificate_elements_advanced(image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced YOLOv5-based certificate element detection with enhanced analysis.
    Detects degree text, signatures, stamps, and validates their authenticity.
    """
    result = {
        "is_suspicious": False,
        "confidence": 0.0,
        "flags": [],
        "suspicious_areas": [],
        "detected_elements": [],
        "element_analysis": {}
    }
    
    try:
        # Use existing certificate detection
        detection_result = await detect_certificate_elements(image_path)
        
        if "error" in detection_result:
            result["flags"].append("element_detection_failed")
            result["element_analysis"]["error"] = detection_result["error"]
            return result
        
        result["detected_elements"] = detection_result["detected_elements"]
        result["confidence"] = detection_result["confidence"]
        
        # Enhanced analysis of detected elements
        if not detection_result["is_certificate"]:
            result["is_suspicious"] = True
            result["flags"].append("no_certificate_elements_detected")
            result["element_analysis"]["reason"] = "Document lacks expected certificate elements"
        
        # Analyze element positioning and authenticity
        elements = detection_result["detected_elements"]
        
        # Check for missing critical elements
        has_degree = any(e["class"] == "degree" for e in elements)
        has_signature = any(e["class"] == "signature" for e in elements)
        has_stamp = any(e["class"] == "stamp" for e in elements)
        
        if not has_degree:
            result["is_suspicious"] = True
            result["flags"].append("missing_degree_text")
        
        if not (has_signature or has_stamp):
            result["is_suspicious"] = True
            result["flags"].append("missing_authentication_elements")
        
        # Analyze element quality and positioning
        for element in elements:
            bbox = element["bbox"]
            confidence = element["confidence"]
            
            # Flag low-confidence detections
            if confidence < 0.6:
                result["is_suspicious"] = True
                result["flags"].append(f"low_confidence_{element['class']}")
                result["suspicious_areas"].append({
                    "x": bbox["x"],
                    "y": bbox["y"],
                    "width": bbox["width"],
                    "height": bbox["height"],
                    "type": f"low_confidence_{element['class']}",
                    "confidence": confidence
                })
        
        result["element_analysis"]["has_degree"] = has_degree
        result["element_analysis"]["has_signature"] = has_signature
        result["element_analysis"]["has_stamp"] = has_stamp
        result["element_analysis"]["total_elements"] = len(elements)
        
    except Exception as e:
        logger.error(f"Error in advanced certificate element detection: {str(e)}")
        result["flags"].append("element_detection_error")
        result["element_analysis"]["error"] = str(e)
    
    return result


async def detect_tampered_content(image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect tampered grades, photos, and seals using advanced image analysis.
    """
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": [],
        "analysis_details": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            result["flags"].append("image_read_error")
            return result
        
        # 1. Detect tampered grades using OCR region analysis
        grade_analysis = await analyze_grade_tampering(image, extracted_data)
        result["analysis_details"]["grade_analysis"] = grade_analysis
        if grade_analysis["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(grade_analysis["flags"])
            result["tampered_areas"].extend(grade_analysis["tampered_areas"])
        
        # 2. Detect photo tampering
        photo_analysis = await analyze_photo_tampering(image)
        result["analysis_details"]["photo_analysis"] = photo_analysis
        if photo_analysis["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(photo_analysis["flags"])
            result["tampered_areas"].extend(photo_analysis["tampered_areas"])
        
        # 3. Detect seal tampering
        seal_analysis = await analyze_seal_tampering(image)
        result["analysis_details"]["seal_analysis"] = seal_analysis
        if seal_analysis["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(seal_analysis["flags"])
            result["tampered_areas"].extend(seal_analysis["tampered_areas"])
        
        # Calculate overall confidence
        confidences = []
        for analysis in [grade_analysis, photo_analysis, seal_analysis]:
            if analysis.get("confidence", 0) > 0:
                confidences.append(analysis["confidence"])
        
        if confidences:
            result["confidence"] = sum(confidences) / len(confidences)
        
    except Exception as e:
        logger.error(f"Error in tampered content detection: {str(e)}")
        result["flags"].append("content_analysis_error")
        result["analysis_details"]["error"] = str(e)
    
    return result


async def detect_structure_anomalies(image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect document structure and formatting inconsistencies.
    """
    result = {
        "has_anomalies": False,
        "confidence": 0.0,
        "anomaly_flags": [],
        "anomalous_areas": [],
        "structure_analysis": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            result["anomaly_flags"].append("image_read_error")
            return result
        
        # Analyze document layout consistency
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect horizontal and vertical lines (typical in certificates)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
        
        # Check for line consistency
        h_line_count = cv2.countNonZero(horizontal_lines)
        v_line_count = cv2.countNonZero(vertical_lines)
        
        # Certificates should have some structural lines
        if h_line_count < 100 and v_line_count < 100:
            result["has_anomalies"] = True
            result["anomaly_flags"].append("missing_structural_lines")
        
        # Check for margin consistency
        height, width = gray.shape
        
        # Analyze margins by checking pixel density at edges
        top_margin = np.mean(gray[:int(height*0.1), :])
        bottom_margin = np.mean(gray[int(height*0.9):, :])
        left_margin = np.mean(gray[:, :int(width*0.1)])
        right_margin = np.mean(gray[:, int(width*0.9):])
        
        margins = [top_margin, bottom_margin, left_margin, right_margin]
        margin_std = np.std(margins)
        
        # Inconsistent margins might indicate tampering
        if margin_std > 50:
            result["has_anomalies"] = True
            result["anomaly_flags"].append("inconsistent_margins")
        
        if result["anomaly_flags"]:
            result["confidence"] = 0.6
        
        result["structure_analysis"]["h_line_count"] = h_line_count
        result["structure_analysis"]["v_line_count"] = v_line_count
        result["structure_analysis"]["margin_std"] = float(margin_std)
        result["structure_analysis"]["layout"] = {
            "horizontal_lines": h_line_count,
            "vertical_lines": v_line_count,
            "margin_consistency": margin_std
        }
        result["structure_analysis"]["alignment"] = {
            "text_alignment": "consistent" if margin_std < 30 else "inconsistent",
            "border_alignment": "consistent" if h_line_count > 50 else "inconsistent"
        }
        result["structure_analysis"]["borders"] = {
            "has_borders": h_line_count > 100 or v_line_count > 100,
            "border_quality": "good" if (h_line_count + v_line_count) > 200 else "poor"
        }
        
    except Exception as e:
        logger.error(f"Error in structure anomaly detection: {str(e)}")
        result["anomaly_flags"].append("structure_analysis_error")
        result["structure_analysis"]["error"] = str(e)
    
    return result


async def detect_noise_inconsistencies_advanced(image_path: str) -> Dict[str, Any]:
    """
    Enhanced noise analysis with multiple algorithms for tamper detection.
    """
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": [],
        "noise_analysis": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            result["flags"].append("image_read_error")
            return result
        
        # Error Level Analysis (ELA)
        ela_result = perform_error_level_analysis(image, image_path)
        result["noise_analysis"]["ela"] = ela_result
        if ela_result["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(ela_result["flags"])
            result["tampered_areas"].extend(ela_result["tampered_areas"])
        
        # Noise Pattern Analysis
        noise_pattern_result = analyze_noise_patterns(image)
        result["noise_analysis"]["patterns"] = noise_pattern_result
        if noise_pattern_result["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(noise_pattern_result["flags"])
            result["tampered_areas"].extend(noise_pattern_result["tampered_areas"])
        
        # Add compression analysis
        compression_result = analyze_compression_artifacts(image)
        result["noise_analysis"]["compression"] = compression_result
        if compression_result["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(compression_result["flags"])
            result["tampered_areas"].extend(compression_result["tampered_areas"])
        
        # Calculate overall confidence
        confidences = [ela_result.get("confidence", 0), noise_pattern_result.get("confidence", 0), compression_result.get("confidence", 0)]
        confidences = [c for c in confidences if c > 0]
        
        if confidences:
            result["confidence"] = sum(confidences) / len(confidences)
        
    except Exception as e:
        logger.error(f"Error in advanced noise analysis: {str(e)}")
        result["flags"].append("noise_analysis_error")
        result["noise_analysis"]["error"] = str(e)
    
    return result


async def detect_font_inconsistencies_advanced(image_path: str) -> Dict[str, Any]:
    """
    Advanced font and text consistency analysis.
    """
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": [],
        "font_analysis": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            result["flags"].append("image_read_error")
            return result
        
        # Font size consistency analysis
        font_size_result = analyze_font_size_consistency(image)
        result["font_analysis"]["font_size"] = font_size_result
        if font_size_result["is_inconsistent"]:
            result["is_tampered"] = True
            result["flags"].extend(font_size_result["flags"])
            result["tampered_areas"].extend(font_size_result["inconsistent_areas"])
        
        # Font style analysis
        font_style_result = analyze_font_style_consistency(image)
        result["font_analysis"]["font_style"] = font_style_result
        if font_style_result["is_inconsistent"]:
            result["is_tampered"] = True
            result["flags"].extend(font_style_result["flags"])
            result["tampered_areas"].extend(font_style_result["inconsistent_areas"])
        
        # Font spacing analysis
        spacing_result = analyze_font_spacing_consistency(image)
        result["font_analysis"]["spacing"] = spacing_result
        if spacing_result["is_inconsistent"]:
            result["is_tampered"] = True
            result["flags"].extend(spacing_result["flags"])
            result["tampered_areas"].extend(spacing_result["inconsistent_areas"])
        
        if result["flags"]:
            result["confidence"] = 0.6
        
    except Exception as e:
        logger.error(f"Error in advanced font analysis: {str(e)}")
        result["flags"].append("font_analysis_error")
        result["font_analysis"]["error"] = str(e)
    
    return result


async def detect_copy_move_forgery_advanced(image_path: str) -> Dict[str, Any]:
    """
    Advanced copy-move and splicing detection using multiple algorithms.
    """
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": [],
        "forgery_analysis": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            result["flags"].append("image_read_error")
            return result
        
        # SIFT-based copy-move detection
        sift_result = detect_sift_copy_move(image)
        result["forgery_analysis"]["sift"] = sift_result
        if sift_result["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(sift_result["flags"])
            result["tampered_areas"].extend(sift_result["tampered_areas"])
        
        # Block matching detection
        block_matching_result = detect_block_matching_forgery(image)
        result["forgery_analysis"]["block_matching"] = block_matching_result
        if block_matching_result["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(block_matching_result["flags"])
            result["tampered_areas"].extend(block_matching_result["tampered_areas"])
        
        # Splicing detection
        splicing_result = detect_image_splicing(image)
        result["forgery_analysis"]["splicing"] = splicing_result
        if splicing_result["is_tampered"]:
            result["is_tampered"] = True
            result["flags"].extend(splicing_result["flags"])
            result["tampered_areas"].extend(splicing_result["tampered_areas"])
        
        if result["flags"]:
            result["confidence"] = 0.7
        
    except Exception as e:
        logger.error(f"Error in advanced forgery detection: {str(e)}")
        result["flags"].append("forgery_analysis_error")
        result["forgery_analysis"]["error"] = str(e)
    
    return result


async def verify_ssl_certificate_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced SSL certificate data verification.
    """
    result = {
        "is_valid": True,
        "confidence": 0.0,
        "flags": [],
        "verification_details": {}
    }
    
    try:
        # Use existing SSL verification with proper async handling
        from app.services.ssl_verification import extract_ssl_certificate_data, verify_ssl_certificate
        
        ssl_data = extract_ssl_certificate_data(extracted_data)
        ssl_result = await verify_ssl_certificate(ssl_data)
        
        result["verification_details"] = ssl_result.get("details", {})
        result["confidence"] = ssl_result.get("confidence", 0.0)
        
        if not ssl_result.get("is_valid", True):
            result["is_valid"] = False
            result["flags"].append("ssl_verification_failed")
            
            # Add specific failure reasons
            if "error" in ssl_result:
                result["flags"].append("ssl_data_error")
            if ssl_result.get("confidence", 0) < 0.5:
                result["flags"].append("low_ssl_confidence")
        
    except Exception as e:
        logger.error(f"Error in SSL certificate verification: {str(e)}")
        result["is_valid"] = False
        result["flags"].append("ssl_verification_error")
        result["verification_details"]["error"] = str(e)
    
    return result


# Helper Functions for Advanced Analysis

async def analyze_grade_tampering(image: np.ndarray, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze potential grade tampering in certificate."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Check extracted data for suspicious grade patterns
        if extracted_data and "grades" in extracted_data:
            grades = extracted_data["grades"]
            if isinstance(grades, dict):
                # Look for suspiciously high grades
                high_grades = [g for g in grades.values() if isinstance(g, (int, float)) and g > 95]
                if len(high_grades) > len(grades) * 0.8:  # More than 80% high grades
                    result["is_tampered"] = True
                    result["flags"].append("suspiciously_high_grades")
                    result["confidence"] = 0.7
        
    except Exception as e:
        logger.error(f"Error in grade tampering analysis: {str(e)}")
        result["flags"].append("grade_analysis_error")
    
    return result


async def analyze_photo_tampering(image: np.ndarray) -> Dict[str, Any]:
    """Analyze potential photo tampering in certificate."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Convert to different color spaces for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect potential photo regions using edge detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        photo_candidates = []
        for contour in contours:
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Look for rectangular regions that might be photos
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h) if h > 0 else 0
                area = cv2.contourArea(contour)
                
                # Photo-like dimensions
                if 0.7 < aspect_ratio < 1.5 and area > 2000:
                    photo_candidates.append((x, y, w, h))
        
        # Basic analysis - if we find potential photo regions, mark for further inspection
        if len(photo_candidates) > 0:
            result["confidence"] = 0.4  # Low confidence, needs human verification
        
    except Exception as e:
        logger.error(f"Error in photo tampering analysis: {str(e)}")
        result["flags"].append("photo_analysis_error")
    
    return result


async def analyze_seal_tampering(image: np.ndarray) -> Dict[str, Any]:
    """Analyze potential seal tampering in certificate."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect circular regions that might be seals
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1, minDist=50,
                                  param1=50, param2=30, minRadius=20, maxRadius=100)
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            
            for (x, y, r) in circles:
                # Extract circular region
                mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.circle(mask, (x, y), r, 255, -1)
                
                # Extract the seal region
                seal_region = cv2.bitwise_and(gray, gray, mask=mask)
                
                # Analyze seal characteristics
                non_zero_pixels = cv2.countNonZero(seal_region)
                expected_pixels = np.pi * r * r
                
                # Check if the seal has expected circular characteristics
                if non_zero_pixels < expected_pixels * 0.3:  # Too few pixels for a proper seal
                    result["is_tampered"] = True
                    result["flags"].append("incomplete_seal_pattern")
                    result["confidence"] = 0.6
        
    except Exception as e:
        logger.error(f"Error in seal tampering analysis: {str(e)}")
        result["flags"].append("seal_analysis_error")
    
    return result


def perform_error_level_analysis(image: np.ndarray, image_path: str) -> Dict[str, Any]:
    """Perform Error Level Analysis (ELA) for tamper detection."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Save image with specific JPEG quality
        temp_path = f"{image_path}_ela_temp.jpg"
        cv2.imwrite(temp_path, image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        # Read the compressed image
        compressed_image = cv2.imread(temp_path)
        os.remove(temp_path)  # Clean up
        
        if compressed_image is None:
            result["flags"].append("ela_compression_failed")
            return result
        
        # Calculate difference
        diff = cv2.absdiff(image, compressed_image)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # Enhance the difference
        enhanced = cv2.convertScaleAbs(diff_gray, alpha=15, beta=0)
        
        # Find regions with high error levels
        _, thresh = cv2.threshold(enhanced, 30, 255, cv2.THRESH_BINARY)
        
        # Find contours of high-error regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        significant_areas = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 200:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                significant_areas.append((x, y, w, h, area))
        
        # If we have significant high-error areas, flag as potentially tampered
        if len(significant_areas) > 3:
            result["is_tampered"] = True
            result["flags"].append("high_error_level_regions")
            result["confidence"] = min(0.8, 0.4 + len(significant_areas) * 0.05)
            
            for x, y, w, h, area in significant_areas:
                result["tampered_areas"].append({
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h),
                    "type": "high_error_level",
                    "area": float(area)
                })
        
    except Exception as e:
        logger.error(f"Error in ELA analysis: {str(e)}")
        result["flags"].append("ela_analysis_error")
    
    return result


def analyze_noise_patterns(image: np.ndarray) -> Dict[str, Any]:
    """Analyze noise patterns for tamper detection."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur and subtract to isolate noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.absdiff(gray, blurred)
        
        # Analyze noise distribution
        height, width = noise.shape
        block_size = 32
        
        noise_inconsistencies = []
        
        for y in range(0, height - block_size, block_size):
            for x in range(0, width - block_size, block_size):
                block = noise[y:y+block_size, x:x+block_size]
                
                # Calculate noise statistics
                noise_std = np.std(block)
                
                # Check for unusual noise patterns
                if noise_std > 15:  # Threshold for suspicious noise
                    noise_inconsistencies.append((x, y, block_size, block_size))
        
        # Flag if too many blocks have unusual noise
        if len(noise_inconsistencies) > 10:
            result["is_tampered"] = True
            result["flags"].append("unusual_noise_patterns")
            result["confidence"] = min(0.6, 0.2 + len(noise_inconsistencies) * 0.02)
            
            for x, y, w, h in noise_inconsistencies:
                result["tampered_areas"].append({
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h),
                    "type": "unusual_noise_pattern"
                })
        
    except Exception as e:
        logger.error(f"Error in noise pattern analysis: {str(e)}")
        result["flags"].append("noise_pattern_analysis_error")
    
    return result


def analyze_font_size_consistency(image: np.ndarray) -> Dict[str, Any]:
    """Analyze font size consistency."""
    result = {
        "is_inconsistent": False,
        "confidence": 0.0,
        "flags": [],
        "inconsistent_areas": []
    }
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect text regions
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY_INV, 11, 2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Extract character heights
        char_heights = []
        char_regions = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0
            
            # Filter for character-like regions
            if 0.1 < aspect_ratio < 3 and 8 < h < 100 and w > 5:
                char_heights.append(h)
                char_regions.append((x, y, w, h))
        
        if len(char_heights) > 5:
            # Analyze height distribution
            heights_array = np.array(char_heights)
            mean_height = np.mean(heights_array)
            std_height = np.std(heights_array)
            
            # Find outliers (characters with unusual sizes)
            outliers = []
            for i, (height, region) in enumerate(zip(char_heights, char_regions)):
                if abs(height - mean_height) > 2 * std_height:
                    outliers.append((region, height))
            
            # If we have many outliers, flag as inconsistent
            if len(outliers) > len(char_heights) * 0.2:  # More than 20% outliers
                result["is_inconsistent"] = True
                result["flags"].append("font_size_inconsistencies")
                result["confidence"] = min(0.7, 0.3 + len(outliers) * 0.05)
                
                for (x, y, w, h), height in outliers:
                    result["inconsistent_areas"].append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h),
                        "type": "unusual_font_size",
                        "height": int(height),
                        "deviation": float(abs(height - mean_height))
                    })
        
    except Exception as e:
        logger.error(f"Error in font size analysis: {str(e)}")
        result["flags"].append("font_size_analysis_error")
    
    return result


def detect_sift_copy_move(image: np.ndarray) -> Dict[str, Any]:
    """Detect copy-move forgery using SIFT features."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect SIFT keypoints and descriptors
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        if descriptors is None or len(keypoints) < 10:
            return result
        
        # Match descriptors with themselves to find duplicates
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        
        matches = flann.knnMatch(descriptors, descriptors, k=2)
        
        # Filter good matches (excluding self-matches)
        good_matches = []
        for i, match_pair in enumerate(matches):
            if len(match_pair) == 2:
                m, n = match_pair
                if m.trainIdx != i and m.distance < 0.7 * n.distance:
                    # Check spatial distance
                    pt1 = keypoints[i].pt
                    pt2 = keypoints[m.trainIdx].pt
                    distance = np.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)
                    
                    if distance > 50:  # Minimum distance for copy-move
                        good_matches.append((i, m.trainIdx, distance))
        
        # If we have enough matches, flag as copy-move forgery
        if len(good_matches) > 15:
            result["is_tampered"] = True
            result["flags"].append("sift_copy_move_detected")
            result["confidence"] = min(0.9, 0.5 + len(good_matches) * 0.02)
            
            # Add general tampered area (simplified)
            result["tampered_areas"].append({
                "x": 0,
                "y": 0,
                "width": gray.shape[1],
                "height": gray.shape[0],
                "type": "copy_move_region",
                "matches": len(good_matches)
            })
        
    except Exception as e:
        logger.error(f"Error in SIFT copy-move detection: {str(e)}")
        result["flags"].append("sift_analysis_error")
    
    return result


def calculate_overall_confidence(detailed_analysis: Dict[str, Any]) -> float:
    """Calculate overall confidence score from all analysis methods."""
    confidences = []
    weights = {
        "element_detection": 0.25,
        "image_analysis": 0.20,
        "structure_analysis": 0.15,
        "noise_analysis": 0.15,
        "font_analysis": 0.10,
        "forgery_analysis": 0.10,
        "ssl_verification": 0.05
    }
    
    total_weight = 0
    weighted_sum = 0
    
    for method, analysis in detailed_analysis.items():
        if method in weights and isinstance(analysis, dict):
            confidence = analysis.get("confidence", 0.0)
            if confidence > 0:
                weight = weights[method]
                weighted_sum += confidence * weight
                total_weight += weight
    
    if total_weight > 0:
        return weighted_sum / total_weight
    else:
        return 0.0


def calculate_risk_score(detailed_analysis: Dict[str, Any], tamper_flags: List[str]) -> float:
    """Calculate risk score based on analysis results and flags."""
    base_score = 0.0
    
    # Score based on number and severity of flags
    flag_weights = {
        "no_certificate_elements_detected": 0.3,
        "missing_degree_text": 0.25,
        "missing_authentication_elements": 0.25,
        "high_error_level_regions": 0.2,
        "sift_copy_move_detected": 0.25,
        "font_size_inconsistencies": 0.1,
        "ssl_verification_failed": 0.15,
        "suspiciously_high_grades": 0.15
    }
    
    for flag in tamper_flags:
        if flag in flag_weights:
            base_score += flag_weights[flag]
        else:
            base_score += 0.05  # Default weight for unknown flags
    
    # Boost score based on number of detection methods that found issues
    methods_with_issues = 0
    for method, analysis in detailed_analysis.items():
        if isinstance(analysis, dict):
            if (analysis.get("is_tampered", False) or 
                analysis.get("is_suspicious", False) or 
                analysis.get("has_anomalies", False) or 
                not analysis.get("is_valid", True)):
                methods_with_issues += 1
    
    # Multiple methods agreeing increases confidence
    if methods_with_issues > 1:
        base_score *= (1 + (methods_with_issues - 1) * 0.2)
    
    # Cap the score at 1.0
    return min(1.0, base_score)


# Legacy functions for backward compatibility
async def detect_noise_inconsistencies(image_path: str) -> Dict[str, Any]:
    """Legacy function for backward compatibility."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "tampered_areas": [],
        "details": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")
        
        # Simple noise analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = cv2.absdiff(gray, blurred)
        
        # Calculate overall noise level
        noise_level = np.mean(noise)
        
        if noise_level > 10:  # Threshold for suspicious noise
            result["is_tampered"] = True
            result["confidence"] = min(0.7, noise_level / 20)
            result["details"]["noise_level"] = float(noise_level)
    
    except Exception as e:
        result["details"]["error"] = str(e)
    
    return result


async def detect_font_inconsistencies(image_path: str) -> Dict[str, Any]:
    """Legacy function for backward compatibility."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "tampered_areas": [],
        "details": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")
        
        # Simple font analysis
        font_result = analyze_font_size_consistency(image)
        
        if font_result["is_inconsistent"]:
            result["is_tampered"] = True
            result["confidence"] = font_result["confidence"]
            result["tampered_areas"] = font_result["inconsistent_areas"]
            result["details"] = font_result
    
    except Exception as e:
        result["details"]["error"] = str(e)
    
    return result


async def detect_copy_move_forgery(image_path: str) -> Dict[str, Any]:
    """Legacy function for backward compatibility."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "tampered_areas": [],
        "details": {}
    }
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")
        
        # Simple copy-move detection
        sift_result = detect_sift_copy_move(image)
        
        if sift_result["is_tampered"]:
            result["is_tampered"] = True
            result["confidence"] = sift_result["confidence"]
            result["tampered_areas"] = sift_result["tampered_areas"]
            result["details"] = sift_result
    
    except Exception as e:
        result["details"]["error"] = str(e)
    
    return result

# Additional helper functions for comprehensive analysis

def analyze_compression_artifacts(image: np.ndarray) -> Dict[str, Any]:
    """Analyze compression artifacts for tamper detection."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply DCT to detect compression inconsistencies
        # Simple approach: look for unusual frequency patterns
        height, width = gray.shape
        block_size = 8
        
        compression_inconsistencies = []
        
        for y in range(0, height - block_size, block_size):
            for x in range(0, width - block_size, block_size):
                block = gray[y:y+block_size, x:x+block_size].astype(np.float32)
                
                # Apply DCT
                dct_block = cv2.dct(block)
                
                # Check for unusual DCT coefficients
                high_freq_energy = np.sum(np.abs(dct_block[4:, 4:]))
                total_energy = np.sum(np.abs(dct_block))
                
                if total_energy > 0:
                    high_freq_ratio = high_freq_energy / total_energy
                    
                    # Unusual high frequency content might indicate tampering
                    if high_freq_ratio > 0.3:
                        compression_inconsistencies.append((x, y, block_size, block_size))
        
        # Flag if too many blocks have compression inconsistencies
        if len(compression_inconsistencies) > 20:
            result["is_tampered"] = True
            result["flags"].append("compression_artifacts_detected")
            result["confidence"] = min(0.7, 0.3 + len(compression_inconsistencies) * 0.01)
            
            for x, y, w, h in compression_inconsistencies:
                result["tampered_areas"].append({
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h),
                    "type": "compression_artifact"
                })
    
    except Exception as e:
        logger.error(f"Error in compression analysis: {str(e)}")
        result["flags"].append("compression_analysis_error")
    
    return result


def analyze_font_style_consistency(image: np.ndarray) -> Dict[str, Any]:
    """Analyze font style consistency."""
    result = {
        "is_inconsistent": False,
        "confidence": 0.0,
        "flags": [],
        "inconsistent_areas": []
    }
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect text regions using morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find text regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze stroke width variations
        stroke_widths = []
        text_regions = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter for text-like regions
            if w > 10 and h > 8 and w < 200 and h < 50:
                text_region = thresh[y:y+h, x:x+w]
                
                # Estimate stroke width using distance transform
                dist_transform = cv2.distanceTransform(text_region, cv2.DIST_L2, 5)
                stroke_width = np.mean(dist_transform[dist_transform > 0]) * 2
                
                if stroke_width > 0:
                    stroke_widths.append(stroke_width)
                    text_regions.append((x, y, w, h, stroke_width))
        
        if len(stroke_widths) > 3:
            # Analyze stroke width consistency
            mean_stroke = np.mean(stroke_widths)
            std_stroke = np.std(stroke_widths)
            
            # Find regions with unusual stroke widths
            outliers = []
            for x, y, w, h, stroke_width in text_regions:
                if abs(stroke_width - mean_stroke) > 2 * std_stroke:
                    outliers.append((x, y, w, h, stroke_width))
            
            # Flag if too many outliers
            if len(outliers) > len(text_regions) * 0.3:
                result["is_inconsistent"] = True
                result["flags"].append("font_style_inconsistencies")
                result["confidence"] = min(0.8, 0.4 + len(outliers) * 0.05)
                
                for x, y, w, h, stroke_width in outliers:
                    result["inconsistent_areas"].append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h),
                        "type": "unusual_font_style",
                        "stroke_width": float(stroke_width)
                    })
    
    except Exception as e:
        logger.error(f"Error in font style analysis: {str(e)}")
        result["flags"].append("font_style_analysis_error")
    
    return result


def analyze_font_spacing_consistency(image: np.ndarray) -> Dict[str, Any]:
    """Analyze font spacing consistency."""
    result = {
        "is_inconsistent": False,
        "confidence": 0.0,
        "flags": [],
        "inconsistent_areas": []
    }
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect text using adaptive threshold
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Group contours by horizontal lines (approximate text lines)
        text_lines = {}
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter for character-like regions
            if 5 < w < 100 and 8 < h < 50:
                line_y = y + h // 2  # Middle of character
                
                # Group by approximate line
                line_key = line_y // 10 * 10  # Group within 10 pixels
                if line_key not in text_lines:
                    text_lines[line_key] = []
                text_lines[line_key].append((x, y, w, h))
        
        # Analyze spacing within each line
        spacing_inconsistencies = []
        
        for line_y, chars in text_lines.items():
            if len(chars) > 2:
                # Sort characters by x position
                chars.sort(key=lambda c: c[0])
                
                # Calculate spacing between characters
                spacings = []
                for i in range(len(chars) - 1):
                    x1, y1, w1, h1 = chars[i]
                    x2, y2, w2, h2 = chars[i + 1]
                    spacing = x2 - (x1 + w1)
                    spacings.append(spacing)
                
                if len(spacings) > 1:
                    mean_spacing = np.mean(spacings)
                    std_spacing = np.std(spacings)
                    
                    # Find unusual spacings
                    for i, spacing in enumerate(spacings):
                        if abs(spacing - mean_spacing) > 2 * std_spacing and std_spacing > 5:
                            x1, y1, w1, h1 = chars[i]
                            x2, y2, w2, h2 = chars[i + 1]
                            spacing_inconsistencies.append((x1, y1, x2 + w2 - x1, max(h1, h2)))
        
        # Flag if too many spacing inconsistencies
        if len(spacing_inconsistencies) > 3:
            result["is_inconsistent"] = True
            result["flags"].append("font_spacing_inconsistencies")
            result["confidence"] = min(0.7, 0.3 + len(spacing_inconsistencies) * 0.05)
            
            for x, y, w, h in spacing_inconsistencies:
                result["inconsistent_areas"].append({
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h),
                    "type": "unusual_font_spacing"
                })
    
    except Exception as e:
        logger.error(f"Error in font spacing analysis: {str(e)}")
        result["flags"].append("font_spacing_analysis_error")
    
    return result


def detect_block_matching_forgery(image: np.ndarray) -> Dict[str, Any]:
    """Detect copy-move forgery using optimized block matching."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # Optimize for performance - use larger blocks and skip more
        block_size = 32  # Larger blocks for faster processing
        step_size = block_size  # Skip more to reduce comparisons
        threshold = 0.9  # Slightly lower threshold
        max_blocks = 100  # Limit number of blocks to analyze
        
        # Extract blocks with reduced sampling
        blocks = []
        count = 0
        for y in range(0, height - block_size, step_size):
            for x in range(0, width - block_size, step_size):
                if count >= max_blocks:
                    break
                block = gray[y:y+block_size, x:x+block_size]
                # Use simpler features for faster comparison
                mean_val = np.mean(block)
                std_val = np.std(block)
                blocks.append((x, y, mean_val, std_val))
                count += 1
            if count >= max_blocks:
                break
        
        # Find similar blocks using feature comparison first
        similar_pairs = []
        for i in range(len(blocks)):
            for j in range(i + 1, min(len(blocks), i + 20)):  # Limit comparisons
                x1, y1, mean1, std1 = blocks[i]
                x2, y2, mean2, std2 = blocks[j]
                
                # Skip if blocks are too close
                distance = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                if distance < block_size * 2:
                    continue
                
                # Quick feature similarity check
                mean_diff = abs(mean1 - mean2)
                std_diff = abs(std1 - std2)
                
                if mean_diff < 10 and std_diff < 5:  # Similar features
                    # Only do expensive correlation for promising candidates
                    block1 = gray[y1:y1+block_size, x1:x1+block_size]
                    block2 = gray[y2:y2+block_size, x2:x2+block_size]
                    
                    correlation = cv2.matchTemplate(block1.astype(np.float32), 
                                                  block2.astype(np.float32), 
                                                  cv2.TM_CCOEFF_NORMED)[0, 0]
                    
                    if correlation > threshold:
                        similar_pairs.append(((x1, y1), (x2, y2), correlation))
        
        # Flag if similar blocks found
        if len(similar_pairs) > 2:  # Lower threshold for faster detection
            result["is_tampered"] = True
            result["flags"].append("block_matching_forgery_detected")
            result["confidence"] = min(0.8, 0.4 + len(similar_pairs) * 0.1)
            
            # Add first few tampered areas only
            for (x1, y1), (x2, y2), correlation in similar_pairs[:3]:
                result["tampered_areas"].extend([
                    {
                        "x": int(x1),
                        "y": int(y1),
                        "width": block_size,
                        "height": block_size,
                        "type": "copy_move_source",
                        "correlation": float(correlation)
                    },
                    {
                        "x": int(x2),
                        "y": int(y2),
                        "width": block_size,
                        "height": block_size,
                        "type": "copy_move_target",
                        "correlation": float(correlation)
                    }
                ])
    
    except Exception as e:
        logger.error(f"Error in block matching detection: {str(e)}")
        result["flags"].append("block_matching_analysis_error")
    
    return result


def detect_image_splicing(image: np.ndarray) -> Dict[str, Any]:
    """Detect image splicing using edge and color analysis."""
    result = {
        "is_tampered": False,
        "confidence": 0.0,
        "flags": [],
        "tampered_areas": []
    }
    
    try:
        # Convert to different color spaces
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        
        # Analyze edge density in different regions
        height, width = gray.shape
        region_size = 64
        
        edge_densities = []
        color_variances = []
        
        for y in range(0, height - region_size, region_size):
            for x in range(0, width - region_size, region_size):
                # Edge density
                edge_region = edges[y:y+region_size, x:x+region_size]
                edge_density = np.sum(edge_region > 0) / (region_size * region_size)
                edge_densities.append((x, y, edge_density))
                
                # Color variance
                color_region = hsv[y:y+region_size, x:x+region_size]
                color_variance = np.var(color_region)
                color_variances.append((x, y, color_variance))
        
        # Find regions with unusual characteristics
        if edge_densities:
            edge_mean = np.mean([d[2] for d in edge_densities])
            edge_std = np.std([d[2] for d in edge_densities])
            
            color_mean = np.mean([v[2] for v in color_variances])
            color_std = np.std([v[2] for v in color_variances])
            
            suspicious_regions = []
            
            for (x, y, edge_density), (_, _, color_variance) in zip(edge_densities, color_variances):
                edge_anomaly = abs(edge_density - edge_mean) > 2 * edge_std
                color_anomaly = abs(color_variance - color_mean) > 2 * color_std
                
                if edge_anomaly and color_anomaly:
                    suspicious_regions.append((x, y, region_size, region_size))
            
            # Flag if too many suspicious regions
            if len(suspicious_regions) > 3:
                result["is_tampered"] = True
                result["flags"].append("image_splicing_detected")
                result["confidence"] = min(0.7, 0.3 + len(suspicious_regions) * 0.05)
                
                for x, y, w, h in suspicious_regions:
                    result["tampered_areas"].append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h),
                        "type": "splicing_region"
                    })
    
    except Exception as e:
        logger.error(f"Error in splicing detection: {str(e)}")
        result["flags"].append("splicing_analysis_error")
    
    return result