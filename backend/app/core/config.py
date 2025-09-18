import os
import secrets
from typing import List, Optional, Union
from pathlib import Path

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Fake Certificate Detection System"
    
    # Secret key for JWT token
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # CORS settings
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://localhost:8001,http://localhost:8080"
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from string to list."""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS

    # MongoDB settings
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "certificate_verification")
    
    # File upload settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    STATIC_DIR: str = os.getenv("STATIC_DIR", "./static")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    # OCR settings
    TESSERACT_CMD: Optional[str] = os.getenv("TESSERACT_CMD", None)  # Path to tesseract executable
    
    # Tamper detection settings
    TAMPER_DETECTION_THRESHOLD: float = 0.85  # Confidence threshold for tamper detection
    
    # Model settings
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./models")  # Directory for ML models
    
    # Dataset settings - flexible path configuration
    SSL_DATASET_DIR: str = os.getenv("SSL_DATASET_DIR", "./SSL-certificate-dataset-main")
    SSL_DATASET_FILE: str = os.getenv("SSL_DATASET_FILE", "SSL_dataset.csv")
    CERTIFICATE_DATASET_DIR: str = os.getenv("CERTIFICATE_DATASET_DIR", "./dataset")
    CERTIFICATE_DATA_YAML: str = os.getenv("CERTIFICATE_DATA_YAML", "data.yaml")
    
    # Blockchain settings (optional)
    USE_BLOCKCHAIN: bool = False
    BLOCKCHAIN_PROVIDER: Optional[str] = None
    
    class Config:
        case_sensitive = True
        env_file = ".env"

    def get_ssl_dataset_path(self) -> Path:
        """Get the full path to the SSL dataset CSV file."""
        return Path(self.SSL_DATASET_DIR) / self.SSL_DATASET_FILE
    
    def get_certificate_dataset_path(self) -> Path:
        """Get the path to the certificate detection dataset directory."""
        return Path(self.CERTIFICATE_DATASET_DIR)
    
    def get_certificate_data_yaml_path(self) -> Path:
        """Get the path to the certificate dataset YAML configuration."""
        return Path(self.CERTIFICATE_DATASET_DIR) / self.CERTIFICATE_DATA_YAML
    
    def validate_dataset_paths(self) -> dict:
        """Validate that all required dataset paths exist and return status."""
        validation_result = {
            "ssl_dataset": False,
            "certificate_dataset": False,
            "certificate_yaml": False,
            "errors": []
        }
        
        # Check SSL dataset
        ssl_path = self.get_ssl_dataset_path()
        if ssl_path.exists() and ssl_path.is_file():
            validation_result["ssl_dataset"] = True
        else:
            validation_result["errors"].append(f"SSL dataset not found at: {ssl_path}")
        
        # Check certificate dataset directory
        cert_dataset_path = self.get_certificate_dataset_path()
        if cert_dataset_path.exists() and cert_dataset_path.is_dir():
            validation_result["certificate_dataset"] = True
            
            # Check for required subdirectories
            required_dirs = ["train", "val"]
            for req_dir in required_dirs:
                dir_path = cert_dataset_path / req_dir
                if not (dir_path.exists() and dir_path.is_dir()):
                    validation_result["errors"].append(f"Required directory not found: {dir_path}")
                    validation_result["certificate_dataset"] = False
        else:
            validation_result["errors"].append(f"Certificate dataset directory not found at: {cert_dataset_path}")
        
        # Check certificate YAML configuration
        yaml_path = self.get_certificate_data_yaml_path()
        if yaml_path.exists() and yaml_path.is_file():
            validation_result["certificate_yaml"] = True
        else:
            validation_result["errors"].append(f"Certificate data YAML not found at: {yaml_path}")
        
        return validation_result


settings = Settings()