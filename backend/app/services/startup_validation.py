"""
Startup validation service for checking system readiness.
"""
import logging
from typing import Dict, Any

from app.core.config import settings
from app.utils.dataset_validator import dataset_validator

logger = logging.getLogger(__name__)

class StartupValidator:
    """Service for validating system components during startup."""
    
    def __init__(self):
        self.validation_results = {}
    
    async def validate_system(self) -> Dict[str, Any]:
        """Perform comprehensive system validation."""
        logger.info("Starting system validation...")
        
        results = {
            "system_ready": False,
            "datasets": {},
            "configuration": {},
            "services": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Validate datasets
            dataset_results = dataset_validator.validate_all_datasets()
            results["datasets"] = dataset_results
            
            # Validate configuration
            config_results = self.validate_configuration()
            results["configuration"] = config_results
            
            # Validate required directories
            directory_results = self.validate_directories()
            results["directories"] = directory_results
            
            # Determine system readiness
            datasets_ok = dataset_results["overall_status"] in ["valid", "partial"]
            config_ok = config_results["valid"]
            directories_ok = directory_results["valid"]
            
            results["system_ready"] = datasets_ok and config_ok and directories_ok
            
            # Collect warnings and errors
            if dataset_results.get("warnings"):
                results["warnings"].extend(dataset_results["warnings"])
            if dataset_results.get("errors"):
                results["errors"].extend(dataset_results["errors"])
            
            if not config_ok:
                results["errors"].extend(config_results.get("errors", []))
            
            if not directories_ok:
                results["errors"].extend(directory_results.get("errors", []))
            
            # Log results
            if results["system_ready"]:
                logger.info("✓ System validation completed successfully")
            else:
                logger.warning("⚠ System validation completed with issues")
                for error in results["errors"]:
                    logger.error(f"  - {error}")
            
            return results
        
        except Exception as e:
            logger.error(f"System validation failed: {str(e)}")
            results["errors"].append(f"System validation failed: {str(e)}")
            return results
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate system configuration."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "settings": {}
        }
        
        try:
            # Check critical settings
            critical_settings = [
                "MONGO_URL",
                "MONGO_DB_NAME",
                "MODEL_DIR",
                "UPLOAD_DIR"
            ]
            
            for setting in critical_settings:
                value = getattr(settings, setting, None)
                result["settings"][setting] = value
                
                if not value:
                    result["errors"].append(f"Critical setting {setting} is not configured")
                    result["valid"] = False
            
            # Validate dataset paths using settings methods
            try:
                ssl_path = settings.get_ssl_dataset_path()
                cert_path = settings.get_certificate_dataset_path()
                yaml_path = settings.get_certificate_data_yaml_path()
                
                result["settings"]["ssl_dataset_path"] = str(ssl_path)
                result["settings"]["certificate_dataset_path"] = str(cert_path)
                result["settings"]["certificate_yaml_path"] = str(yaml_path)
                
            except Exception as e:
                result["errors"].append(f"Error resolving dataset paths: {str(e)}")
                result["valid"] = False
            
            # Check optional settings
            optional_settings = [
                "TESSERACT_CMD",
                "USE_BLOCKCHAIN",
                "BLOCKCHAIN_PROVIDER"
            ]
            
            for setting in optional_settings:
                value = getattr(settings, setting, None)
                result["settings"][setting] = value
                
                if setting == "TESSERACT_CMD" and not value:
                    result["warnings"].append("Tesseract OCR path not configured - OCR functionality may be limited")
        
        except Exception as e:
            result["errors"].append(f"Configuration validation failed: {str(e)}")
            result["valid"] = False
        
        return result
    
    def validate_directories(self) -> Dict[str, Any]:
        """Validate required directories exist or can be created."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "directories": {}
        }
        
        try:
            import os
            from pathlib import Path
            
            # Directories that should exist or be creatable
            required_dirs = [
                ("upload_dir", settings.UPLOAD_DIR),
                ("static_dir", settings.STATIC_DIR),
                ("model_dir", settings.MODEL_DIR)
            ]
            
            for dir_name, dir_path in required_dirs:
                try:
                    path_obj = Path(dir_path)
                    
                    if path_obj.exists():
                        if path_obj.is_dir():
                            result["directories"][dir_name] = {
                                "path": str(path_obj),
                                "status": "exists",
                                "writable": os.access(path_obj, os.W_OK)
                            }
                        else:
                            result["errors"].append(f"{dir_name} path exists but is not a directory: {path_obj}")
                            result["valid"] = False
                    else:
                        # Try to create directory
                        try:
                            path_obj.mkdir(parents=True, exist_ok=True)
                            result["directories"][dir_name] = {
                                "path": str(path_obj),
                                "status": "created",
                                "writable": True
                            }
                            logger.info(f"Created directory: {path_obj}")
                        except PermissionError:
                            result["errors"].append(f"Permission denied creating {dir_name}: {path_obj}")
                            result["valid"] = False
                        except Exception as e:
                            result["errors"].append(f"Failed to create {dir_name}: {path_obj} - {str(e)}")
                            result["valid"] = False
                
                except Exception as e:
                    result["errors"].append(f"Error validating {dir_name}: {str(e)}")
                    result["valid"] = False
        
        except Exception as e:
            result["errors"].append(f"Directory validation failed: {str(e)}")
            result["valid"] = False
        
        return result
    
    def get_system_status_summary(self) -> str:
        """Get a brief system status summary."""
        if not hasattr(self, '_last_validation'):
            return "System validation not performed yet"
        
        results = self._last_validation
        
        if results["system_ready"]:
            return "✓ System is ready"
        else:
            error_count = len(results.get("errors", []))
            warning_count = len(results.get("warnings", []))
            return f"⚠ System has issues: {error_count} errors, {warning_count} warnings"


# Global startup validator instance
startup_validator = StartupValidator()

async def validate_system_startup() -> Dict[str, Any]:
    """Convenience function for system startup validation."""
    results = await startup_validator.validate_system()
    startup_validator._last_validation = results
    return results

def get_system_status() -> str:
    """Get current system status summary."""
    return startup_validator.get_system_status_summary()