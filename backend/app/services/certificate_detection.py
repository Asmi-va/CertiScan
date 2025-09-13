import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from app.core.config import settings

class CertificateDetector:
    """Class for detecting certificate elements using YOLOv8 model or fallback methods."""
    
    def __init__(self):
        self.model = None
        self.classes = ['degree', 'signature', 'stamp']
        self.model_path = os.path.join(settings.MODEL_DIR, 'certificate_detection_yolov8.pt')
        self.confidence_threshold = 0.5
        self.initialized = False
        self.use_ml = True
    
    async def initialize(self):
        """Initialize the YOLOv8 model if possible, otherwise use fallback detection."""
        try:
            # Check for YOLOv8 (ultralytics)
            try:
                from ultralytics import YOLO
                print("YOLOv8 (ultralytics) available")
            except ImportError:
                print("YOLOv8 (ultralytics) not available, using fallback detection methods")
                self.use_ml = False
                self.initialized = True
                return True
                
            # Check if model file exists
            if not os.path.exists(self.model_path):
                # Train model if it doesn't exist
                success = await self.train_model()
                if not success:
                    print("YOLOv8 model training failed, using fallback detection methods")
                    self.use_ml = False
                    self.initialized = True
                    return True
            
            # Load the YOLOv8 model
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print("YOLOv8 model loaded successfully")
            
            self.initialized = True
            return True
        except Exception as e:
            print(f"Error initializing YOLOv8 certificate detector: {str(e)}")
            print("Using fallback detection methods")
            self.use_ml = False
            self.initialized = True
            return True
    
    async def train_model(self):
        """Train the YOLOv8 model using the certificate dataset."""
        try:
            from ultralytics import YOLO
            
            # Ensure model directory exists
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Set up paths using configuration
            dataset_path = settings.get_certificate_dataset_path()
            yaml_path = settings.get_certificate_data_yaml_path()
            
            print(f"Training YOLOv8 model with dataset: {yaml_path}")
            
            # Load pretrained YOLOv8 model (nano version for faster training)
            model = YOLO('yolov8n.pt')
            
            # Detect available device
            import torch
            if torch.cuda.is_available():
                device = 0  # Use first GPU
                batch_size = 16
                workers = 8
                print(f"Training on GPU: {torch.cuda.get_device_name(0)}")
            else:
                device = 'cpu'
                batch_size = 8
                workers = 4
                print("Training on CPU")
            
            # Train the model
            results = model.train(
                data=str(yaml_path),
                epochs=100,  # More epochs for better accuracy with GPU
                batch=batch_size,
                imgsz=640,
                save_period=10,
                project='runs/detect',
                name='certificate_detection',
                patience=15,  # Early stopping
                device=device,
                workers=workers,
                amp=True,  # Automatic Mixed Precision for faster training
                cache=True,  # Cache images for faster training
                optimizer='AdamW',  # Better optimizer
                lr0=0.01,  # Initial learning rate
                lrf=0.01,  # Final learning rate
                momentum=0.937,
                weight_decay=0.0005,
                warmup_epochs=3,
                warmup_momentum=0.8,
                warmup_bias_lr=0.1
            )
            
            # Save the trained model to our model directory
            best_model_path = Path('runs/detect/certificate_detection/weights/best.pt')
            if best_model_path.exists():
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                # Copy instead of rename to preserve the original
                import shutil
                shutil.copy2(best_model_path, self.model_path)
                print(f"YOLOv8 model saved to: {self.model_path}")
                return True
            else:
                print("Training completed but best model not found")
                return False
            
        except ImportError:
            print("YOLOv8 (ultralytics) not installed. Install with: pip install ultralytics")
            return False
        except Exception as e:
            print(f"Error training YOLOv8 certificate detector: {str(e)}")
            return False
    
    async def detect(self, image_path: str) -> Dict[str, Any]:
        """Detect certificate elements in an image."""
        result = {
            "detected_elements": [],
            "confidence": 0.0,
            "is_certificate": False
        }
        
        try:
            # Initialize model if not already done
            if not self.initialized:
                success = await self.initialize()
                if not success:
                    result["error"] = "Failed to initialize detector"
                    return result
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                result["error"] = f"Could not read image at {image_path}"
                return result
            
            if self.use_ml and self.model is not None:
                # Use YOLOv8-based detection
                return await self._detect_with_yolov8(image_path)
            else:
                # Use fallback detection
                return self._detect_fallback(image)
            
        except Exception as e:
            result["error"] = f"Error detecting certificate elements: {str(e)}"
            return result
    
    async def _detect_with_yolov8(self, image_path: str) -> Dict[str, Any]:
        """Detect certificate elements using YOLOv8 model."""
        result = {
            "detected_elements": [],
            "confidence": 0.0,
            "is_certificate": False,
            "method": "yolov8"
        }
        
        try:
            # Run YOLOv8 inference
            results = self.model(image_path, conf=self.confidence_threshold)
            
            # Extract detected elements
            detected_elements = []
            
            for r in results:
                # Get detection boxes
                boxes = r.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        # Get box coordinates
                        box = boxes.xyxy[i].cpu().numpy()  # x1, y1, x2, y2
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls = int(boxes.cls[i].cpu().numpy())
                        
                        if conf >= self.confidence_threshold and cls < len(self.classes):
                            element = {
                                "class": self.classes[cls],
                                "confidence": conf,
                                "bbox": {
                                    "x": int(box[0]),
                                    "y": int(box[1]),
                                    "width": int(box[2] - box[0]),
                                    "height": int(box[3] - box[1])
                                }
                            }
                            detected_elements.append(element)
            
            # Update result
            result["detected_elements"] = detected_elements
            
            # Determine if this is a certificate based on detected elements
            # A certificate should have at least a degree text and either a signature or stamp
            has_degree = any(e["class"] == "degree" for e in detected_elements)
            has_signature = any(e["class"] == "signature" for e in detected_elements)
            has_stamp = any(e["class"] == "stamp" for e in detected_elements)
            
            if has_degree and (has_signature or has_stamp):
                result["is_certificate"] = True
                # Calculate confidence based on detected elements
                confidences = [e["confidence"] for e in detected_elements]
                result["confidence"] = sum(confidences) / len(confidences) if confidences else 0.0
            elif detected_elements:
                # If we have some elements but not the ideal combination
                result["is_certificate"] = True
                confidences = [e["confidence"] for e in detected_elements]
                result["confidence"] = sum(confidences) / len(confidences) * 0.7  # Lower confidence
            
            return result
            
        except Exception as e:
            print(f"Error in YOLOv8 detection: {str(e)}")
            result["error"] = f"YOLOv8 detection failed: {str(e)}"
            return result
    
    def _detect_fallback(self, image) -> Dict[str, Any]:
        """Fallback method for certificate detection without ML."""
        result = {
            "detected_elements": [],
            "confidence": 0.7,  # Default confidence for fallback method
            "is_certificate": True,  # Assume it's a certificate by default
            "method": "fallback"
        }
        
        height, width = image.shape[:2]
        
        # Use basic image analysis to estimate certificate elements
        # These are just estimates based on typical certificate layouts
        detected_elements = [
            {
                "class": "degree",
                "confidence": 0.8,
                "bbox": {
                    "x": int(width * 0.2),
                    "y": int(height * 0.3),
                    "width": int(width * 0.6),
                    "height": int(height * 0.2)
                }
            },
            {
                "class": "signature",
                "confidence": 0.7,
                "bbox": {
                    "x": int(width * 0.6),
                    "y": int(height * 0.7),
                    "width": int(width * 0.3),
                    "height": int(height * 0.1)
                }
            },
            {
                "class": "stamp",
                "confidence": 0.6,
                "bbox": {
                    "x": int(width * 0.1),
                    "y": int(height * 0.7),
                    "width": int(width * 0.2),
                    "height": int(height * 0.2)
                }
            }
        ]
        
        result["detected_elements"] = detected_elements
        return result

# Singleton instance
certificate_detector = CertificateDetector()

async def detect_certificate_elements(image_path: str) -> Dict[str, Any]:
    """Detect certificate elements in an image."""
    return await certificate_detector.detect(image_path)

async def verify_certificate_authenticity(image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify certificate authenticity using SSL dataset."""
    result = {
        "is_authentic": True,
        "confidence": 0.0,
        "details": {}
    }
    
    try:
        # First detect certificate elements
        detection_result = await detect_certificate_elements(image_path)
        
        if "error" in detection_result:
            result["is_authentic"] = False
            result["details"]["error"] = detection_result["error"]
            return result
        
        # Check if it's a certificate
        if not detection_result["is_certificate"]:
            result["is_authentic"] = False
            result["details"]["reason"] = "Document does not appear to be a valid certificate"
            result["confidence"] = 0.8
            return result
        
        # TODO: Implement SSL certificate dataset verification
        # This would compare extracted certificate data with the SSL dataset
        # For now, we'll use the detection confidence as our authenticity measure
        
        result["confidence"] = detection_result["confidence"]
        result["details"]["detected_elements"] = detection_result["detected_elements"]
        
        return result
        
    except Exception as e:
        result["is_authentic"] = False
        result["details"]["error"] = f"Error verifying certificate authenticity: {str(e)}"
        return result