# Backend Deployment Guide

## Docker Deployment

### Prerequisites
- Docker installed
- AWS S3 bucket: `icmemo-documents-prod`
- AWS credentials with S3 access

### Environment Variables

Create a `.env` file in the `dashboard/backend/` directory with the following:

```bash
# Flask Configuration
FLASK_DEBUG=False
PORT=5001

# Storage Configuration
USE_S3=true
SURVEILLANCE_BASE_PATH=/app/data

# S3 Configuration
S3_BUCKET_NAME=icmemo-documents-prod
S3_BASE_PREFIX=trade_surveillance
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key

# CORS Configuration (comma-separated list of allowed origins)
CORS_ORIGINS=https://your-frontend-domain.com
```

### Build Docker Image

```bash
cd dashboard/backend
docker build -t trade-surveillance-backend .
```

### Run Docker Container

```bash
docker run -d \
  --name trade-surveillance-backend \
  -p 5001:5001 \
  --env-file .env \
  trade-surveillance-backend
```

### S3 Folder Structure

Ensure your S3 bucket has the following structure:

```
s3://icmemo-documents-prod/trade_surveillance/
├── August/
│   ├── Daily_Reports/
│   │   └── 01082025/
│   ├── Order Files/
│   └── Call Records/
├── September/
│   ├── Daily_Reports/
│   ├── Order Files/
│   └── Call Records/
└── ...
```

### Local Development (without Docker)

For local development without S3, set:

```bash
USE_S3=false
SURVEILLANCE_BASE_PATH=/path/to/trade_surveillance_prod
```

Then run:

```bash
python surveillance_api.py
```



