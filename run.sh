#!/bin/bash

# Quick run script for Document Converter

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create necessary directories
mkdir -p uploads outputs

# Check if MinIO is needed and running
if ! lsof -i :9000 &> /dev/null; then
    echo "⚠️  MinIO server not detected on port 9000"
    echo "💡 To start MinIO: ./start_services.sh"
    echo "💡 To run without MinIO: set STORAGE_MODE=LOCAL in .env"
    echo ""
fi

# Run the application
echo "🚀 Starting Document Converter & Text Splitter..."
echo "📱 Open http://localhost:5000 in your browser"
echo "⏹️  Press Ctrl+C to stop"
echo ""

python3 app.py
