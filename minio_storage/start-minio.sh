#!/bin/bash

# MinIO Server Start Script
# This script starts the MinIO server with proper configuration

MINIO_DIR="."
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
mkdir -p "$(dirname "$LOG_FILE")"

# Set proper permissions
chmod 755 "$DATA_DIR"

# Check disk space before starting
AVAILABLE_SPACE=$(df "$DATA_DIR" | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -lt 1048576 ]; then  # Less than 1GB
    echo "⚠️  Warning: Low disk space available: $(( AVAILABLE_SPACE / 1024 ))MB"
fi

# Performance optimization: Set I/O scheduler to deadline for better MinIO performance
if [ -w /sys/block/sda/queue/scheduler ]; then
    echo deadline | sudo tee /sys/block/sda/queue/scheduler > /dev/null 2>&1 || true
fi

# Start MinIO server with improved settings
echo "🎯 Starting MinIO server with enhanced I/O settings..."
echo "💾 Available disk space: $(( AVAILABLE_SPACE / 1024 ))MB"
echo ""

# Use nice to reduce I/O priority and avoid blocking system I/O
nice -n 10 minio server "$DATA_DIR" \
    --console-address ":9001" \
    --quiet \
    2>&1 | tee "$LOG_FILE"
