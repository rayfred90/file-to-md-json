# Document Converter - Troubleshooting Guide

## 🚨 Common Issues & Solutions

### 1. "python: command not found"

**Problem**: The system is looking for `python` but only `python3` is available.

**Solution**:
```bash
# Check what's available
python3 --version
which python3

# If python3 works, the app should work fine
# This is already fixed in the latest version
```

### 2. "No module named 'flask'" or similar import errors

**Problem**: Dependencies not installed or virtual environment not activated.

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Or run setup again
./setup.sh
```

### 3. MinIO connection errors

**Problem**: MinIO server not running or configured incorrectly.

**Solution**:
```bash
# Check if MinIO is needed
# Edit .env file:
STORAGE_MODE=LOCAL

# Or start MinIO server:
./start_services.sh
```

### 4. Port 5000 already in use

**Problem**: Another application is using port 5000.

**Solution**:
```bash
# Kill the process using port 5000
lsof -ti:5000 | xargs kill -9

# Or use a different port
# Edit app.py and change port=5000 to port=5001
```

### 5. Permission denied errors

**Problem**: Scripts don't have execute permissions.

**Solution**:
```bash
# Make scripts executable
chmod +x install.sh setup.sh run.sh

# Or run with bash
bash install.sh
```

### 6. Virtual environment creation fails

**Problem**: `python3 -m venv` not working.

**Solution**:
```bash
# Install venv module
# Ubuntu/Debian:
sudo apt install python3-venv

# CentOS/RHEL:
sudo yum install python3-venv

# Or use pip
pip3 install virtualenv
python3 -m virtualenv venv
```

### 7. "ModuleNotFoundError: No module named 'pyarrow'"

**Problem**: Missing pyarrow dependency (pandas warning).

**Solution**:
```bash
# Install pyarrow
pip install pyarrow

# Or reinstall all dependencies
pip install -r requirements.txt
```

## 🔧 System Requirements

### Minimum Requirements
- Python 3.8+
- pip (Python package manager)
- 1GB RAM
- 1GB disk space

### Recommended Requirements
- Python 3.9+
- 2GB RAM
- 2GB disk space
- Virtual environment support

## 🐛 Getting Help

### Before Asking for Help
1. Check this troubleshooting guide
2. Make sure you're using the latest version
3. Try the simple installation: `./install.sh`
4. Check the logs for error messages

### What to Include in Bug Reports
- Operating system (Ubuntu, CentOS, macOS, etc.)
- Python version (`python3 --version`)
- Complete error message
- Steps to reproduce the issue
- Any modifications you made to the code

### Quick Diagnostics
```bash
# Check Python
python3 --version

# Check pip
pip3 --version

# Check virtual environment
which python  # Should show venv path if activated

# Check port usage
lsof -i :5000

# Check app status
curl -s http://localhost:5000/ | head -10
```

## 🎯 Known Limitations

1. **Large File Processing**: Files over 100MB may take longer to process
2. **OCR Processing**: Requires pytesseract and tesseract-ocr for image text extraction
3. **Complex Documents**: Some complex formatting may not convert perfectly
4. **Browser Compatibility**: Best experience with modern browsers (Chrome, Firefox, Safari)

## 📞 Support

For additional help:
1. Check the README.md file
2. Review the QUICK_START.md guide
3. Look through the code comments
4. Check the project's issue tracker (if available)

Remember: The app is designed to work out of the box with minimal configuration! 🚀
