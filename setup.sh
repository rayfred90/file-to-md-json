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
        echo "📦 Using apt package manager..."
        sudo apt-get update && sudo apt-get install -y python3 python3-venv
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install Python 3 with apt. Please check your package manager and try again."
            exit 1
        fi
    elif command_exists yum; then
        echo "📦 Using yum package manager..."
        sudo yum install -y python3 python3-venv
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install Python 3 with yum. Please check your package manager and try again."
            exit 1
        fi
    elif command_exists dnf; then
        echo "📦 Using dnf package manager..."
        sudo dnf install -y python3 python3-venv
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install Python 3 with dnf. Please check your package manager and try again."
            exit 1
        fi
    else
        echo "❌ No supported package manager detected (apt, yum, or dnf)."
        echo "   Please install Python 3.8+ manually and re-run this script."
        echo "   Visit https://www.python.org/downloads/ for installation instructions."
        exit 1
    fi
    
    # Verify Python 3 installation
    if ! command_exists python3; then
        echo "❌ Python 3 installation failed. Please install Python 3 manually."
        exit 1
    fi
    echo "✅ Python 3 installed successfully"
else
    echo "✅ Python 3 already installed"
fi

if ! command_exists pip3; then
    echo "❌ pip3 not found. Installing pip3..."
    if command_exists apt-get; then
        echo "📦 Installing pip3 with apt..."
        sudo apt-get install -y python3-pip
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install pip3 with apt. Please check your package manager and try again."
            exit 1
        fi
    elif command_exists yum; then
        echo "📦 Installing pip3 with yum..."
        sudo yum install -y python3-pip
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install pip3 with yum. Please check your package manager and try again."
            exit 1
        fi
    elif command_exists dnf; then
        echo "📦 Installing pip3 with dnf..."
        sudo dnf install -y python3-pip
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install pip3 with dnf. Please check your package manager and try again."
            exit 1
        fi
    else
        echo "❌ No supported package manager detected (apt, yum, or dnf)."
        echo "   Please install pip3 manually and re-run this script."
        echo "   Visit https://pip.pypa.io/en/stable/installation/ for installation instructions."
        exit 1
    fi
    
    # Verify pip3 installation
    if ! command_exists pip3; then
        echo "❌ pip3 installation failed. Please install pip3 manually."
        exit 1
    fi
    echo "✅ pip3 installed successfully"
else
    echo "✅ pip3 already installed"
fi

# Display Python version
python_version=$(python3 --version)
echo "✅ Found $python_version"
pip_version=$(pip3 --version)
echo "✅ Found $pip_version"

# ===== MinIO Installation =====
echo "🗄️ Checking MinIO server and client..."

# Install MinIO server if not already installed
if ! command_exists minio; then
    echo "📥 Downloading MinIO server binary..."
    if ! wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O minio; then
        echo "❌ Failed to download MinIO server. Please check your internet connection."
        exit 1
    fi
    chmod +x minio
    echo "🔑 Installing MinIO server (requires sudo)..."
    if ! sudo mv minio /usr/local/bin/; then
        echo "❌ Failed to install MinIO server. Please check your sudo permissions."
        exit 1
    fi
    if command_exists minio; then
        echo "✅ MinIO server installed: $(minio --version)"
    else
        echo "❌ MinIO server installation verification failed."
        exit 1
    fi
else
    echo "✅ MinIO server already installed: $(minio --version)"
fi

# Install MinIO client (mc) if not already installed
if ! command_exists mc; then
    echo "📥 Downloading MinIO client (mc)..."
    if ! wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O mc; then
        echo "❌ Failed to download MinIO client. Please check your internet connection."
        exit 1
    fi
    chmod +x mc
    echo "🔑 Installing MinIO client (requires sudo)..."
    if ! sudo mv mc /usr/local/bin/; then
        echo "❌ Failed to install MinIO client. Please check your sudo permissions."
        exit 1
    fi
    if command_exists mc; then
        echo "✅ MinIO client installed: $(mc --version)"
    else
        echo "❌ MinIO client installation verification failed."
        exit 1
    fi
else
    echo "✅ MinIO client already installed: $(mc --version)"
fi

# ===== Python Virtual Environment =====
echo "🐍 Setting up Python virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    if ! python3 -m venv venv; then
        echo "❌ Failed to create virtual environment."
        echo "   Make sure python3-venv is installed: sudo apt install python3-venv"
        exit 1
    fi
    echo "✅ Virtual environment created successfully"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
if [ $? -eq 0 ]; then
    echo "✅ Virtual environment activated"
else
    echo "❌ Failed to activate virtual environment."
    exit 1
fi

# Upgrade pip (with --break-system-packages for modern distributions)
echo "🔄 Upgrading pip..."
if ! pip install --upgrade pip --break-system-packages 2>/dev/null; then
    # Fallback without --break-system-packages for older systems
    if ! pip install --upgrade pip; then
        echo "❌ Failed to upgrade pip. Please check your Python installation."
        exit 1
    fi
fi
echo "✅ pip upgraded successfully"

# Install requirements (with --break-system-packages for modern distributions)
echo "📚 Installing Python dependencies..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found. Please ensure you are in the correct directory."
    exit 1
fi

if ! pip install -r requirements.txt --break-system-packages 2>/dev/null; then
    # Fallback without --break-system-packages for older systems
    if ! pip install -r requirements.txt; then
        echo "❌ Failed to install Python dependencies."
        echo "   Please check the error messages above and ensure all system dependencies are installed."
        echo "   You may need to install additional system packages for some Python libraries."
        exit 1
    fi
fi
echo "✅ Python dependencies installed successfully"

echo ""
echo "🎉 Setup completed successfully!"
echo "================================"
echo ""
echo "🚀 Quick Start Options:"
echo "1. Simple start (local storage):   ./run.sh"
echo "2. Full start (with MinIO):        ./start_services.sh"
echo "3. Open http://localhost:5000 in your browser"
echo ""
echo "💡 For first-time users, we recommend option 1 (./run.sh)"
