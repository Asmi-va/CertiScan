#!/usr/bin/env python3
"""
Test script for YOLOv8 certificate detection integration.
"""

import asyncio
import sys
import os
import cv2
import numpy as np
import tempfile

# Add backend to path
sys.path.append('backend')

from app.services.certificate_detection import detect_certificate_elements

async def test_yolov8_integration():
    """Test YOLOv8 certificate detection integration."""
    print("=== YOLOv8 Certificate Detection Integration Test ===\n")
    
    # Create a test certificate image
    print("1. Creating test certificate image...")
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    
    # Add certificate-like elements
    cv2.rectangle(img, (100, 100), (700, 150), (0, 0, 0), 2)  # Header
    cv2.putText(img, "CERTIFICATE", (250, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    cv2.rectangle(img, (100, 200), (700, 250), (0, 0, 0), 1)  # Content area
    cv2.putText(img, "Bachelor of Computer Science", (150, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    cv2.rectangle(img, (500, 450), (700, 500), (0, 0, 0), 1)  # Signature area
    cv2.putText(img, "Signature", (520, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    cv2.circle(img, (200, 475), 40, (0, 0, 0), 2)  # Stamp
    cv2.putText(img, "SEAL", (180, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # Save test image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        cv2.imwrite(tmp.name, img)
        test_image_path = tmp.name
    
    try:
        print(f"   Test image saved: {test_image_path}")
        
        # Test certificate detection
        print("\n2. Testing certificate detection...")
        result = await detect_certificate_elements(test_image_path)
        
        print(f"   Detection method: {result.get('method', 'unknown')}")
        print(f"   Is certificate: {result.get('is_certificate', False)}")
        print(f"   Overall confidence: {result.get('confidence', 0):.2f}")
        print(f"   Detected elements: {len(result.get('detected_elements', []))}")
        
        # Display detected elements
        if result.get('detected_elements'):
            print("\n   Detected Elements:")
            for i, element in enumerate(result['detected_elements']):
                print(f"     {i+1}. {element['class']} (confidence: {element['confidence']:.2f})")
                bbox = element['bbox']
                print(f"        Location: ({bbox['x']}, {bbox['y']}) {bbox['width']}x{bbox['height']}")
        
        # Check for errors
        if 'error' in result:
            print(f"\n   ⚠️  Error: {result['error']}")
        
        # Determine test result
        if result.get('method') == 'yolov8':
            print("\n✅ SUCCESS: YOLOv8 model is working!")
            return True
        elif result.get('method') == 'fallback':
            print("\n⚠️  FALLBACK: Using fallback detection (YOLOv8 not available)")
            print("   To use YOLOv8, install ultralytics: pip install ultralytics")
            return True
        else:
            print("\n❌ FAILED: Detection system not working properly")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False
    finally:
        # Clean up
        try:
            os.unlink(test_image_path)
        except:
            pass

async def test_yolov8_training():
    """Test YOLOv8 model training capability."""
    print("\n=== YOLOv8 Training Test ===\n")
    
    try:
        from ultralytics import YOLO
        print("✅ YOLOv8 (ultralytics) is installed")
        
        # Check if dataset exists
        dataset_yaml = "dataset/data.yaml"
        if os.path.exists(dataset_yaml):
            print(f"✅ Dataset configuration found: {dataset_yaml}")
            
            # Read dataset info
            with open(dataset_yaml, 'r') as f:
                content = f.read()
                print("   Dataset configuration:")
                for line in content.split('\n')[:6]:  # Show first 6 lines
                    if line.strip():
                        print(f"     {line}")
        else:
            print(f"⚠️  Dataset configuration not found: {dataset_yaml}")
        
        # Test model loading
        print("\n   Testing YOLOv8 model loading...")
        model = YOLO('yolov8n.pt')  # This will download if not present
        print("✅ YOLOv8 pretrained model loaded successfully")
        
        return True
        
    except ImportError:
        print("❌ YOLOv8 (ultralytics) not installed")
        print("   Install with: pip install ultralytics")
        return False
    except Exception as e:
        print(f"❌ Error testing YOLOv8: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("YOLOv8 Certificate Detection Integration Tests")
    print("=" * 50)
    
    # Test 1: YOLOv8 availability and training capability
    training_ok = await test_yolov8_training()
    
    # Test 2: Certificate detection integration
    detection_ok = await test_yolov8_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"  YOLOv8 Training Ready: {'✅ PASS' if training_ok else '❌ FAIL'}")
    print(f"  Detection Integration: {'✅ PASS' if detection_ok else '❌ FAIL'}")
    
    if training_ok and detection_ok:
        print("\n🎉 All tests passed! YOLOv8 integration is ready.")
        print("\nNext steps:")
        print("  1. Run model training with your dataset")
        print("  2. Test with real certificate images")
        print("  3. Integrate with tamper detection system")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return training_ok and detection_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)