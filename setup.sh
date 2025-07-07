#!/bin/bash

# Document Converter Setup Script

echo "🚀 Setting up Document Converter & Text Splitter..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Python is installed
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Display Python version
python_version=$(python3 --version)
echo "✅ Found $python_version"

# Check if pip is installed
if ! command_exists pip3; then
    echo "❌ pip3 is required but not installed."
    echo "Please install pip3 and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment."
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔄 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Setup complete!"
    echo ""
    echo "🚀 Quick Start Options:"
    echo "1. Simple start (local storage):   ./run.sh"
    echo "2. Full start (with MinIO):        ./start_services.sh"
    echo "3. Open http://localhost:5000 in your browser"
    echo ""
    echo "💡 For first-time users, we recommend option 1 (./run.sh)"
else
    echo "❌ Failed to install dependencies."
    echo "Please check the error messages above and try again."
    exit 1
fi
