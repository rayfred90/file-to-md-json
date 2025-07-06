#!/bin/bash

# MinIO Bucket Setup Script
# Creates default buckets and sets up policies

echo "🪣 Setting up MinIO buckets..."

# MinIO client configuration
MC_HOST_NAME="local"
MINIO_URL="http://localhost:9000"
ACCESS_KEY="minioadmin"
SECRET_KEY="minioadmin"

# Configure MinIO client
echo "⚙️  Configuring MinIO client..."
mc alias set $MC_HOST_NAME $MINIO_URL $ACCESS_KEY $SECRET_KEY

# Create buckets
echo "📦 Creating buckets..."
mc mb ${MC_HOST_NAME}/uploads --ignore-existing
mc mb ${MC_HOST_NAME}/outputs --ignore-existing  
mc mb ${MC_HOST_NAME}/splits --ignore-existing

# Set bucket policies (public read for easy access)
echo "🔒 Setting bucket policies..."
mc anonymous set public ${MC_HOST_NAME}/uploads
mc anonymous set public ${MC_HOST_NAME}/outputs
mc anonymous set public ${MC_HOST_NAME}/splits

echo "✅ MinIO buckets setup complete!"
echo ""
echo "Buckets created:"
mc ls $MC_HOST_NAME
