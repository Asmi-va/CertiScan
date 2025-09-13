import os
import sys
import pandas as pd
import pickle
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# Add the parent directory to sys.path to import from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings

def main():
    # Define paths
    ssl_dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                   'SSL-certificate-dataset-main', 'SSL_dataset.csv')
    
    # Ensure model directory exists
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    
    # Load the SSL certificate dataset
    print(f"Loading SSL certificate dataset from {ssl_dataset_path}")
    df = pd.read_csv(ssl_dataset_path)
    
    # Rename columns to match our expected format
    column_mapping = {
        'Domain': 'domain',
        'Issuer': 'issuer',
        'Valid From': 'valid_from',
        'Valid Till': 'valid_till',
        'Serial Number': 'serial_number',
        'Key Algorithm': 'key_algorithm',
        'Issuer Common Name': 'issuer_common_name',
        'Issuer Organization': 'issuer_organization',
        'Issuer Organization Unit': 'issuer_organization_unit',
        'Malicious or Not': 'is_malicious'
    }
    
    # Apply column renaming if needed
    df = df.rename(columns={col: column_mapping.get(col, col) for col in df.columns})
    
    # Ensure the target column exists
    if 'is_malicious' not in df.columns:
        print("Error: 'is_malicious' column not found in the dataset")
        return
    
    # Prepare features and target
    # Convert categorical features to numerical using label encoding
    categorical_cols = ['issuer', 'key_algorithm', 'issuer_common_name', 
                       'issuer_organization', 'issuer_organization_unit']
    
    # Create label encoders for each categorical column
    encoders = {}
    for col in categorical_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = df[col].fillna('unknown')
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
    
    # Convert date columns to numerical (days since epoch)
    date_cols = ['valid_from', 'valid_till']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: x.timestamp() if pd.notnull(x) else 0)
    
    # Fill missing values
    df = df.fillna(0)
    
    # Prepare features and target
    X = df.drop(['is_malicious', 'domain'], axis=1, errors='ignore')
    y = df['is_malicious']
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train a Random Forest classifier
    print("Training SSL certificate verification model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate the model
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.4f}")
    
    # Save the model and encoders
    model_path = os.path.join(settings.MODEL_DIR, 'ssl_verifier.pkl')
    encoders_path = os.path.join(settings.MODEL_DIR, 'ssl_encoders.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    with open(encoders_path, 'wb') as f:
        pickle.dump(encoders, f)
    
    print(f"Model saved to {model_path}")
    print(f"Encoders saved to {encoders_path}")

if __name__ == "__main__":
    main()