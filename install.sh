#!/bin/bash

# Document Converter - Simple Installation Script
# This script provides the easiest way to get started

echo "🚀 Document Converter - Simple Installation"
echo "=========================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
echo "🔍 Checking system requirements..."

# Check Python
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed."
    echo ""
    echo "Please install Python 3.8+ first:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

# Check pip
if ! command_exists pip3; then
    echo "❌ pip3 is required but not installed."
    echo ""
    echo "Please install pip3:"
    echo "  Ubuntu/Debian: sudo apt install python3-pip"
    echo "  CentOS/RHEL: sudo yum install python3-pip"
    exit 1
fi

python_version=$(python3 --version)
echo "✅ Found $python_version"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        cp .env.default .env
    fi
    echo "✅ Created .env file with default settings"
fi

# Run setup
echo "🔧 Running setup..."
chmod +x setup.sh
./setup.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation Complete!"
    echo "========================"
    echo ""
    echo "🚀 To start the application:"
    echo "   ./run.sh"
    echo ""
    echo "📱 Then open http://localhost:5000 in your browser"
    echo ""
    echo "💡 Tips:"
    echo "   - The app uses local file storage by default"
    echo "   - Upload files and convert them to Markdown or JSON"
    echo "   - Use text splitting for large documents"
    echo ""
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
