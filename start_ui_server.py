#!/usr/bin/env python3
"""
Start the Certificate Tamper Detection UI Server
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading
from pathlib import Path

def start_fastapi_server():
    """Start the FastAPI backend server."""
    print("🚀 Starting FastAPI backend server...")
    
    # Change to backend directory
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found!")
        return None
    
    # Start uvicorn server
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8002",
            "--reload"
        ], cwd=backend_dir)

        print("✅ FastAPI server starting on http://localhost:8002")
        return process
    except Exception as e:
        print(f"❌ Failed to start FastAPI server: {e}")
        return None

def start_frontend_server():
    """Start a simple HTTP server for the frontend."""
    print("🌐 Starting frontend server...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return None
    
    try:
        # Start simple HTTP server with dashboard.html as default page
        # Using Python 3.7+ http.server supports --directory option
        process = subprocess.Popen([
            sys.executable, "-m", "http.server", "3000", "--directory", str(frontend_dir)
        ])
        
        print("✅ Frontend server starting on http://localhost:3000")
        print("ℹ️  Dashboard UI available at http://localhost:3000/dashboard.html")
        return process
    except Exception as e:
        print(f"❌ Failed to start frontend server: {e}")
        return None

def wait_for_server(url, timeout=30):
    """Wait for server to be ready."""
    import requests
    
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def open_browser():
    """Open the web browser to the UI."""
    print("🌐 Opening web browser...")
    webbrowser.open("http://localhost:3000")

def main():
    """Main function to start the UI."""
    print("🔍 Certificate Tamper Detection System - UI Launcher")
    print("=" * 60)
    
    # Start backend server
    backend_process = start_fastapi_server()
    if not backend_process:
        print("❌ Failed to start backend server")
        return
    
    # Start frontend server
    frontend_process = start_frontend_server()
    if not frontend_process:
        print("❌ Failed to start frontend server")
        backend_process.terminate()
        return
    
    # Wait for servers to start
    print("\n⏳ Waiting for servers to start...")
    time.sleep(3)
    
    # Check if backend is ready
    print("🔍 Checking backend server...")
    try:
        import requests
        if wait_for_server("http://localhost:8001", 10):
            print("✅ Backend server is ready")
        else:
            print("⚠️  Backend server may not be fully ready")
    except ImportError:
        print("⚠️  Cannot check backend status (requests not installed)")

    # Open browser
    threading.Timer(2, open_browser).start()

    print("\n" + "=" * 60)
    print("🎉 Certificate Tamper Detection UI is ready!")
    print("=" * 60)
    print("📱 Frontend UI: http://localhost:3000")
    print("🔧 Backend API: http://localhost:8001")
    print("📚 API Docs: http://localhost:8001/docs")
    print("=" * 60)
    print("\n💡 Instructions:")
    print("1. The web interface should open automatically")
    print("2. Upload a certificate image or use sample tests")
    print("3. View detailed tamper detection results")
    print("4. Press Ctrl+C to stop the servers")
    print("\n🔍 Features available:")
    print("- YOLOv8 certificate element detection")
    print("- Multi-method tamper analysis")
    print("- Real-time confidence scoring")
    print("- Detailed analysis breakdown")
    
    try:
        # Keep servers running
        print("\n⏳ Servers running... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        print("✅ Servers stopped successfully")

if __name__ == "__main__":
    main()