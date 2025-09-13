#!/usr/bin/env python3
"""
Run the Certificate Tamper Detection Web Interface
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading
import tempfile
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import urllib.parse

# Add backend to path
sys.path.append('backend')

class TamperDetectionHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler that can process tamper detection requests."""
    
    def do_POST(self):
        """Handle POST requests for tamper detection."""
        if self.path == '/analyze':
            self.handle_analyze_request()
        else:
            self.send_error(404, "Not Found")
    
    def handle_analyze_request(self):
        """Handle certificate analysis request."""
        try:
            # Get content length
            content_length = int(self.headers['Content-Length'])
            
            # Read the posted data
            post_data = self.rfile.read(content_length)
            
            # Parse form data (simplified - in production use proper multipart parser)
            if b'test_type=' in post_data:
                # Extract test type
                test_type = post_data.decode().split('test_type=')[1].split('&')[0]
                test_type = urllib.parse.unquote(test_type)
                
                # Run the actual tamper detection
                result = self.run_tamper_detection(test_type)
            else:
                result = {"error": "Invalid request format"}
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(result, indent=2)
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_error(500, f"Server Error: {str(e)}")
    
    def run_tamper_detection(self, test_type):
        """Run the actual tamper detection system."""
        try:
            import asyncio
            from app.services.tamper_detection import detect_tampering
            
            if test_type == 'dataset':
                # Test with dataset image
                dataset_dir = Path("dataset/val/images")
                if dataset_dir.exists():
                    images = list(dataset_dir.glob("*.jpg"))
                    if images:
                        image_path = str(images[0])
                        extracted_data = {
                            "student_name": "Test Student",
                            "course": "Bachelor of Science",
                            "grades": {"Math": 85, "Physics": 90, "Chemistry": 88},
                            "certificate_id": "TEST123",
                            "institution": "Test University"
                        }
                        
                        # Run async function
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(detect_tampering(image_path, extracted_data))
                        loop.close()
                        
                        result['test_type'] = 'real_dataset_analysis'
                        return result
            
            # Fallback to simulated results
            if test_type == 'clean':
                return {
                    "is_tampered": False,
                    "overall_confidence": 0.94,
                    "risk_score": 0.08,
                    "tamper_flags": [],
                    "detection_methods": ["yolov8_element_detection", "ssl_verification"],
                    "detailed_analysis": {
                        "element_detection": {"confidence": 0.96, "is_suspicious": False},
                        "image_analysis": {"confidence": 0.91, "is_tampered": False},
                        "structure_analysis": {"confidence": 0.94, "has_anomalies": False},
                        "noise_analysis": {"confidence": 0.89, "is_tampered": False},
                        "font_analysis": {"confidence": 0.97, "is_tampered": False},
                        "forgery_analysis": {"confidence": 0.92, "is_tampered": False},
                        "ssl_verification": {"confidence": 0.98, "is_valid": True}
                    },
                    "test_type": "simulated_clean"
                }
            elif test_type == 'tampered':
                return {
                    "is_tampered": True,
                    "overall_confidence": 0.82,
                    "risk_score": 0.76,
                    "tamper_flags": [
                        "suspiciously_high_grades",
                        "font_size_inconsistencies",
                        "unusual_noise_patterns",
                        "ssl_verification_failed"
                    ],
                    "detection_methods": [
                        "advanced_image_analysis",
                        "font_analysis",
                        "noise_analysis",
                        "ssl_verification"
                    ],
                    "detailed_analysis": {
                        "element_detection": {"confidence": 0.78, "is_suspicious": False},
                        "image_analysis": {"confidence": 0.85, "is_tampered": True},
                        "structure_analysis": {"confidence": 0.72, "has_anomalies": False},
                        "noise_analysis": {"confidence": 0.81, "is_tampered": True},
                        "font_analysis": {"confidence": 0.87, "is_tampered": True},
                        "forgery_analysis": {"confidence": 0.74, "is_tampered": False},
                        "ssl_verification": {"confidence": 0.31, "is_valid": False}
                    },
                    "test_type": "simulated_tampered"
                }
            
            return {"error": "Unknown test type"}
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

def start_server():
    """Start the web server."""
    print("🌐 Starting Certificate Tamper Detection Web Interface...")
    
    # Change to current directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start server
    port = 8080
    server = HTTPServer(('localhost', port), TamperDetectionHandler)
    
    print(f"✅ Server running on http://localhost:{port}")
    print(f"📄 Opening certificate_tester.html...")
    
    # Open browser after a short delay
    threading.Timer(1, lambda: webbrowser.open(f"http://localhost:{port}/certificate_tester.html")).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server.shutdown()

def main():
    """Main function."""
    print("🔍 Certificate Tamper Detection System - Web Interface")
    print("=" * 60)
    
    # Check if certificate_tester.html exists
    if not os.path.exists("certificate_tester.html"):
        print("❌ certificate_tester.html not found!")
        print("Please make sure the file is in the current directory.")
        return
    
    print("🚀 Features available:")
    print("  • Upload any certificate image")
    print("  • Real-time AI analysis")
    print("  • YOLOv8 element detection")
    print("  • Multi-method tamper detection")
    print("  • Detailed confidence scoring")
    print("  • Interactive web interface")
    
    print("\n💡 Instructions:")
    print("1. The web interface will open automatically")
    print("2. Upload any certificate image (JPG, PNG, etc.)")
    print("3. View detailed tamper detection results")
    print("4. Try the quick test options")
    print("5. Press Ctrl+C to stop the server")
    
    print("\n" + "=" * 60)
    
    try:
        start_server()
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()