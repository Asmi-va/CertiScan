#!/usr/bin/env python3
"""
Test script for dataset integration functionality.
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def test_dataset_integration():
    """Test the dataset integration functionality."""
    print("Testing Dataset Integration")
    print("=" * 50)
    
    try:
        # Test configuration
        print("\n1. Testing Configuration...")
        from app.core.config import settings
        
        print(f"   SSL Dataset Path: {settings.get_ssl_dataset_path()}")
        print(f"   Certificate Dataset Path: {settings.get_certificate_dataset_path()}")
        print(f"   Certificate YAML Path: {settings.get_certificate_data_yaml_path()}")
        
        # Test dataset validation
        print("\n2. Testing Dataset Validation...")
        validation_results = settings.validate_dataset_paths()
        
        for key, value in validation_results.items():
            if key != "errors":
                status = "✓" if value else "✗"
                print(f"   {key}: {status}")
        
        if validation_results["errors"]:
            print("   Errors:")
            for error in validation_results["errors"]:
                print(f"     - {error}")
        
        # Test comprehensive validation
        print("\n3. Testing Comprehensive Validation...")
        from app.utils.dataset_validator import dataset_validator
        
        full_results = dataset_validator.validate_all_datasets()
        print(f"   Overall Status: {full_results['overall_status']}")
        
        # Test SSL verification service
        print("\n4. Testing SSL Verification Service...")
        from app.services.ssl_verification import ssl_verifier
        
        init_result = await ssl_verifier.initialize()
        print(f"   SSL Verifier Initialization: {'✓' if init_result else '✗'}")
        
        if init_result and ssl_verifier.dataset is not None:
            print(f"   SSL Dataset Records: {len(ssl_verifier.dataset)}")
        
        # Test certificate detection service
        print("\n5. Testing Certificate Detection Service...")
        from app.services.certificate_detection import certificate_detector
        
        init_result = await certificate_detector.initialize()
        print(f"   Certificate Detector Initialization: {'✓' if init_result else '✗'}")
        print(f"   Using ML: {'✓' if certificate_detector.use_ml else '✗ (Fallback)'}")
        
        # Test startup validation
        print("\n6. Testing Startup Validation...")
        from app.services.startup_validation import validate_system_startup
        
        startup_results = await validate_system_startup()
        print(f"   System Ready: {'✓' if startup_results['system_ready'] else '✗'}")
        
        if startup_results.get("errors"):
            print("   Errors:")
            for error in startup_results["errors"]:
                print(f"     - {error}")
        
        if startup_results.get("warnings"):
            print("   Warnings:")
            for warning in startup_results["warnings"]:
                print(f"     - {warning}")
        
        print("\n" + "=" * 50)
        
        # Overall result
        if (validation_results["ssl_dataset"] and 
            validation_results["certificate_dataset"] and 
            startup_results["system_ready"]):
            print("✓ ALL TESTS PASSED - Dataset integration successful!")
            return True
        else:
            print("⚠ SOME TESTS FAILED - Check the issues above")
            return False
    
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    success = asyncio.run(test_dataset_integration())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()