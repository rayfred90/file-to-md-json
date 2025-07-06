# MinIO Integration for Document Converter

This directory contains all MinIO-related files for the document converter project.

## Directory Structure

```
minio/
├── config/
│   └── minio.env           # MinIO server configuration
├── data/                   # MinIO data storage (auto-created)
├── logs/                   # MinIO server logs
├── minio_service.py        # Python MinIO service integration
├── start-minio.sh          # Script to start MinIO server
├── setup-buckets.sh        # Script to create and configure buckets
└── README.md              # This file
```

## Quick Start

1. **Install MinIO** (if not already installed):
   ```bash
   wget https://dl.min.io/server/minio/release/linux-amd64/minio
   chmod +x minio
   sudo mv minio /usr/local/bin/
   
   wget https://dl.min.io/client/mc/release/linux-amd64/mc
   chmod +x mc
   sudo mv mc /usr/local/bin/
   ```

2. **Start MinIO Server**:
   ```bash
   ./start-minio.sh
   ```

3. **Setup Buckets** (in another terminal):
   ```bash
   ./setup-buckets.sh
   ```

4. **Access MinIO Console**:
   - URL: http://localhost:9001
   - Username: minioadmin
   - Password: minioadmin

## Configuration

- **API Endpoint**: http://localhost:9000
- **Console**: http://localhost:9001
- **Data Storage**: `./data/`
- **Default Buckets**: uploads, outputs, splits

## Integration

The `minio_service.py` file provides the Python integration with MinIO for the Flask application, replacing the previous Supabase storage service.
