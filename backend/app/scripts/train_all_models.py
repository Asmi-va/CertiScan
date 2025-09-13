import os
import sys
import subprocess
from pathlib import Path

# Add the parent directory to sys.path to import from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

def check_dependencies():
    """Check if required dependencies are installed and provide installation instructions if not."""
    missing_deps = []
    try:
        import torch
        import torchvision
    except ImportError:
        missing_deps.append("torch torchvision")
    
    try:
        import pandas
        import sklearn
    except ImportError:
        missing_deps.append("pandas scikit-learn")
    
    try:
        import yaml
    except ImportError:
        missing_deps.append("pyyaml")
    
    if missing_deps:
        print("\nMissing required dependencies. Please install them using:")
        print(f"pip install {' '.join(missing_deps)}")
        print("\nFor YOLOv5 (required for certificate detection):")
        print("pip install -U yolov5")
        print("\nAfter installing dependencies, run this script again.")
        return False
    return True

def main():
    print("Starting dataset preparation and model training process...")
    
    # Check dependencies before proceeding
    if not check_dependencies():
        return
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    # Step 1: Prepare the dataset
    print("\n=== Step 1: Preparing dataset ===")
    prepare_script = os.path.join(current_dir, "prepare_dataset.py")
    try:
        subprocess.run([sys.executable, prepare_script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during dataset preparation: {e}")
        return
    
    # Step 2: Train the certificate detector model
    print("\n=== Step 2: Training certificate detector model ===")
    cert_detector_script = os.path.join(current_dir, "train_certificate_detector.py")
    try:
        subprocess.run([sys.executable, cert_detector_script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during certificate detector training: {e}")
        print("Skipping to next step...")
    
    # Step 3: Train the SSL verifier model
    print("\n=== Step 3: Training SSL verifier model ===")
    ssl_verifier_script = os.path.join(current_dir, "train_ssl_verifier.py")
    try:
        subprocess.run([sys.executable, ssl_verifier_script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during SSL verifier training: {e}")
        return
    
    print("\nAll models trained successfully!")
    print("The models are now available for use in the certificate verification system.")
    print("\nTo use the models, restart the backend server.")

if __name__ == "__main__":
    main()