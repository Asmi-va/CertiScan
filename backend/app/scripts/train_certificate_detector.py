import os
import sys
import torch
import yaml
from pathlib import Path

# Add the parent directory to sys.path to import from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings
from app.services.certificate_detection import CertificateDetector

def main():
    # Define paths
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'dataset')
    train_path = os.path.join(dataset_path, 'train')
    val_path = os.path.join(dataset_path, 'val') if os.path.exists(os.path.join(dataset_path, 'val')) else None
    
    # Create data.yaml file for YOLOv5
    data_yaml_path = os.path.join(settings.MODEL_DIR, 'certificate_data.yaml')
    
    # Define class names based on the dataset
    class_names = ['degree', 'signature', 'stamp']
    
    # Create data.yaml content
    data_yaml = {
        'train': train_path,
        'val': val_path if val_path else train_path,
        'nc': len(class_names),
        'names': class_names
    }
    
    # Ensure model directory exists
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    
    # Write data.yaml file
    with open(data_yaml_path, 'w') as f:
        yaml.dump(data_yaml, f)
    
    print(f"Created data.yaml at {data_yaml_path}")
    
    # Initialize and train the model
    detector = CertificateDetector()
    
    # Train the model
    epochs = 50  # Adjust based on your needs
    batch_size = 16  # Adjust based on your GPU memory
    img_size = 640
    
    print("Starting model training...")
    detector.train(
        data_yaml_path=data_yaml_path,
        epochs=epochs,
        batch_size=batch_size,
        img_size=img_size
    )
    
    print("Training complete!")
    print(f"Model saved to {os.path.join(settings.MODEL_DIR, 'certificate_detector.pt')}")

if __name__ == "__main__":
    main()