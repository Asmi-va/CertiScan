import os
import sys
import shutil
import random
from pathlib import Path

# Add the parent directory to sys.path to import from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings

def main():
    # Define paths
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'dataset')
    ssl_dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                   'SSL-certificate-dataset-main')
    
    # Create model directory if it doesn't exist
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    
    print(f"Preparing dataset from {dataset_path}")
    
    # Check if dataset exists
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset directory {dataset_path} not found")
        return
    
    # Check if SSL dataset exists
    if not os.path.exists(ssl_dataset_path):
        print(f"Error: SSL dataset directory {ssl_dataset_path} not found")
        return
    
    # Print dataset structure
    print("Dataset structure:")
    for root, dirs, files in os.walk(dataset_path):
        level = root.replace(dataset_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files[:5]:  # Show only first 5 files
            print(f"{sub_indent}{f}")
        if len(files) > 5:
            print(f"{sub_indent}... ({len(files) - 5} more files)")
    
    # Print SSL dataset structure
    print("\nSSL dataset structure:")
    for root, dirs, files in os.walk(ssl_dataset_path):
        level = root.replace(ssl_dataset_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")
    
    # Create validation split if it doesn't exist
    train_images_dir = os.path.join(dataset_path, 'train', 'images')
    train_labels_dir = os.path.join(dataset_path, 'train', 'labels')
    val_dir = os.path.join(dataset_path, 'val')
    val_images_dir = os.path.join(val_dir, 'images')
    val_labels_dir = os.path.join(val_dir, 'labels')
    
    if os.path.exists(train_images_dir) and not os.path.exists(val_dir):
        print("Creating validation split...")
        
        # Create validation directories
        os.makedirs(val_images_dir, exist_ok=True)
        os.makedirs(val_labels_dir, exist_ok=True)
        
        # Get all image files
        image_files = [f for f in os.listdir(train_images_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        # Randomly select 20% for validation
        random.seed(42)  # For reproducibility
        val_count = int(len(image_files) * 0.2)
        val_files = random.sample(image_files, val_count)
        
        print(f"Moving {val_count} files to validation set")
        
        # Move files to validation set
        for img_file in val_files:
            # Move image
            src_img = os.path.join(train_images_dir, img_file)
            dst_img = os.path.join(val_images_dir, img_file)
            shutil.move(src_img, dst_img)
            
            # Move corresponding label if it exists
            label_file = os.path.splitext(img_file)[0] + '.txt'
            src_label = os.path.join(train_labels_dir, label_file)
            if os.path.exists(src_label):
                dst_label = os.path.join(val_labels_dir, label_file)
                shutil.move(src_label, dst_label)
    
    print("Dataset preparation complete!")

if __name__ == "__main__":
    main()