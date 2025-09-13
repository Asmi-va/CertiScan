# Dataset Integration Guide

This document explains how the Certificate Verification System integrates with your datasets and how to configure them properly.

## Overview

The system has been updated to remove hardcoded paths and provide flexible dataset configuration through environment variables. This makes the system portable across different environments and operating systems.

## Dataset Structure

### SSL Certificate Dataset
- **Location**: `SSL-certificate-dataset-main/SSL_dataset.csv`
- **Purpose**: Contains SSL certificate data for verification and fraud detection
- **Format**: CSV file with columns for certificate details and malicious flags

### Certificate Detection Dataset
- **Location**: `dataset/` directory
- **Purpose**: Training data for YOLOv5 model to detect certificate elements
- **Structure**:
  ```
  dataset/
  ├── train/
  │   ├── images/
  │   └── labels/
  ├── val/
  │   ├── images/
  │   └── labels/
  └── data.yaml
  ```

## Configuration

### Environment Variables

You can configure dataset paths using these environment variables:

```bash
# SSL Certificate Dataset
SSL_DATASET_DIR=./SSL-certificate-dataset-main
SSL_DATASET_FILE=SSL_dataset.csv

# Certificate Detection Dataset
CERTIFICATE_DATASET_DIR=./dataset
CERTIFICATE_DATA_YAML=data.yaml
```

### Configuration Methods

1. **Environment Variables**: Set directly in your shell
2. **`.env` File**: Create a `.env` file in the project root
3. **Default Values**: System uses sensible defaults if not configured

## Setup Instructions

### 1. Quick Setup

Run the dataset setup script:

```bash
cd backend
python -m app.scripts.setup_datasets
```

This will:
- Validate your current dataset configuration
- Show detailed validation results
- Provide recommendations for fixing issues

### 2. Create Environment File

Generate a sample `.env` file:

```bash
cd backend
python -m app.scripts.setup_datasets --create-env
```

### 3. Manual Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env with your specific paths
```

## Validation

### Automatic Validation

The system automatically validates datasets on startup and will:
- Check if dataset files exist
- Validate dataset structure
- Provide detailed error messages
- Continue with fallback methods if datasets are unavailable

### Manual Validation

Test your dataset integration:

```bash
python test_dataset_integration.py
```

This comprehensive test will verify:
- Configuration loading
- Dataset path resolution
- Dataset structure validation
- Service initialization
- System readiness

## Troubleshooting

### Common Issues

1. **Dataset Not Found**
   - Check that your dataset directories exist
   - Verify paths in `.env` file
   - Ensure file permissions are correct

2. **Invalid Dataset Structure**
   - Verify SSL dataset CSV has required columns
   - Check certificate dataset has train/val folders
   - Ensure YAML configuration is valid

3. **Permission Issues**
   - Check read permissions on dataset files
   - Verify write permissions for model directory
   - Ensure upload directory is writable

### Error Messages

The system provides detailed error messages:

```
ERROR: SSL dataset file not found at: ./SSL-certificate-dataset-main/SSL_dataset.csv
ERROR: Missing required directories: ['train']
WARNING: Missing expected columns: ['malicious']
```

### Fallback Behavior

When datasets are unavailable, the system will:
- Use rule-based detection instead of ML models
- Disable SSL verification features gracefully
- Continue operating with reduced functionality
- Log warnings about missing features

## Advanced Configuration

### Custom Dataset Locations

For non-standard setups, you can specify absolute paths:

```bash
SSL_DATASET_DIR=/path/to/your/ssl-dataset
CERTIFICATE_DATASET_DIR=/path/to/your/certificate-dataset
```

### Multiple Environments

Use different `.env` files for different environments:

```bash
# Development
cp .env.example .env.dev

# Production
cp .env.example .env.prod
```

### Docker Configuration

When using Docker, mount your datasets as volumes:

```yaml
volumes:
  - ./SSL-certificate-dataset-main:/app/SSL-certificate-dataset-main
  - ./dataset:/app/dataset
```

## Integration Status

After setup, check integration status:

1. **Startup Logs**: Check console output when starting the application
2. **Validation Script**: Run `python test_dataset_integration.py`
3. **API Health Check**: Use the system status endpoints

## Support

If you encounter issues:

1. Run the validation script for detailed diagnostics
2. Check the startup logs for error messages
3. Verify your dataset structure matches the expected format
4. Ensure all required files are present and readable

The system is designed to be resilient and will continue operating even with partial dataset availability, but full functionality requires both datasets to be properly configured.