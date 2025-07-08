#!/bin/bash

# Document Converter Setup Script

echo "🚀 Setting up Document Converter & Text Splitter..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect package manager
detect_package_manager() {
    if command_exists apt-get; then
        echo "apt"
    elif command_exists yum; then
        echo "yum"
    elif command_exists dnf; then
        echo "dnf"
    elif command_exists brew; then
        echo "brew"
    elif command_exists pacman; then
        echo "pacman"
    else
        echo "unknown"
    fi
}

# ===== System Dependencies (Python3 & pip3) =====
echo "🔎 Checking for Python 3 and pip3..."

if ! command_exists python3; then
    echo "❌ Python 3 not found. Installing Python 3..."
    pkg_manager=$(detect_package_manager)
    
    case $pkg_manager in
        "apt")
            sudo apt-get update
            sudo apt-get install -y python3 python3-venv
            ;;
        "yum")
            sudo yum install -y python3 python3-venv
            ;;
        "dnf")
            sudo dnf install -y python3 python3-venv
            ;;
        "brew")
            brew install python3
            ;;
        "pacman")
            sudo pacman -S python3
            ;;
        *)
            echo "❌ Unsupported package manager. Please install Python 3.8+ manually."
            echo "Visit: https://www.python.org/downloads/"
            exit 1
            ;;
    esac
fi

if ! command_exists pip3; then
    echo "❌ pip3 not found. Installing pip3..."
    pkg_manager=$(detect_package_manager)
    
    case $pkg_manager in
        "apt")
            sudo apt-get install -y python3-pip
            ;;
        "yum")
            sudo yum install -y python3-pip
            ;;
        "dnf")
            sudo dnf install -y python3-pip
            ;;
        "brew")
            # pip3 should already be installed with python3 on macOS
            if ! command_exists pip3; then
                echo "❌ pip3 still not found. Please install manually."
                exit 1
            fi
            ;;
        "pacman")
            sudo pacman -S python-pip
            ;;
        *)
            echo "❌ Unsupported package manager. Please install pip3 manually."
            exit 1
            ;;
    esac
fi

# Display Python version
python_version=$(python3 --version)
echo "✅ Found $python_version"
pip_version=$(pip3 --version)
echo "✅ Found $pip_version"

# ===== MinIO Installation (Optional) =====
echo "🔎 Checking for MinIO components..."

# Check if MinIO server is needed (only install if start_services.sh exists)
if [ -f "start_services.sh" ]; then
    # Install MinIO server if not already installed
    if ! command_exists minio; then
        echo "📥 Downloading MinIO server binary..."
        
        # Detect architecture
        arch=$(uname -m)
        case $arch in
            "x86_64")
                arch_suffix="amd64"
                ;;
            "aarch64"|"arm64")
                arch_suffix="arm64"
                ;;
            *)
                echo "❌ Unsupported architecture: $arch"
                echo "Please install MinIO manually from https://min.io/download"
                exit 1
                ;;
        esac
        
        # Download MinIO server
        if command_exists wget; then
            wget -q "https://dl.min.io/server/minio/release/linux-${arch_suffix}/minio" -O minio
        elif command_exists curl; then
            curl -s "https://dl.min.io/server/minio/release/linux-${arch_suffix}/minio" -o minio
        else
            echo "❌ wget or curl is required to download MinIO."
            exit 1
        fi
        
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
        
        # Use same architecture detection as above
        if command_exists wget; then
            wget -q "https://dl.min.io/client/mc/release/linux-${arch_suffix}/mc" -O mc
        elif command_exists curl; then
            curl -s "https://dl.min.io/client/mc/release/linux-${arch_suffix}/mc" -o mc
        else
            echo "❌ wget or curl is required to download MinIO client."
            exit 1
        fi
        
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
else
    echo "ℹ️  Skipping MinIO installation (start_services.sh not found)"
fi

# ===== Python Virtual Environment =====
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

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment."
        echo "💡 Try: sudo apt-get install python3-venv (on Ubuntu/Debian)"
        exit 1
    fi
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔄 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "🚀 Quick Start Options:"
    echo "1. Simple start (local storage):   ./run.sh"
    
    # Only show MinIO option if services script exists
    if [ -f "start_services.sh" ]; then
        echo "2. Full start (with MinIO):        ./start_services.sh"
    fi
    
    echo "3. Open http://localhost:5000 in your browser"
    echo ""
    echo "💡 For first-time users, we recommend option 1 (./run.sh)"
    echo ""
    echo "🔧 To activate the virtual environment manually:"
    echo "   source venv/bin/activate"
else
    echo "❌ Failed to install dependencies."
    echo "Please check the error messages above and try again."
    echo ""
    echo "💡 Common fixes:"
    echo "   - Ensure you have internet connection"
    echo "   - Try: pip install --upgrade pip"
    echo "   - Check if all system dependencies are installed"
    exit 1
fi
