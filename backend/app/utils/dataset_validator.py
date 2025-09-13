"""
Dataset validation utilities for certificate verification system.
"""
import os
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class DatasetValidator:
    """Utility class for validating dataset integrity and structure."""
    
    def __init__(self):
        self.validation_results = {}
    
    def validate_all_datasets(self) -> Dict[str, Any]:
        """Validate all datasets and return comprehensive results."""
        results = {
            "ssl_dataset": self.validate_ssl_dataset(),
            "certificate_dataset": self.validate_certificate_dataset(),
            "overall_status": "unknown",
            "errors": [],
            "warnings": []
        }
        
        # Determine overall status
        ssl_valid = results["ssl_dataset"]["valid"]
        cert_valid = results["certificate_dataset"]["valid"]
        
        if ssl_valid and cert_valid:
            results["overall_status"] = "valid"
        elif ssl_valid or cert_valid:
            results["overall_status"] = "partial"
            results["warnings"].append("Some datasets are missing or invalid")
        else:
            results["overall_status"] = "invalid"
            results["errors"].append("All datasets are missing or invalid")
        
        return results
    
    def validate_ssl_dataset(self) -> Dict[str, Any]:
        """Validate the SSL certificate dataset."""
        result = {
            "valid": False,
            "path": str(settings.get_ssl_dataset_path()),
            "errors": [],
            "warnings": [],
            "info": {}
        }
        
        try:
            ssl_path = settings.get_ssl_dataset_path()
            
            # Check if file exists
            if not ssl_path.exists():
                result["errors"].append(f"SSL dataset file not found at: {ssl_path}")
                return result
            
            # Check if it's a file
            if not ssl_path.is_file():
                result["errors"].append(f"SSL dataset path is not a file: {ssl_path}")
                return result
            
            # Try to load and validate CSV structure
            try:
                df = pd.read_csv(str(ssl_path))
                result["info"]["total_records"] = len(df)
                result["info"]["columns"] = list(df.columns)
                
                # Check for expected columns (flexible approach)
                expected_columns = [
                    'subject', 'issuer', 'valid_from', 'valid_till', 
                    'serial_number', 'malicious'
                ]
                
                missing_columns = []
                for col in expected_columns:
                    # Check for exact match or similar column names
                    if col not in df.columns:
                        similar_cols = [c for c in df.columns if col.lower() in c.lower()]
                        if not similar_cols:
                            missing_columns.append(col)
                
                if missing_columns:
                    result["warnings"].append(f"Missing expected columns: {missing_columns}")
                
                # Check for malicious column values
                if 'malicious' in df.columns:
                    malicious_count = df['malicious'].sum() if df['malicious'].dtype in ['int64', 'float64'] else 0
                    result["info"]["malicious_certificates"] = int(malicious_count)
                
                result["valid"] = True
                logger.info(f"SSL dataset validated successfully: {len(df)} records")
                
            except pd.errors.EmptyDataError:
                result["errors"].append("SSL dataset file is empty")
            except pd.errors.ParserError as e:
                result["errors"].append(f"Error parsing SSL dataset CSV: {str(e)}")
            except Exception as e:
                result["errors"].append(f"Error reading SSL dataset: {str(e)}")
        
        except Exception as e:
            result["errors"].append(f"Unexpected error validating SSL dataset: {str(e)}")
        
        return result
    
    def validate_certificate_dataset(self) -> Dict[str, Any]:
        """Validate the certificate detection dataset."""
        result = {
            "valid": False,
            "path": str(settings.get_certificate_dataset_path()),
            "errors": [],
            "warnings": [],
            "info": {}
        }
        
        try:
            dataset_path = settings.get_certificate_dataset_path()
            yaml_path = settings.get_certificate_data_yaml_path()
            
            # Check if dataset directory exists
            if not dataset_path.exists():
                result["errors"].append(f"Certificate dataset directory not found: {dataset_path}")
                return result
            
            if not dataset_path.is_dir():
                result["errors"].append(f"Certificate dataset path is not a directory: {dataset_path}")
                return result
            
            # Check for required subdirectories
            required_dirs = ["train", "val"]
            optional_dirs = ["test", "valid"]
            
            existing_dirs = []
            missing_dirs = []
            
            for req_dir in required_dirs:
                dir_path = dataset_path / req_dir
                if dir_path.exists() and dir_path.is_dir():
                    existing_dirs.append(req_dir)
                    # Count images and labels
                    images_dir = dir_path / "images"
                    labels_dir = dir_path / "labels"
                    
                    if images_dir.exists():
                        image_count = len(list(images_dir.glob("*.*")))
                        result["info"][f"{req_dir}_images"] = image_count
                    
                    if labels_dir.exists():
                        label_count = len(list(labels_dir.glob("*.txt")))
                        result["info"][f"{req_dir}_labels"] = label_count
                else:
                    missing_dirs.append(req_dir)
            
            # Check optional directories
            for opt_dir in optional_dirs:
                dir_path = dataset_path / opt_dir
                if dir_path.exists() and dir_path.is_dir():
                    existing_dirs.append(opt_dir)
            
            result["info"]["existing_directories"] = existing_dirs
            
            if missing_dirs:
                result["errors"].append(f"Missing required directories: {missing_dirs}")
                return result
            
            # Validate YAML configuration
            yaml_validation = self.validate_yaml_config(yaml_path)
            result["info"]["yaml_config"] = yaml_validation
            
            if not yaml_validation["valid"]:
                result["warnings"].extend(yaml_validation["errors"])
            
            result["valid"] = True
            logger.info(f"Certificate dataset validated successfully at: {dataset_path}")
        
        except Exception as e:
            result["errors"].append(f"Unexpected error validating certificate dataset: {str(e)}")
        
        return result
    
    def validate_yaml_config(self, yaml_path: Path) -> Dict[str, Any]:
        """Validate the YAML configuration file for certificate dataset."""
        result = {
            "valid": False,
            "path": str(yaml_path),
            "errors": [],
            "config": {}
        }
        
        try:
            if not yaml_path.exists():
                result["errors"].append(f"YAML config file not found: {yaml_path}")
                return result
            
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            result["config"] = config
            
            # Check required fields
            required_fields = ["nc", "names"]
            for field in required_fields:
                if field not in config:
                    result["errors"].append(f"Missing required field in YAML: {field}")
            
            # Validate class names
            if "names" in config:
                expected_classes = ["degree", "signature", "stamp"]
                actual_classes = config["names"]
                
                if not isinstance(actual_classes, list):
                    result["errors"].append("'names' field should be a list")
                elif set(actual_classes) != set(expected_classes):
                    result["errors"].append(f"Expected classes {expected_classes}, got {actual_classes}")
            
            # Validate number of classes
            if "nc" in config and "names" in config:
                if config["nc"] != len(config["names"]):
                    result["errors"].append(f"Number of classes (nc={config['nc']}) doesn't match names length ({len(config['names'])})")
            
            if not result["errors"]:
                result["valid"] = True
        
        except yaml.YAMLError as e:
            result["errors"].append(f"Error parsing YAML file: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Error reading YAML file: {str(e)}")
        
        return result
    
    def create_dataset_report(self) -> str:
        """Create a human-readable dataset validation report."""
        validation_results = self.validate_all_datasets()
        
        report = []
        report.append("=" * 60)
        report.append("DATASET VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Overall Status: {validation_results['overall_status'].upper()}")
        report.append("")
        
        # SSL Dataset Report
        ssl_result = validation_results["ssl_dataset"]
        report.append("SSL Certificate Dataset:")
        report.append(f"  Status: {'✓ VALID' if ssl_result['valid'] else '✗ INVALID'}")
        report.append(f"  Path: {ssl_result['path']}")
        
        if ssl_result.get("info"):
            info = ssl_result["info"]
            if "total_records" in info:
                report.append(f"  Records: {info['total_records']}")
            if "malicious_certificates" in info:
                report.append(f"  Malicious: {info['malicious_certificates']}")
        
        if ssl_result["errors"]:
            report.append("  Errors:")
            for error in ssl_result["errors"]:
                report.append(f"    - {error}")
        
        if ssl_result["warnings"]:
            report.append("  Warnings:")
            for warning in ssl_result["warnings"]:
                report.append(f"    - {warning}")
        
        report.append("")
        
        # Certificate Dataset Report
        cert_result = validation_results["certificate_dataset"]
        report.append("Certificate Detection Dataset:")
        report.append(f"  Status: {'✓ VALID' if cert_result['valid'] else '✗ INVALID'}")
        report.append(f"  Path: {cert_result['path']}")
        
        if cert_result.get("info"):
            info = cert_result["info"]
            if "existing_directories" in info:
                report.append(f"  Directories: {', '.join(info['existing_directories'])}")
            
            for key, value in info.items():
                if key.endswith("_images") or key.endswith("_labels"):
                    report.append(f"  {key.replace('_', ' ').title()}: {value}")
        
        if cert_result["errors"]:
            report.append("  Errors:")
            for error in cert_result["errors"]:
                report.append(f"    - {error}")
        
        if cert_result["warnings"]:
            report.append("  Warnings:")
            for warning in cert_result["warnings"]:
                report.append(f"    - {warning}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


# Global validator instance
dataset_validator = DatasetValidator()

def validate_datasets() -> Dict[str, Any]:
    """Convenience function to validate all datasets."""
    return dataset_validator.validate_all_datasets()

def print_dataset_report():
    """Print a comprehensive dataset validation report."""
    report = dataset_validator.create_dataset_report()
    print(report)
    return report