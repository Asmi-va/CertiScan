"""
Enhanced OCR Service for Certificate Text Extraction

This service provides improved text extraction capabilities with:
- Multiple certificate template support
- Confidence scoring and validation
- Regional language support
- Structured data extraction with field mapping
- Advanced preprocessing for better accuracy

Requirements: 1.1, 7.1, 7.2, 7.3
"""

import os
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime
import logging

from app.core.config import settings

# Configure tesseract path if provided in settings
if hasattr(settings, 'TESSERACT_CMD') and settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Set up logging
logger = logging.getLogger(__name__)

class CertificateType(Enum):
    """Supported certificate types with different templates."""
    DEGREE = "degree"
    DIPLOMA = "diploma"
    PROFESSIONAL = "professional"
    COURSE_COMPLETION = "course_completion"
    ACHIEVEMENT = "achievement"
    GENERIC = "generic"

class LanguageCode(Enum):
    """Supported languages for OCR."""
    ENGLISH = "eng"
    HINDI = "hin"
    BENGALI = "ben"
    TAMIL = "tam"
    TELUGU = "tel"
    MARATHI = "mar"
    GUJARATI = "guj"
    KANNADA = "kan"
    MALAYALAM = "mal"
    PUNJABI = "pan"

@dataclass
class OCRResult:
    """Structured OCR result with confidence scoring."""
    text: str
    confidence: float
    bounding_boxes: List[Dict[str, Any]]
    language_detected: str
    processing_time: float

@dataclass
class ExtractedField:
    """Individual extracted field with metadata."""
    value: str
    confidence: float
    field_type: str
    bounding_box: Optional[Dict[str, int]] = None
    validation_status: str = "pending"

@dataclass
class CertificateData:
    """Complete certificate data extraction result."""
    certificate_id: Optional[ExtractedField] = None
    student_name: Optional[ExtractedField] = None
    roll_number: Optional[ExtractedField] = None
    course_name: Optional[ExtractedField] = None
    institution_name: Optional[ExtractedField] = None
    marks_grade: Optional[ExtractedField] = None
    issue_date: Optional[ExtractedField] = None
    completion_date: Optional[ExtractedField] = None
    certificate_type: Optional[CertificateType] = None
    overall_confidence: float = 0.0
    raw_text: str = ""
    processing_metadata: Dict[str, Any] = field(default_factory=dict)

class EnhancedOCRService:
    """Enhanced OCR service with improved text extraction capabilities."""
    
    def __init__(self):
        self.supported_languages = [lang.value for lang in LanguageCode]
        self.certificate_templates = self._load_certificate_templates()
        self.field_patterns = self._initialize_field_patterns()
    
    def _load_certificate_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load certificate templates for different types."""
        return {
            CertificateType.DEGREE.value: {
                "keywords": ["degree", "bachelor", "master", "doctorate", "university"],
                "required_fields": ["student_name", "course_name", "institution_name", "issue_date"],
                "field_positions": {
                    "student_name": {"region": "upper_center", "priority": 1},
                    "course_name": {"region": "center", "priority": 2},
                    "institution_name": {"region": "lower_center", "priority": 3}
                }
            },
            CertificateType.DIPLOMA.value: {
                "keywords": ["diploma", "certificate", "completion"],
                "required_fields": ["student_name", "course_name", "completion_date"],
                "field_positions": {
                    "student_name": {"region": "upper_center", "priority": 1},
                    "course_name": {"region": "center", "priority": 2}
                }
            },
            CertificateType.PROFESSIONAL.value: {
                "keywords": ["professional", "certification", "qualified", "license"],
                "required_fields": ["student_name", "certificate_id", "issue_date"],
                "field_positions": {
                    "certificate_id": {"region": "upper_right", "priority": 1},
                    "student_name": {"region": "center", "priority": 2}
                }
            },
            CertificateType.COURSE_COMPLETION.value: {
                "keywords": ["course", "training", "workshop", "completion"],
                "required_fields": ["student_name", "course_name", "completion_date"],
                "field_positions": {
                    "student_name": {"region": "center", "priority": 1},
                    "course_name": {"region": "upper_center", "priority": 2}
                }
            }
        }
    
    def _initialize_field_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for different certificate fields."""
        return {
            "certificate_id": [
                r'(?:CERTIFICATE|CERT)[\s\#]?(?:ID|NO|NUMBER)[\s\#]?[\:\-\s]?([A-Z0-9\-\/]+)',
                r'(?:REG|REGISTRATION)[\s\#]?(?:ID|NO|NUMBER)[\s\#]?[\:\-\s]?([A-Z0-9\-\/]+)',
                r'(?:SERIAL|SL)[\s\#]?(?:NO|NUMBER)[\s\#]?[\:\-\s]?([A-Z0-9\-\/]+)',
                r'ID[\s\#]?[\:\-\s]?([A-Z0-9\-\/]{4,})',
            ],
            "student_name": [
                r'(?:NAME|STUDENT)[\s\#]?(?:OF)?[\s\#]?[\:\-\s]?([A-Za-z\s\.]{3,50})',
                r'(?:THIS IS TO CERTIFY THAT|AWARDED TO|PRESENTED TO)[\s\:]?([A-Za-z\s\.]{3,50})',
                r'(?:MR|MS|MISS|DR)[\.\s]?([A-Za-z\s\.]{3,50})',
                r'(?:श्री|श्रीमती|कुमारी)[\s]?([A-Za-z\s\.]{3,50})',  # Hindi honorifics
            ],
            "roll_number": [
                r'(?:ROLL|REG|REGISTRATION|ENROLLMENT)[\s\#]?(?:NO|NUM|NUMBER)[\s\#]?[\:\-\s]?([A-Z0-9\-\/]+)',
                r'(?:STUDENT|ADMISSION)[\s\#]?(?:ID|NO|NUMBER)[\s\#]?[\:\-\s]?([A-Z0-9\-\/]+)',
                r'(?:रोल|पंजीकरण)[\s\#]?(?:संख्या|नंबर)[\s\#]?[\:\-\s]?([A-Z0-9\-\/]+)',  # Hindi
            ],
            "course_name": [
                r'(?:COURSE|DEGREE|PROGRAM|DIPLOMA)[\s\#]?(?:IN|OF)?[\s\#]?[\:\-\s]?([A-Za-z\s\.\(\)&]{5,100})',
                r'(?:BACHELOR|MASTER|DOCTORATE)[\s]?(?:OF)?[\s]?([A-Za-z\s\.\(\)&]{5,100})',
                r'(?:B\.?TECH|M\.?TECH|B\.?SC|M\.?SC|B\.?COM|M\.?COM|B\.?A|M\.?A|MBA|MCA)[\s]?(?:IN)?[\s]?([A-Za-z\s\.\(\)&]*)',
                r'(?:पाठ्यक्रम|डिग्री)[\s\#]?[\:\-\s]?([A-Za-z\s\.\(\)&]{5,100})',  # Hindi
            ],
            "institution_name": [
                r'(?:UNIVERSITY|COLLEGE|INSTITUTE|SCHOOL)[\s]?(?:OF)?[\s]?([A-Za-z\s\.\(\)&]{5,100})',
                r'(?:विश्वविद्यालय|महाविद्यालय|संस्थान)[\s]?([A-Za-z\s\.\(\)&]{5,100})',  # Hindi
                r'([A-Za-z\s\.\(\)&]{5,100})[\s]?(?:UNIVERSITY|COLLEGE|INSTITUTE)',
            ],
            "marks_grade": [
                r'(?:MARKS|GRADE|CGPA|GPA|PERCENTAGE|SCORE)[\s\#]?[\:\-\s]?([A-Za-z0-9\s\.\%\+\-]{1,20})',
                r'(?:SECURED|OBTAINED|ACHIEVED)[\s]?([A-Za-z0-9\s\.\%\+\-]{1,20})',
                r'(?:WITH|SCORING)[\s]?([A-Za-z0-9\s\.\%\+\-]{1,20})[\s]?(?:MARKS|GRADE|CGPA|GPA|PERCENTAGE)',
                r'(?:अंक|ग्रेड)[\s\#]?[\:\-\s]?([A-Za-z0-9\s\.\%\+\-]{1,20})',  # Hindi
            ],
            "issue_date": [
                r'(?:ISSUED|DATE|DATED)[\s\#]?(?:ON|OF)?[\s\#]?[\:\-\s]?([0-9]{1,2}[\-\/\s][A-Za-z]{3,9}[\-\/\s][0-9]{2,4})',
                r'(?:ISSUED|DATE|DATED)[\s\#]?(?:ON|OF)?[\s\#]?[\:\-\s]?([0-9]{1,2}[\-\/\s][0-9]{1,2}[\-\/\s][0-9]{2,4})',
                r'([0-9]{1,2}[\-\/\s][A-Za-z]{3,9}[\-\/\s][0-9]{2,4})',
                r'([0-9]{4}[\-\/][0-9]{1,2}[\-\/][0-9]{1,2})',
                r'(?:दिनांक|तारीख)[\s\#]?[\:\-\s]?([0-9]{1,2}[\-\/\s][A-Za-z]{3,9}[\-\/\s][0-9]{2,4})',  # Hindi
            ],
            "completion_date": [
                r'(?:COMPLETED|COMPLETION|FINISHED)[\s\#]?(?:ON|DATE)?[\s\#]?[\:\-\s]?([0-9]{1,2}[\-\/\s][A-Za-z]{3,9}[\-\/\s][0-9]{2,4})',
                r'(?:COMPLETED|COMPLETION|FINISHED)[\s\#]?(?:ON|DATE)?[\s\#]?[\:\-\s]?([0-9]{1,2}[\-\/\s][0-9]{1,2}[\-\/\s][0-9]{2,4})',
                r'(?:पूर्ण|समाप्त)[\s\#]?(?:दिनांक)?[\s\#]?[\:\-\s]?([0-9]{1,2}[\-\/\s][A-Za-z]{3,9}[\-\/\s][0-9]{2,4})',  # Hindi
            ]
        }

    async def extract_text_with_confidence(self, image_path: str, languages: List[str] = None) -> OCRResult:
        """
        Extract text from image with confidence scoring and language detection.
        
        Args:
            image_path: Path to the certificate image
            languages: List of language codes to use for OCR
            
        Returns:
            OCRResult with text, confidence, and metadata
        """
        start_time = datetime.now()
        
        try:
            # Prepare languages for tesseract
            if languages is None:
                languages = [LanguageCode.ENGLISH.value]
            
            lang_string = '+'.join(languages)
            
            # Load and preprocess image
            processed_image = self._preprocess_image_for_ocr(image_path)
            
            # Perform OCR with detailed output
            ocr_data = pytesseract.image_to_data(
                processed_image, 
                lang=lang_string,
                output_type=pytesseract.Output.DICT,
                config='--psm 6'  # Uniform block of text
            )
            
            # Extract text and confidence
            text_parts = []
            confidences = []
            bounding_boxes = []
            
            for i in range(len(ocr_data['text'])):
                if int(ocr_data['conf'][i]) > 0:  # Filter out low confidence
                    word = ocr_data['text'][i].strip()
                    if word:
                        text_parts.append(word)
                        confidences.append(int(ocr_data['conf'][i]))
                        bounding_boxes.append({
                            'x': ocr_data['left'][i],
                            'y': ocr_data['top'][i],
                            'width': ocr_data['width'][i],
                            'height': ocr_data['height'][i],
                            'text': word,
                            'confidence': int(ocr_data['conf'][i])
                        })
            
            # Calculate overall confidence
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Combine text
            full_text = ' '.join(text_parts)
            
            # Detect primary language
            detected_language = self._detect_primary_language(full_text, languages)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return OCRResult(
                text=full_text,
                confidence=overall_confidence,
                bounding_boxes=bounding_boxes,
                language_detected=detected_language,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {str(e)}")
            raise Exception(f"OCR extraction failed: {str(e)}")
    
    def _preprocess_image_for_ocr(self, image_path: str) -> Image.Image:
        """Advanced image preprocessing for better OCR accuracy."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply multiple preprocessing techniques
        
        # 1. Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # 2. Contrast enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # 3. Adaptive thresholding for better text separation
        thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 4. Morphological operations to clean up text
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # 5. Deskewing if needed
        deskewed = self._deskew_image(cleaned)
        
        # Convert back to PIL Image
        return Image.fromarray(deskewed)
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct image skew."""
        # Find all white pixels
        coords = np.column_stack(np.where(image > 0))
        
        # Find minimum area rectangle
        if len(coords) > 0:
            rect = cv2.minAreaRect(coords)
            angle = rect[2]
            
            # Correct angle
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            # Only deskew if angle is significant
            if abs(angle) > 0.5:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated
        
        return image
    
    def _detect_primary_language(self, text: str, available_languages: List[str]) -> str:
        """Detect the primary language of the extracted text."""
        # Simple language detection based on character patterns
        hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if hindi_chars > english_chars and LanguageCode.HINDI.value in available_languages:
            return LanguageCode.HINDI.value
        
        return LanguageCode.ENGLISH.value
    
    async def extract_certificate_data(self, image_path: str, certificate_type: CertificateType = None) -> CertificateData:
        """
        Extract structured certificate data with field mapping and validation.
        
        Args:
            image_path: Path to the certificate image
            certificate_type: Type of certificate for template matching
            
        Returns:
            CertificateData with extracted fields and confidence scores
        """
        try:
            # Perform OCR extraction
            ocr_result = await self.extract_text_with_confidence(image_path)
            
            # Detect certificate type if not provided
            if certificate_type is None:
                certificate_type = self._detect_certificate_type(ocr_result.text)
            
            # Extract structured fields
            certificate_data = CertificateData(
                raw_text=ocr_result.text,
                certificate_type=certificate_type,
                processing_metadata={
                    'ocr_confidence': ocr_result.confidence,
                    'language_detected': ocr_result.language_detected,
                    'processing_time': ocr_result.processing_time,
                    'bounding_boxes_count': len(ocr_result.bounding_boxes)
                }
            )
            
            # Extract each field type
            field_confidences = []
            
            for field_name in self.field_patterns.keys():
                extracted_field = self._extract_field(
                    field_name, ocr_result.text, ocr_result.bounding_boxes
                )
                if extracted_field:
                    setattr(certificate_data, field_name, extracted_field)
                    field_confidences.append(extracted_field.confidence)
            
            # Calculate overall confidence
            certificate_data.overall_confidence = (
                sum(field_confidences) / len(field_confidences) if field_confidences else 0
            )
            
            # Validate extracted data
            certificate_data = self._validate_extracted_data(certificate_data, certificate_type)
            
            return certificate_data
            
        except Exception as e:
            logger.error(f"Certificate data extraction failed for {image_path}: {str(e)}")
            raise Exception(f"Certificate data extraction failed: {str(e)}")
    
    def _detect_certificate_type(self, text: str) -> CertificateType:
        """Detect certificate type based on text content."""
        text_lower = text.lower()
        
        # Check for keywords in each certificate type
        type_scores = {}
        
        for cert_type, template in self.certificate_templates.items():
            score = 0
            for keyword in template['keywords']:
                if keyword in text_lower:
                    score += 1
            type_scores[cert_type] = score
        
        # Return type with highest score, default to generic
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return CertificateType(best_type)
        
        return CertificateType.GENERIC
    
    def _extract_field(self, field_name: str, text: str, bounding_boxes: List[Dict]) -> Optional[ExtractedField]:
        """Extract a specific field from text using patterns."""
        patterns = self.field_patterns.get(field_name, [])
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                value = match.group(1).strip() if match.groups() else match.group(0).strip()
                
                # Clean up the extracted value
                cleaned_value = self._clean_extracted_value(value, field_name)
                
                if cleaned_value and len(cleaned_value) > 1:
                    # Calculate confidence based on pattern match and value quality
                    confidence = self._calculate_field_confidence(cleaned_value, field_name, match)
                    
                    # Find bounding box for this text
                    bounding_box = self._find_text_bounding_box(cleaned_value, bounding_boxes)
                    
                    return ExtractedField(
                        value=cleaned_value,
                        confidence=confidence,
                        field_type=field_name,
                        bounding_box=bounding_box,
                        validation_status="extracted"
                    )
        
        return None
    
    def _clean_extracted_value(self, value: str, field_type: str) -> str:
        """Clean and normalize extracted field values."""
        # Remove extra whitespace
        cleaned = ' '.join(value.split())
        
        # Field-specific cleaning
        if field_type == "student_name":
            # Remove common prefixes and suffixes
            cleaned = re.sub(r'^(MR\.?|MS\.?|MISS\.?|DR\.?|श्री|श्रीमती|कुमारी)\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s*(JR\.?|SR\.?|III|IV)$', '', cleaned, flags=re.IGNORECASE)
            
        elif field_type == "certificate_id":
            # Remove common prefixes
            cleaned = re.sub(r'^(CERTIFICATE|CERT|ID|NO|NUMBER)[\s\:\-]*', '', cleaned, flags=re.IGNORECASE)
            
        elif field_type == "course_name":
            # Standardize degree abbreviations
            degree_mappings = {
                r'\bB\.?TECH\b': 'B.Tech',
                r'\bM\.?TECH\b': 'M.Tech',
                r'\bB\.?SC\b': 'B.Sc',
                r'\bM\.?SC\b': 'M.Sc',
                r'\bB\.?COM\b': 'B.Com',
                r'\bM\.?COM\b': 'M.Com',
                r'\bB\.?A\b': 'B.A',
                r'\bM\.?A\b': 'M.A'
            }
            
            for pattern, replacement in degree_mappings.items():
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _calculate_field_confidence(self, value: str, field_type: str, match: re.Match) -> float:
        """Calculate confidence score for extracted field."""
        base_confidence = 70.0  # Base confidence for pattern match
        
        # Adjust based on field type and value characteristics
        if field_type == "student_name":
            # Names should have reasonable length and proper case
            if 3 <= len(value) <= 50 and any(c.isupper() for c in value):
                base_confidence += 20
            
        elif field_type == "certificate_id":
            # IDs should have alphanumeric characters
            if re.match(r'^[A-Z0-9\-\/]{4,20}$', value):
                base_confidence += 25
                
        elif field_type == "marks_grade":
            # Grades should be reasonable values
            if re.match(r'^\d+(\.\d+)?%?$', value) or value.upper() in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'PASS', 'FAIL']:
                base_confidence += 20
        
        # Adjust based on match position (earlier matches often more reliable)
        position_factor = max(0, 100 - match.start() / 10)
        base_confidence += min(position_factor, 10)
        
        return min(base_confidence, 100.0)
    
    def _find_text_bounding_box(self, text: str, bounding_boxes: List[Dict]) -> Optional[Dict[str, int]]:
        """Find bounding box coordinates for extracted text."""
        text_words = text.lower().split()
        
        for box in bounding_boxes:
            box_text = box.get('text', '').lower()
            if any(word in box_text for word in text_words):
                return {
                    'x': box['x'],
                    'y': box['y'],
                    'width': box['width'],
                    'height': box['height']
                }
        
        return None
    
    def _validate_extracted_data(self, certificate_data: CertificateData, certificate_type: CertificateType) -> CertificateData:
        """Validate extracted certificate data against template requirements."""
        template = self.certificate_templates.get(certificate_type.value, {})
        required_fields = template.get('required_fields', [])
        
        # Check if required fields are present
        for field_name in required_fields:
            field_value = getattr(certificate_data, field_name, None)
            if field_value:
                field_value.validation_status = "validated"
            else:
                logger.warning(f"Required field '{field_name}' missing for {certificate_type.value} certificate")
        
        # Additional validation rules
        if certificate_data.student_name:
            if len(certificate_data.student_name.value) < 2:
                certificate_data.student_name.validation_status = "invalid"
                certificate_data.student_name.confidence *= 0.5
        
        if certificate_data.certificate_id:
            if len(certificate_data.certificate_id.value) < 3:
                certificate_data.certificate_id.validation_status = "invalid"
                certificate_data.certificate_id.confidence *= 0.5
        
        return certificate_data

# Create global service instance
enhanced_ocr_service = EnhancedOCRService()

# Legacy function for backward compatibility
async def extract_text_from_image(image_path: str) -> Dict[str, Any]:
    """Legacy function for backward compatibility."""
    try:
        # Use enhanced service for extraction
        certificate_data = await enhanced_ocr_service.extract_certificate_data(image_path)
        
        # Convert to legacy format
        result = {
            "cert_id": certificate_data.certificate_id.value if certificate_data.certificate_id else None,
            "name": certificate_data.student_name.value if certificate_data.student_name else None,
            "roll_no": certificate_data.roll_number.value if certificate_data.roll_number else None,
            "course": certificate_data.course_name.value if certificate_data.course_name else None,
            "marks": certificate_data.marks_grade.value if certificate_data.marks_grade else None,
            "issue_date": certificate_data.issue_date.value if certificate_data.issue_date else None,
            "raw_text": certificate_data.raw_text,
            "image_path": image_path,
            "confidence": certificate_data.overall_confidence,
            "certificate_type": certificate_data.certificate_type.value if certificate_data.certificate_type else "generic"
        }
        
        return result
        
    except Exception as e:
        raise Exception(f"OCR extraction failed: {str(e)}")

def extract_certificate_fields(text: str) -> Dict[str, Any]:
    """Legacy function for extracting certificate fields from text."""
    # Use enhanced service patterns for extraction
    service = enhanced_ocr_service
    
    result = {
        "cert_id": None,
        "name": None,
        "roll_no": None,
        "course": None,
        "marks": None,
        "issue_date": None,
        "raw_text": text,
    }
    
    # Extract using enhanced patterns
    for field_name, legacy_key in [
        ("certificate_id", "cert_id"),
        ("student_name", "name"),
        ("roll_number", "roll_no"),
        ("course_name", "course"),
        ("marks_grade", "marks"),
        ("issue_date", "issue_date")
    ]:
        patterns = service.field_patterns.get(field_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip() if match.groups() else match.group(0).strip()
                cleaned_value = service._clean_extracted_value(value, field_name)
                if cleaned_value:
                    result[legacy_key] = cleaned_value
                    break
    
    return result

async def extract_text_from_regions(image_path: str, regions: List[Dict[str, Any]]) -> Dict[str, str]:
    """Extract text from specific regions of an image with enhanced preprocessing."""
    try:
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")
        
        result = {}
        service = enhanced_ocr_service
        
        for region in regions:
            name = region.get("name", "unknown")
            x, y, w, h = region.get("x", 0), region.get("y", 0), region.get("width", 100), region.get("height", 100)
            
            # Extract region
            roi = image[y:y+h, x:x+w]
            
            # Convert to grayscale
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Apply enhanced preprocessing
            denoised = cv2.fastNlMeansDenoising(gray)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            thresh = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
            
            # Perform OCR on region with confidence
            try:
                ocr_data = pytesseract.image_to_data(
                    thresh, 
                    output_type=pytesseract.Output.DICT,
                    config='--psm 8'  # Single word
                )
                
                # Extract text with confidence filtering
                text_parts = []
                for i in range(len(ocr_data['text'])):
                    if int(ocr_data['conf'][i]) > 30:  # Filter low confidence
                        word = ocr_data['text'][i].strip()
                        if word:
                            text_parts.append(word)
                
                result[name] = ' '.join(text_parts)
                
            except Exception as e:
                logger.warning(f"OCR failed for region {name}: {str(e)}")
                result[name] = ""
        
        return result
        
    except Exception as e:
        raise Exception(f"Region OCR extraction failed: {str(e)}")

# Additional utility functions for enhanced OCR service

async def extract_text_with_multiple_languages(image_path: str, languages: List[str] = None) -> Dict[str, Any]:
    """
    Extract text using multiple languages and return the best result.
    
    Args:
        image_path: Path to the certificate image
        languages: List of language codes to try
        
    Returns:
        Dict with extraction results and language detection info
    """
    if languages is None:
        languages = [LanguageCode.ENGLISH.value, LanguageCode.HINDI.value]
    
    best_result = None
    best_confidence = 0
    
    for lang in languages:
        try:
            ocr_result = await enhanced_ocr_service.extract_text_with_confidence(
                image_path, [lang]
            )
            
            if ocr_result.confidence > best_confidence:
                best_confidence = ocr_result.confidence
                best_result = {
                    "text": ocr_result.text,
                    "confidence": ocr_result.confidence,
                    "language": ocr_result.language_detected,
                    "processing_time": ocr_result.processing_time,
                    "bounding_boxes": ocr_result.bounding_boxes
                }
                
        except Exception as e:
            logger.warning(f"OCR failed for language {lang}: {str(e)}")
            continue
    
    if best_result is None:
        raise Exception("OCR failed for all specified languages")
    
    return best_result

async def validate_certificate_data_quality(certificate_data: CertificateData) -> Dict[str, Any]:
    """
    Validate the quality and completeness of extracted certificate data.
    
    Args:
        certificate_data: Extracted certificate data
        
    Returns:
        Dict with validation results and quality metrics
    """
    validation_result = {
        "overall_quality": "good",
        "completeness_score": 0.0,
        "confidence_score": certificate_data.overall_confidence,
        "field_analysis": {},
        "recommendations": []
    }
    
    # Analyze each field
    total_fields = 0
    completed_fields = 0
    
    for field_name in ["certificate_id", "student_name", "roll_number", "course_name", 
                       "institution_name", "marks_grade", "issue_date"]:
        field_value = getattr(certificate_data, field_name, None)
        total_fields += 1
        
        if field_value and field_value.value:
            completed_fields += 1
            validation_result["field_analysis"][field_name] = {
                "status": "extracted",
                "confidence": field_value.confidence,
                "validation_status": field_value.validation_status
            }
            
            # Field-specific quality checks
            if field_name == "student_name" and len(field_value.value) < 3:
                validation_result["recommendations"].append(
                    f"Student name '{field_value.value}' seems too short"
                )
            elif field_name == "certificate_id" and len(field_value.value) < 4:
                validation_result["recommendations"].append(
                    f"Certificate ID '{field_value.value}' seems too short"
                )
        else:
            validation_result["field_analysis"][field_name] = {
                "status": "missing",
                "confidence": 0,
                "validation_status": "missing"
            }
    
    # Calculate completeness score
    validation_result["completeness_score"] = (completed_fields / total_fields) * 100
    
    # Determine overall quality
    if validation_result["completeness_score"] >= 80 and validation_result["confidence_score"] >= 70:
        validation_result["overall_quality"] = "excellent"
    elif validation_result["completeness_score"] >= 60 and validation_result["confidence_score"] >= 50:
        validation_result["overall_quality"] = "good"
    elif validation_result["completeness_score"] >= 40 and validation_result["confidence_score"] >= 30:
        validation_result["overall_quality"] = "fair"
    else:
        validation_result["overall_quality"] = "poor"
        validation_result["recommendations"].append(
            "Consider re-scanning the certificate with better image quality"
        )
    
    return validation_result

# Export enhanced service for use in other modules
__all__ = [
    'enhanced_ocr_service',
    'extract_text_from_image',
    'extract_certificate_fields', 
    'extract_text_from_regions',
    'extract_text_with_multiple_languages',
    'validate_certificate_data_quality',
    'CertificateType',
    'LanguageCode',
    'OCRResult',
    'ExtractedField',
    'CertificateData'
]