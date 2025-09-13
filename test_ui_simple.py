#!/usr/bin/env python3
"""
Simple UI test for the tamper detection system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append('backend')

from app.services.tamper_detection import detect_tampering

async def interactive_test():
    """Interactive test interface for tamper detection."""
    print("🔍 Certificate Tamper Detection System - Interactive Test")
    print("=" * 60)
    
    while True:
        print("\n📋 Choose a test option:")
        print("1. Test with dataset image")
        print("2. Test with your own image")
        print("3. Test with synthetic tampered image")
        print("4. View system status")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            await test_dataset_image()
        elif choice == "2":
            await test_custom_image()
        elif choice == "3":
            await test_synthetic_tampered()
        elif choice == "4":
            show_system_status()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

async def test_dataset_image():
    """Test with a real dataset image."""
    print("\n🎓 Testing with Dataset Image")
    print("-" * 40)
    
    # Find dataset images
    dataset_dir = Path("dataset/val/images")
    if not dataset_dir.exists():
        print("❌ Dataset directory not found!")
        return
    
    images = list(dataset_dir.glob("*.jpg"))
    if not images:
        print("❌ No images found in dataset!")
        return
    
    # Use first image
    test_image = images[0]
    print(f"📄 Using: {test_image.name}")
    
    # Sample extracted data
    extracted_data = {
        "student_name": "John Doe",
        "roll_number": "12345",
        "course": "Bachelor of Science in Psychology",
        "grades": {
            "Psychology": 85,
            "Statistics": 88,
            "Research Methods": 90,
            "Cognitive Psychology": 87
        },
        "certificate_id": "CERT2024001",
        "institution": "University of Excellence"
    }
    
    await run_tamper_detection(str(test_image), extracted_data)

async def test_custom_image():
    """Test with user-provided image."""
    print("\n📁 Testing with Custom Image")
    print("-" * 40)
    
    image_path = input("Enter the path to your certificate image: ").strip()
    
    if not os.path.exists(image_path):
        print("❌ File not found!")
        return
    
    # Simple extracted data
    extracted_data = {
        "student_name": "Test Student",
        "course": "Test Course",
        "grades": {"Subject1": 85, "Subject2": 90},
        "certificate_id": "TEST123",
        "institution": "Test Institution"
    }
    
    await run_tamper_detection(image_path, extracted_data)

async def test_synthetic_tampered():
    """Test with a synthetically tampered image."""
    print("\n⚠️  Testing with Synthetic Tampered Image")
    print("-" * 40)
    
    # Find a dataset image to tamper
    dataset_dir = Path("dataset/val/images")
    if not dataset_dir.exists():
        print("❌ Dataset directory not found!")
        return
    
    images = list(dataset_dir.glob("*.jpg"))
    if not images:
        print("❌ No images found in dataset!")
        return
    
    import cv2
    import numpy as np
    
    # Load and tamper an image
    original_image = cv2.imread(str(images[0]))
    if original_image is None:
        print("❌ Could not load image!")
        return
    
    print("🔧 Creating synthetic tampering...")
    
    # Create tampered version
    tampered_image = original_image.copy()
    height, width = tampered_image.shape[:2]
    
    # Add noise (simulating grade tampering)
    noise_region = tampered_image[height//3:height//2, width//3:2*width//3]
    noise = np.random.randint(0, 50, noise_region.shape, dtype=np.uint8)
    tampered_image[height//3:height//2, width//3:2*width//3] = cv2.add(noise_region, noise)
    
    # Add suspicious rectangle
    cv2.rectangle(tampered_image, (width//4, height//4), (width//2, height//2), (255, 0, 0), 3)
    
    # Save tampered image
    tampered_path = "temp_tampered_certificate.jpg"
    cv2.imwrite(tampered_path, tampered_image)
    
    print(f"📄 Created tampered image: {tampered_path}")
    
    # Suspicious extracted data
    extracted_data = {
        "student_name": "Jane Smith",
        "course": "Bachelor of Computer Science",
        "grades": {
            "Math": 98,
            "Physics": 99,
            "Chemistry": 97,
            "Programming": 100,
            "Algorithms": 98
        },
        "certificate_id": "FAKE123456",
        "institution": "Fake University"
    }
    
    await run_tamper_detection(tampered_path, extracted_data)
    
    # Clean up
    try:
        os.remove(tampered_path)
        print(f"🗑️  Cleaned up temporary file")
    except:
        pass

async def run_tamper_detection(image_path, extracted_data):
    """Run tamper detection and display results."""
    print(f"\n🔍 Analyzing: {os.path.basename(image_path)}")
    print("⏳ Running AI-powered tamper detection...")
    
    try:
        # Run tamper detection
        result = await detect_tampering(image_path, extracted_data)
        
        # Display results
        display_results(result)
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")

def display_results(result):
    """Display tamper detection results in a nice format."""
    print("\n" + "=" * 60)
    print("🎯 TAMPER DETECTION RESULTS")
    print("=" * 60)
    
    # Main result
    is_tampered = result.get('is_tampered', False)
    confidence = result.get('overall_confidence', 0)
    risk_score = result.get('risk_score', 0)
    
    status = "🚨 TAMPERED DETECTED" if is_tampered else "✅ CERTIFICATE CLEAN"
    print(f"\n{status}")
    print(f"Overall Confidence: {confidence:.1%}")
    print(f"Risk Score: {risk_score:.1%}")
    
    # Detection methods
    methods = result.get('detection_methods', [])
    if methods:
        print(f"\n🔍 Detection Methods Used ({len(methods)}):")
        for method in methods:
            print(f"  • {method.replace('_', ' ').title()}")
    
    # Tamper flags
    flags = result.get('tamper_flags', [])
    if flags:
        print(f"\n🚩 Tamper Flags ({len(flags)}):")
        for flag in flags:
            print(f"  • {flag.replace('_', ' ').title()}")
    
    # Detailed analysis
    detailed = result.get('detailed_analysis', {})
    if detailed:
        print(f"\n📊 Detailed Analysis:")
        for method, analysis in detailed.items():
            if isinstance(analysis, dict):
                conf = analysis.get('confidence', 0)
                is_suspicious = (analysis.get('is_tampered', False) or 
                               analysis.get('is_suspicious', False) or 
                               analysis.get('has_anomalies', False) or 
                               not analysis.get('is_valid', True))
                
                status_icon = "🚨" if is_suspicious else "✅"
                method_name = method.replace('_', ' ').title()
                print(f"  {status_icon} {method_name}: {conf:.1%}")
    
    print("\n" + "=" * 60)

def show_system_status():
    """Show system status information."""
    print("\n🖥️  System Status")
    print("-" * 40)
    
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        print(f"✅ CUDA Available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        
        # Check YOLOv8
        try:
            from ultralytics import YOLO
            print("✅ YOLOv8 (Ultralytics): Available")
        except ImportError:
            print("❌ YOLOv8 (Ultralytics): Not available")
        
        # Check model file
        model_path = Path("backend/models/certificate_detection_yolov8.pt")
        if model_path.exists():
            print("✅ YOLOv8 Model: Available")
        else:
            print("❌ YOLOv8 Model: Not found")
        
        # Check dataset
        dataset_path = Path("dataset/data.yaml")
        if dataset_path.exists():
            print("✅ Dataset: Available")
        else:
            print("❌ Dataset: Not found")
        
    except Exception as e:
        print(f"❌ Error checking system status: {e}")

def main():
    """Main function."""
    try:
        asyncio.run(interactive_test())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()