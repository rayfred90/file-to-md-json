#!/bin/bash

# Document Converter - Test File Cleanup Script
# This script removes all test files and temporary data

echo "🧹 Cleaning up test files and temporary data..."
echo "=============================================="

# Set colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to safely remove files/directories
safe_remove() {
    local path=$1
    local description=$2
    
    if [ -e "$path" ]; then
        echo -e "${BLUE}🗑️  Removing $description...${NC}"
        rm -rf "$path"
        echo -e "${GREEN}✅ Removed: $path${NC}"
    else
        echo -e "${YELLOW}⚠️  Not found: $path${NC}"
    fi
}

# Function to remove files by pattern
remove_pattern() {
    local pattern=$1
    local description=$2
    
    echo -e "${BLUE}🔍 Looking for $description...${NC}"
    found_files=$(find . -name "$pattern" -type f 2>/dev/null | head -10)
    
    if [ -n "$found_files" ]; then
        echo "$found_files" | while read -r file; do
            echo -e "${BLUE}🗑️  Removing: $file${NC}"
            rm -f "$file"
        done
        echo -e "${GREEN}✅ Cleaned up $description${NC}"
    else
        echo -e "${YELLOW}⚠️  No $description found${NC}"
    fi
}

cd /home/adebo/con

echo -e "${BLUE}📁 Cleaning up test files...${NC}"

# Remove specific test files
safe_remove "test_document.txt" "test document"
safe_remove "downloaded_converted.md" "downloaded converted file"
safe_remove "downloaded_test.md" "downloaded test file" 
safe_remove "test_download.md" "test download file"
safe_remove "test_markdown.md" "test markdown file"
safe_remove "test_split_download.md" "test split download file"
safe_remove "test_ocr.py" "OCR test script"
safe_remove "test_python.py" "Python test script"
safe_remove "test_minio.py" "MinIO test script"
safe_remove "test_minio_login.py" "MinIO login test script"
safe_remove "test_flask_minio.py" "Flask MinIO test script"
safe_remove "simple_minio_test.py" "simple MinIO test script"
safe_remove "debug_minio.py" "MinIO debug script"

# Remove log files
echo -e "${BLUE}📄 Cleaning up log files...${NC}"
safe_remove "app.log" "application log"
safe_remove "flask_test.log" "Flask test log"
safe_remove "flask.log" "Flask log"
safe_remove "session_cookies.txt" "session cookies"

# Remove temporary directories and their contents
echo -e "${BLUE}📂 Cleaning up temporary directories...${NC}"
safe_remove "file_metadata" "file metadata directory"
safe_remove "conversion_metadata" "conversion metadata directory"
safe_remove "sessions" "sessions directory"

# Clean uploads directory but keep the folder
echo -e "${BLUE}📁 Cleaning uploads directory...${NC}"
if [ -d "uploads" ]; then
    find uploads -type f -name "*" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ Cleaned uploads directory${NC}"
fi

# Clean outputs directory but keep the folder  
echo -e "${BLUE}📁 Cleaning outputs directory...${NC}"
if [ -d "outputs" ]; then
    find outputs -type f -name "*" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ Cleaned outputs directory${NC}"
fi

# Remove Python cache files
echo -e "${BLUE}🐍 Cleaning Python cache files...${NC}"
remove_pattern "*.pyc" "Python cache files"
remove_pattern "__pycache__" "Python cache directories"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove any remaining temporary files
echo -e "${BLUE}🗂️  Cleaning temporary files...${NC}"
remove_pattern "*.tmp" "temporary files"
remove_pattern "*.temp" "temp files" 
remove_pattern "*.bak" "backup files"
remove_pattern ".DS_Store" "macOS system files"

# Clean MinIO data directory but keep structure
echo -e "${BLUE}🗄️  Cleaning MinIO data...${NC}"
if [ -d "minio/data" ]; then
    find minio/data -type f -name "*" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ Cleaned MinIO data directory${NC}"
fi

# Clean MinIO logs
if [ -d "minio_storage/logs" ]; then
    find minio_storage/logs -type f -name "*.log" -delete 2>/dev/null || true
    echo -e "${GREEN}✅ Cleaned MinIO logs${NC}"
fi

echo -e "${GREEN}"
echo "🎉 Cleanup completed successfully!"
echo "================================="
echo -e "${BLUE}📊 Cleanup Summary:${NC}"
echo -e "${GREEN}   ✅ Test files removed${NC}"
echo -e "${GREEN}   ✅ Log files removed${NC}"
echo -e "${GREEN}   ✅ Temporary data cleared${NC}"
echo -e "${GREEN}   ✅ Python cache cleared${NC}"
echo -e "${GREEN}   ✅ Upload/output directories cleaned${NC}"
echo -e "${GREEN}   ✅ MinIO data cleared${NC}"
echo ""
echo -e "${BLUE}📁 Preserved directories:${NC}"
echo "   • uploads/ (empty)"
echo "   • outputs/ (empty)" 
echo "   • minio_storage/ (structure preserved)"
echo "   • processors/ (source code)"
echo "   • static/ (web assets)"
echo -e "${NC}"
