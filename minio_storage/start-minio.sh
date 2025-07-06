#!/bin/bash

# MinIO Server Start Script
# This script starts the MinIO server with proper configuration

MINIO_DIR="/home/adebo/con/minio_storage"
DATA_DIR="$MINIO_DIR/data"
CONFIG_FILE="$MINIO_DIR/config/minio.env"
LOG_FILE="$MINIO_DIR/logs/minio.log"

echo "🚀 Starting MinIO Server..."
echo "📁 Data Directory: $DATA_DIR"
echo "⚙️  Configuration: $CONFIG_FILE"
echo "📝 Log File: $LOG_FILE"
echo "🌐 Console URL: http://localhost:9001"
echo "🔗 API URL: http://localhost:9000"
echo ""

# Source configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "✅ Configuration loaded from $CONFIG_FILE"
else
    echo "⚠️  Configuration file not found, using defaults"
    export MINIO_ROOT_USER=minioadmin
    export MINIO_ROOT_PASSWORD=minioadmin
fi

# Create data directory if it doesn't exist
mkdir -p "$DATA_DIR"

# Start MinIO server
echo "🎯 Starting MinIO server..."
minio server "$DATA_DIR" --console-address ":9001" 2>&1 | tee "$LOG_FILE"
