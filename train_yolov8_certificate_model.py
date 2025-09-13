#!/usr/bin/env python3
"""
Script to train YOLOv8 model for certificate detection using GPU.
"""

import os
import sys
import torch
from pathlib import Path

# Add backend to path
sys.path.append('backend')

def check_gpu_availability():
    """Check GPU availability and display info."""
    print("=== GPU Information ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"  Memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.1f} GB")
        return True
    else:
        print("No GPU available")
        return False

def train_certificate_model():
    """Train YOLOv8 model for certificate detection."""
    try:
        from ultralytics import YOLO
        
        print("\n=== Training YOLOv8 Certificate Detection Model ===")
        
        # Check dataset
        dataset_yaml = "dataset/data.yaml"
        if not os.path.exists(dataset_yaml):
            print(f"❌ Dataset not found: {dataset_yaml}")
            return False
        
        print(f"✅ Dataset found: {dataset_yaml}")
        
        # Load pretrained model
        print("Loading YOLOv8 pretrained model...")
        model = YOLO('yolov8n.pt')  # Nano model for faster training
        
        # Configure training parameters based on GPU
        if torch.cuda.is_available():
            device = 0
            batch_size = 16
            workers = 8
            epochs = 100
            print(f"🚀 Training on GPU: {torch.cuda.get_device_name(0)}")
        else:
            device = 'cpu'
            batch_size = 8
            workers = 4
            epochs = 50
            print("⚠️  Training on CPU (slower)")
        
        # Start training
        print(f"\nStarting training with:")
        print(f"  - Device: {device}")
        print(f"  - Batch size: {batch_size}")
        print(f"  - Epochs: {epochs}")
        print(f"  - Workers: {workers}")
        
        results = model.train(
            data=dataset_yaml,
            epochs=epochs,
            batch=batch_size,
            imgsz=640,
            save_period=10,
            project='runs/detect',
            name='certificate_detection',
            patience=15,
            device=device,
            workers=workers,
            amp=True,  # Automatic Mixed Precision
            cache=True,  # Cache images
            optimizer='AdamW',
            lr0=0.01,
            lrf=0.01,
            momentum=0.937,
            weight_decay=0.0005,
            warmup_epochs=3,
            warmup_momentum=0.8,
            warmup_bias_lr=0.1,
            verbose=True
        )
        
        # Check if training was successful
        best_model_path = Path('runs/detect/certificate_detection/weights/best.pt')
        if best_model_path.exists():
            print(f"\n✅ Training completed successfully!")
            print(f"   Best model saved: {best_model_path}")
            
            # Copy to models directory
            models_dir = Path('backend/models')
            models_dir.mkdir(exist_ok=True)
            
            target_path = models_dir / 'certificate_detection_yolov8.pt'
            import shutil
            shutil.copy2(best_model_path, target_path)
            print(f"   Model copied to: {target_path}")
            
            # Test the trained model
            print("\n=== Testing Trained Model ===")
            trained_model = YOLO(str(target_path))
            
            # Test on a sample image from validation set
            val_images = list(Path('dataset/val/images').glob('*.jpg'))
            if val_images:
                test_image = val_images[0]
                print(f"Testing on: {test_image}")
                
                results = trained_model(str(test_image))
                
                print("Detection results:")
                for r in results:
                    boxes = r.boxes
                    if boxes is not None and len(boxes) > 0:
                        for i in range(len(boxes)):
                            cls = int(boxes.cls[i])
                            conf = float(boxes.conf[i])
                            class_names = ['degree', 'signature', 'stamp']
                            if cls < len(class_names):
                                print(f"  - {class_names[cls]}: {conf:.2f}")
                    else:
                        print("  - No detections")
            
            return True
        else:
            print("❌ Training failed - no model file found")
            return False
            
    except ImportError:
        print("❌ YOLOv8 not installed. Install with: pip install ultralytics")
        return False
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")
        return False

def main():
    """Main function."""
    print("YOLOv8 Certificate Detection Model Training")
    print("=" * 50)
    
    # Check GPU
    gpu_available = check_gpu_availability()
    
    if not gpu_available:
        print("\n⚠️  No GPU detected. Training will be slower on CPU.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Training cancelled.")
            return False
    
    # Train model
    success = train_certificate_model()
    
    if success:
        print("\n🎉 Model training completed successfully!")
        print("\nNext steps:")
        print("1. Test the model with real certificate images")
        print("2. Integrate with the tamper detection system")
        print("3. Fine-tune parameters if needed")
    else:
        print("\n❌ Model training failed. Check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)