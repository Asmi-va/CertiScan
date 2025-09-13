"""
Main FastAPI application for Certificate Verification System
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.main import app

if __name__ == "__main__":
    import uvicorn
    # Change port to 8002 to avoid conflicts
    uvicorn.run(app, host="0.0.0.0", port=8002)
