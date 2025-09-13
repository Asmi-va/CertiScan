import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.config import settings

class SSLCertificateVerifier:
    """Class for verifying SSL certificates using the SSL certificate dataset and trained model."""
    
    def __init__(self):
        self.dataset_path = settings.get_ssl_dataset_path()
        self.dataset = None
        self.initialized = False
        self.model_loaded = False
        self.model = None
        self.encoders = None
    
    async def initialize(self):
        """Initialize the verifier by loading the SSL certificate dataset and model."""
        try:
            # Validate dataset path exists
            if not self.dataset_path.exists():
                raise FileNotFoundError(f"SSL certificate dataset not found at {self.dataset_path}")
            
            # Load the dataset
            self.dataset = pd.read_csv(str(self.dataset_path))
            
            # Rename columns for easier access
            column_names = [
                'subject', 'issuer', 'valid_from', 'valid_till', 'serial_number',
                'public_key_algorithm', 'signature_algorithm', 'issuer_country',
                'issuer_state', 'issuer_locality', 'issuer_organization',
                'issuer_organization_unit', 'malicious'
            ]
            
            if len(self.dataset.columns) == len(column_names):
                self.dataset.columns = column_names
            
            # Load the trained model if available
            model_path = os.path.join(settings.MODEL_DIR, 'ssl_verifier.pkl')
            encoders_path = os.path.join(settings.MODEL_DIR, 'ssl_encoders.pkl')
            
            try:
                # Check if pickle is available
                import pickle
                
                if os.path.exists(model_path) and os.path.exists(encoders_path):
                    with open(model_path, 'rb') as f:
                        self.model = pickle.load(f)
                    
                    with open(encoders_path, 'rb') as f:
                        self.encoders = pickle.load(f)
                    
                    self.model_loaded = True
                    print("SSL verification model loaded successfully")
                else:
                    self.model_loaded = False
                    print("SSL verification model not found, falling back to dataset matching")
            except ImportError:
                self.model_loaded = False
                print("Pickle module not available, falling back to dataset matching")
            
            self.initialized = True
            return True
        except Exception as e:
            print(f"Error initializing SSL certificate verifier: {str(e)}")
            return False
    
    def _prepare_features(self, certificate_data: Dict[str, Any]) -> pd.DataFrame:
        """Prepare features for model prediction.
        
        Args:
            certificate_data: Dictionary containing SSL certificate data
            
        Returns:
            DataFrame with prepared features
        """
        # Create a single row dataframe
        df = pd.DataFrame([certificate_data])
        
        # Convert date columns to numerical (days since epoch)
        date_cols = ['valid_from', 'valid_till']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: x.timestamp() if pd.notnull(x) else 0)
        
        # Apply label encoding to categorical columns
        categorical_cols = ['issuer', 'subject', 'public_key_algorithm', 'signature_algorithm']
        
        for col in categorical_cols:
            if col in df.columns and col in self.encoders:
                # If value not in encoder, use -1 as unknown
                df[col] = df[col].apply(lambda x: 
                                       self.encoders[col].transform([x])[0] 
                                       if x in self.encoders[col].classes_ else -1)
        
        # Fill missing values
        df = df.fillna(0)
        
        # Ensure all columns from training are present
        if hasattr(self.model, 'feature_names_in_'):
            missing_cols = set(self.model.feature_names_in_) - set(df.columns)
            for col in missing_cols:
                df[col] = 0
            
            # Ensure columns are in the right order
            df = df[self.model.feature_names_in_]
        
        return df
    
    async def verify(self, certificate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a certificate using the SSL dataset and trained model."""
        result = {
            "is_valid": True,
            "confidence": 0.0,
            "details": {}
        }
        
        try:
            # Initialize if not already done
            if not self.initialized:
                success = await self.initialize()
                if not success:
                    result["is_valid"] = False
                    result["details"]["error"] = "Failed to initialize SSL certificate verifier"
                    return result
            
            # Extract relevant fields from certificate data
            subject = certificate_data.get('subject', '')
            issuer = certificate_data.get('issuer', '')
            valid_from = certificate_data.get('valid_from', '')
            valid_till = certificate_data.get('valid_till', '')
            
            # Check if certificate is expired
            if valid_till:
                try:
                    # Parse date string (assuming format is DD/MM/YYYY HH:MM)
                    valid_till_date = datetime.strptime(valid_till, '%d/%m/%Y %H:%M')
                    if valid_till_date < datetime.now():
                        result["is_valid"] = False
                        result["details"]["reason"] = "Certificate is expired"
                        result["confidence"] = 1.0
                        return result
                except ValueError:
                    # If date parsing fails, continue with other checks
                    pass
            
            # Try using the trained model if available
            method = "No match found"
            if self.model_loaded and len(certificate_data) >= 3:  # Need at least a few features
                try:
                    # Prepare features
                    features = self._prepare_features(certificate_data)
                    
                    # Make prediction
                    prediction = self.model.predict(features)[0]
                    prediction_proba = self.model.predict_proba(features)[0]
                    
                    # Get confidence
                    is_malicious = prediction == 1
                    confidence = prediction_proba[1] if is_malicious else prediction_proba[0]
                    method = "ML model prediction"
                    
                    if is_malicious and confidence > 0.7:
                        result["is_valid"] = False
                        result["details"]["reason"] = "Certificate identified as potentially malicious by ML model"
                        result["confidence"] = float(confidence)
                        result["details"]["verification_method"] = method
                        return result
                except Exception as e:
                    print(f"Error using ML model for prediction: {str(e)}")
                    # Fall back to dataset matching
            
            # Check if certificate is in the dataset
            if subject and issuer:
                # Filter dataset for similar certificates
                similar_certs = self.dataset[
                    (self.dataset['subject'].str.contains(subject, case=False, na=False)) &
                    (self.dataset['issuer'].str.contains(issuer, case=False, na=False))
                ]
                
                if not similar_certs.empty:
                    # Check if any similar certificates are marked as malicious
                    malicious_certs = similar_certs[similar_certs['malicious'] > 0.5]
                    
                    if not malicious_certs.empty:
                        result["is_valid"] = False
                        result["details"]["reason"] = "Similar certificates found in malicious database"
                        result["confidence"] = float(malicious_certs['malicious'].mean())
                        result["details"]["verification_method"] = "Database match"
                        return result
                    else:
                        # Found in dataset and not malicious
                        result["confidence"] = 0.9
                        result["details"]["matches"] = len(similar_certs)
                        result["details"]["verification_method"] = "Database match"
                        return result
            
            # If we couldn't find a match or make a determination
            result["confidence"] = 0.5
            result["details"]["note"] = "Certificate could not be definitively verified against database or model"
            result["details"]["verification_method"] = method
            return result
            
        except Exception as e:
            result["is_valid"] = False
            result["details"]["error"] = f"Error verifying SSL certificate: {str(e)}"
            return result

# Singleton instance
ssl_verifier = SSLCertificateVerifier()

async def verify_ssl_certificate(certificate_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a certificate using the SSL dataset and trained model."""
    return await ssl_verifier.verify(certificate_data)

async def extract_ssl_certificate_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract SSL certificate data from OCR extracted data."""
    ssl_data = {
        "subject": extracted_data.get("name", ""),
        "issuer": extracted_data.get("institution", ""),
        "valid_from": extracted_data.get("issue_date", ""),
        "valid_till": extracted_data.get("expiry_date", ""),
        "serial_number": extracted_data.get("cert_id", ""),
        "public_key_algorithm": extracted_data.get("key_algorithm", ""),
        "signature_algorithm": extracted_data.get("signature_algorithm", "")
    }
    
    return ssl_data