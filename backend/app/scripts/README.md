# Certificate Verification Model Training Scripts

This directory contains scripts for preparing datasets and training models for certificate verification.

## Dependencies

To train the ML models, you'll need the following dependencies:

```bash
pip install torch torchvision yolov5 pandas scikit-learn pyyaml
```

However, the system is designed to work even without these dependencies. If the ML libraries are not available, the system will automatically fall back to rule-based methods.

## Available Scripts

### 1. prepare_dataset.py

This script prepares the certificate detection dataset by organizing the training and validation splits.

```bash
python -m app.scripts.prepare_dataset
```

### 2. train_certificate_detector.py

This script trains the YOLOv5 model for certificate element detection using the prepared dataset.

```bash
python -m app.scripts.train_certificate_detector
```

### 3. train_ssl_verifier.py

This script trains a machine learning model for SSL certificate verification using the SSL certificate dataset.

```bash
python -m app.scripts.train_ssl_verifier
```

## Dataset Structure

### Certificate Detection Dataset

The certificate detection dataset should be organized as follows:

```
dataset/
├── train/
│   ├── images/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   └── labels/
│       ├── image1.txt
│       ├── image2.txt
│       └── ...
└── val/
    ├── images/
    │   ├── image3.jpg
    │   ├── image4.jpg
    │   └── ...
    └── labels/
        ├── image3.txt
        ├── image4.txt
        └── ...
```

The label files should follow the YOLOv5 format:

```
<class_id> <x_center> <y_center> <width> <height>
```

Where:
- `class_id`: 0 for degree, 1 for signature, 2 for stamp
- `x_center`, `y_center`: Normalized center coordinates (0-1)
- `width`, `height`: Normalized width and height (0-1)

### SSL Certificate Dataset

The SSL certificate dataset is a CSV file with the following columns:

- Domain
- Issuer
- Valid From
- Valid Till
- Serial Number
- Key Algorithm
- Issuer Common Name
- Issuer Organization
- Issuer Organization Unit
- Malicious or Not (1 for malicious, 0 for valid)

## Model Output

The trained models will be saved in the `models` directory:

- `certificate_detector.pt`: YOLOv5 model for certificate element detection
- `ssl_verifier.pkl`: Random Forest model for SSL certificate verification
- `ssl_encoders.pkl`: Label encoders for categorical features in the SSL dataset

## Integration

The trained models are automatically integrated into the certificate verification system through the following services:

- `app.services.certificate_detection`: Uses the YOLOv5 model to detect certificate elements
- `app.services.ssl_verification`: Uses the SSL verification model to check certificate validity

These services are used in the tamper detection pipeline to enhance the verification process.

## Fallback Mechanisms

The system is designed with graceful degradation in mind:

- If ML dependencies (torch, yolov5, etc.) are not available, the certificate detection will use rule-based heuristics to estimate certificate elements.
- If the SSL verification model is not available, the system will use rule-based checks based on trusted issuers, validity periods, key sizes, and signature algorithms.

This ensures the system remains functional even without the ML components, though with potentially reduced accuracy.