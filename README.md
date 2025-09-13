# Fake Certificate Detection System

A comprehensive platform for detecting fake or tampered educational certificates using OCR, AI anomaly detection, and secure verification.

## Tech Stack

- **Frontend**: React + Tailwind CSS
- **Backend**: Python FastAPI
- **Database**: MongoDB (Atlas or Local)
- **OCR**: Tesseract OCR (pytesseract) + OpenCV
- **AI Tamper Detection**: PyTorch (pre-trained CNN) or simple OpenCV heuristics
- **Blockchain (Optional)**: Store SHA-256 hash on testnet or local chain
- **Authentication**: JWT-based auth
- **Hosting**: Render / Vercel for demo

## Core Features

- Upload interface for certificate images/PDFs
- OCR extraction for Name, Roll No, Course, Marks, Certificate ID
- Database lookup against institution records
- Tamper detection for altered seals, signatures, or grades
- QR Code / Digital Signature support for new certificates
- Admin dashboard with verification logs & blacklist
- Alerts for flagged/tampered certificates

## API Endpoints

- `POST /api/upload`: Accept certificate file, run OCR + tamper checks, return PASS/FLAG with reasons
- `POST /api/institution/upload`: Bulk upload institution records (CSV/JSON)
- `GET /api/verify/{cert_id}`: Verify single certificate by ID
- `GET /api/admin/logs`: View verification history + flagged certificates
- `POST /api/admin/blacklist`: Blacklist forged certificate IDs

## Database Collections

- **certificates**: Stores issued certificates with fields: cert_id, name, roll_no, course, issue_date, hash, institution_id
- **institutions**: Stores institution details + their certificate records
- **verifications**: Logs each verification attempt with result + timestamp
- **blacklist**: Stores invalid or flagged certificate IDs

## Backend Flow

1. User uploads certificate
2. FastAPI saves file temporarily
3. OCR extracts text & metadata
4. Compare extracted data with MongoDB records
5. Run tamper detection (image hash, AI model, or checksum)
6. Return PASS/FLAG with evidence (highlighted image parts)
7. Log verification event in MongoDB

## Tamper Detection Methods

- Compare file hash with DB hash
- Detect font/style inconsistencies using OpenCV
- Image forgery detection via noise-level anomalies
- Mismatch in signatures or photos vs stored originals
- Certificate element detection using YOLOv5 (trained on certificate dataset) or fallback heuristics
- SSL certificate verification using ML model (trained on SSL certificate dataset) or rule-based checks

## Project Structure

```
/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── admin.py
│   │   │   │   ├── certificate.py
│   │   │   │   └── institution.py
│   │   │   └── api.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── ocr.py
│   │   │   ├── tamper_detection.py
│   │   │   └── verification.py
│   │   └── main.py
│   ├── .env
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   └── layout/
│   │   │       ├── Footer.js
│   │   │       └── Navbar.js
│   │   ├── pages/
│   │   │   ├── admin/
│   │   │   │   ├── AdminBlacklist.js
│   │   │   │   ├── AdminDashboard.js
│   │   │   │   └── AdminLogs.js
│   │   │   ├── Home.js
│   │   │   ├── InstitutionUpload.js
│   │   │   ├── NotFound.js
│   │   │   ├── VerificationResult.js
│   │   │   └── VerifyCertificate.js
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   ├── package.json
│   └── tailwind.config.js
└── README.md
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables by creating a `.env` file based on the provided template

4. Install Tesseract OCR:
   - Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt install tesseract-ocr`
   - Mac: `brew install tesseract`

5. Run the FastAPI server:
   ```
   uvicorn app.main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

## Setup Instructions

1. Clone this repository
2. Install backend dependencies: `pip install -r requirements.txt`
3. Install frontend dependencies: `cd frontend && npm install`
4. Set up MongoDB (local or Atlas)
5. Configure environment variables
6. Run backend: `uvicorn app.main:app --reload`
7. Run frontend: `cd frontend && npm start`

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── admin.py
│   │   │   │   ├── certificate.py
│   │   │   │   └── institution.py
│   │   │   └── api.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── ocr.py
│   │   │   ├── tamper_detection.py
│   │   │   └── verification.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── App.js
└── README.md
```

## License

MIT