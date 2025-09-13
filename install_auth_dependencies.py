#!/usr/bin/env python3
"""
Install authentication system dependencies.
"""
import subprocess
import sys

def install_dependencies():
    """Install required dependencies for authentication system."""
    dependencies = [
        "pyotp",           # Two-factor authentication
        "qrcode[pil]",     # QR code generation
        "python-jose[cryptography]",  # JWT tokens
        "passlib[bcrypt]", # Password hashing
        "cryptography",    # Cryptographic operations
        "python-multipart" # Form data handling
    ]
    
    print("Installing authentication system dependencies...")
    
    for dep in dependencies:
        try:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✓ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {dep}: {e}")
            return False
    
    print("\n✓ All authentication dependencies installed successfully!")
    return True

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)