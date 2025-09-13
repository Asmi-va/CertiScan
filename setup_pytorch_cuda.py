#!/usr/bin/env python3
"""
Script to help install PyTorch with CUDA support for YOLOv8 training.
"""

import subprocess
import sys
import torch

def check_current_pytorch():
    """Check current PyTorch installation."""
    print("=== Current PyTorch Installation ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        return True
    else:
        print("❌ CUDA not available in current PyTorch installation")
        return False

def get_cuda_install_command():
    """Get the correct PyTorch installation command for CUDA 12.x."""
    print("\n=== PyTorch CUDA Installation ===")
    print("Your system has CUDA 12.7, so you need PyTorch with CUDA 12.x support.")
    print("\nRecommended installation commands:")
    
    # For CUDA 12.1 (most compatible)
    cuda_121_cmd = [
        sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", 
        "--index-url", "https://download.pytorch.org/whl/cu121"
    ]
    
    # For CUDA 12.4 (newer)
    cuda_124_cmd = [
        sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", 
        "--index-url", "https://download.pytorch.org/whl/cu124"
    ]
    
    print("\nOption 1 (Recommended - CUDA 12.1):")
    print(" ".join(cuda_121_cmd))
    
    print("\nOption 2 (CUDA 12.4):")
    print(" ".join(cuda_124_cmd))
    
    return cuda_121_cmd, cuda_124_cmd

def install_pytorch_cuda():
    """Install PyTorch with CUDA support."""
    try:
        print("\n=== Installing PyTorch with CUDA Support ===")
        
        # Uninstall current PyTorch first
        print("1. Uninstalling current PyTorch...")
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", 
            "torch", "torchvision", "torchaudio", "-y"
        ], check=True)
        
        # Install PyTorch with CUDA 12.1 support
        print("2. Installing PyTorch with CUDA 12.1 support...")
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cu121"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        print("✅ PyTorch with CUDA support installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def verify_cuda_installation():
    """Verify CUDA installation after reinstalling PyTorch."""
    try:
        print("\n=== Verifying CUDA Installation ===")
        print("Reloading PyTorch...")
        
        # Note: In a real scenario, you'd need to restart Python to reload PyTorch
        print("⚠️  You need to restart Python/your terminal to test the new PyTorch installation.")
        print("\nAfter restarting, run this to verify:")
        print("python -c \"import torch; print('CUDA available:', torch.cuda.is_available())\"")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main function."""
    print("PyTorch CUDA Setup for YOLOv8 Training")
    print("=" * 50)
    
    # Check current installation
    cuda_available = check_current_pytorch()
    
    if cuda_available:
        print("\n✅ PyTorch with CUDA is already installed!")
        print("You can proceed with YOLOv8 training.")
        return True
    
    # Show installation options
    cmd1, cmd2 = get_cuda_install_command()
    
    print("\n" + "=" * 50)
    print("INSTALLATION INSTRUCTIONS:")
    print("=" * 50)
    
    print("\n1. AUTOMATIC INSTALLATION (Recommended):")
    print("   Run this script with --install flag:")
    print(f"   python {sys.argv[0]} --install")
    
    print("\n2. MANUAL INSTALLATION:")
    print("   Copy and run one of the commands above in your terminal")
    
    print("\n3. AFTER INSTALLATION:")
    print("   Restart your Python environment and run:")
    print("   python train_yolov8_certificate_model.py")
    
    # Check if user wants automatic installation
    if len(sys.argv) > 1 and sys.argv[1] == '--install':
        print("\n🚀 Starting automatic installation...")
        success = install_pytorch_cuda()
        if success:
            verify_cuda_installation()
        return success
    else:
        print(f"\n💡 To install automatically, run:")
        print(f"   python {sys.argv[0]} --install")
        return False

if __name__ == "__main__":
    main()