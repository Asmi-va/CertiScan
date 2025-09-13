#!/usr/bin/env python3
"""
Quick performance test for the tamper detection system.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append('backend')

from app.services.tamper_detection import detect_tampering

async def quick_performance_test():
    """Quick performance test with one image."""
    print("🚀 Quick Performance Test")
    print("=" * 40)
    
    # Find a test image
    val_images_dir = Path('dataset/val/images')
    if not val_images_dir.exists():
        print("❌ Validation dataset not found")
        return False
    
    certificate_images = list(val_images_dir.glob('*.jpg'))
    if not certificate_images:
        print("❌ No certificate images found")
        return False
    
    test_image = certificate_images[0]
    print(f"📄 Testing: {test_image.name}")
    
    # Simple test data
    extracted_data = {
        "student_name": "Test Student",
        "course": "Test Course",
        "grades": {"Math": 85, "Physics": 90}
    }
    
    # Measure performance
    start_time = time.time()
    
    try:
        result = await detect_tampering(str(test_image), extracted_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n⏱️  Processing Time: {processing_time:.2f} seconds")
        print(f"🎯 Is Tampered: {result.get('is_tampered', 'Unknown')}")
        print(f"📊 Confidence: {result.get('overall_confidence', 0):.3f}")
        print(f"🔍 Methods Used: {len(result.get('detection_methods', []))}")
        print(f"🚩 Flags: {len(result.get('tamper_flags', []))}")
        
        # Performance assessment
        if processing_time < 5:
            print("✅ EXCELLENT: Very fast processing")
        elif processing_time < 15:
            print("✅ GOOD: Acceptable processing time")
        elif processing_time < 30:
            print("⚠️  SLOW: Processing time could be improved")
        else:
            print("❌ VERY SLOW: Performance optimization needed")
        
        return processing_time < 30  # Consider acceptable if under 30 seconds
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_performance_test())
    print(f"\nTest {'PASSED' if success else 'FAILED'}")