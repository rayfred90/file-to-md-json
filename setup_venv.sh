#!/bin/bash

# Document Converter - Virtual Environment Setup Script
# This script creates and sets up the Python virtual environment

echo "🐍 Setting up Python Virtual Environment"
echo "========================================"

# Set colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}🔍 Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo "Please install Python 3.8+ before continuing"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment 'venv' already exists${NC}"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🗑️  Removing existing virtual environment...${NC}"
        rm -rf venv
    else
        echo -e "${BLUE}📦 Using existing virtual environment${NC}"
        source venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
        
        # Check if requirements are installed
        if [ -f "requirements.txt" ]; then
            echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
            pip install -r requirements.txt --quiet
            echo -e "${GREEN}✅ Dependencies verified/installed${NC}"
        fi
        
        echo -e "${GREEN}🎉 Setup complete! You can now run: ./start_all.sh${NC}"
        exit 0
    fi
fi

# Create new virtual environment
echo -e "${BLUE}📦 Creating virtual environment...${NC}"
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Failed to create virtual environment${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment created${NC}"

# Activate virtual environment
echo -e "${BLUE}🔌 Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Upgrade pip
echo -e "${BLUE}⬆️  Upgrading pip...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}✅ Pip upgraded${NC}"

# Install requirements
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  No requirements.txt found${NC}"
    echo -e "${BLUE}📦 Installing basic dependencies...${NC}"
    pip install flask flask-cors minio python-pptx python-docx openpyxl ebooklib pytesseract Pillow
    echo -e "${GREEN}✅ Basic dependencies installed${NC}"
fi

echo -e "${GREEN}"
echo "🎉 Virtual Environment Setup Complete!"
echo "====================================="
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Run: ./start_all.sh (to start all services)"
echo "2. Or manually activate: source venv/bin/activate"
echo "3. Then run: python app.py"
echo ""
echo -e "${BLUE}🌐 Once started, access your app at: http://localhost:5000${NC}"
echo -e "${NC}"
