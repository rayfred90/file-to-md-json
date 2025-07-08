#!/bin/bash

# Document Converter Setup Script

echo "🚀 Setting up Document Converter & Text Splitter..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ===== System Dependencies (Python3 & pip3) =====
echo "🔎 Checking for Python 3 and pip3..."

if ! command_exists python3; then
    echo "❌ Python 3 not found. Installing Python 3..."
    if command_exists apt-get; then
        sudo apt-get update
        sudo apt-get install -y python3
    elif command_exists yum; then
        sudo yum install -y python3
    elif command_exists dnf; then
        sudo dnf install -y python3
    else
        echo "❌ Unsupported package manager. Please install Python 3 manually."
        exit 1
    fi
fi

if ! command_exists pip3; then
    echo "❌ pip3 not found. Installing pip3..."
    if command_exists apt-get; then
        sudo apt-get install -y python3-pip
    elif command_exists yum; then
        sudo yum install -y python3-pip
    elif command_exists dnf; then
        sudo dnf install -y python3-pip
    else
        echo "❌ Unsupported package manager. Please install pip3 manually."
        exit 1
    fi
fi

# Display Python version
python_version=$(python3 --version)
echo "✅ Found $python_version"
pip_version=$(pip3 --version)
echo "✅ Found $pip_version"

# ===== MinIO Installation =====
# Install MinIO server if not already installed
if ! command_exists minio; then
    echo "📥 Downloading MinIO server binary..."
    wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O minio
    chmod +x minio
    echo "🔑 Installing MinIO server (requires sudo)..."
    sudo mv minio /usr/local/bin/
    if command_exists minio; then
        echo "✅ MinIO server installed: $(minio --version)"
    else
        echo "❌ Failed to install MinIO server."
        exit 1
    fi
else
    echo "✅ MinIO server already installed: $(minio --version)"
fi

# Install MinIO client (mc) if not already installed
if ! command_exists mc; then
    echo "📥 Downloading MinIO client (mc)..."
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O mc
    chmod +x mc
    echo "🔑 Installing MinIO client (requires sudo)..."
    sudo mv mc /usr/local/bin/
    if command_exists mc; then
        echo "✅ MinIO client installed: $(mc --version)"
    else
        echo "❌ Failed to install MinIO client."
        exit 1
    fi
else
    echo "✅ MinIO client already installed: $(mc --version)"
fi

# ===== Python Virtual Environment =====
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
