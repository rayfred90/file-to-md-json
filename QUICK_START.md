# Document Converter - Quick Start Guide

## 📋 Prerequisites

Make sure you have Python 3.8+ installed. The startup script will automatically:
- ✅ Detect and activate existing virtual environment (`venv`, `my_env`, or `.venv`)
- ✅ Create a new virtual environment if none exists
- ✅ Install Python dependencies from `requirements.txt`

## 🚀 Starting the Services

To start both MinIO and Flask services:

```bash
./start_all.sh
```

This will:
- ✅ Set up and activate Python virtual environment
- ✅ Install dependencies (if needed)
- ✅ Start MinIO server on ports 9000 (API) and 9001 (Console)
- ✅ Start Flask application on port 5000
- ✅ Show you the status and URLs
- ✅ Keep running until you press Ctrl+C

**Access URLs:**
- **Web App**: http://localhost:5000
- **MinIO Console**: http://localhost:9001 (admin/password123)
- **MinIO API**: http://localhost:9000

## 🛑 Stopping the Services

To stop all services:

```bash
./stop_all.sh
```

Or press `Ctrl+C` while `start_all.sh` is running.

## 🧹 Cleaning Up Test Files

To remove all test files and temporary data:

```bash
./cleanup_tests.sh
```

This will clean up:
- Test files and logs
- Temporary session data
- Upload/output directories (but keep the folders)
- MinIO data
- Python cache files

## 📊 Features Available

✅ **File Upload** - Supports 25+ file formats  
✅ **Document Conversion** - Convert to Markdown or JSON  
✅ **Text Splitting** - Smart text chunking  
✅ **Session Management** - Isolated user sessions  
✅ **Cloud Storage** - MinIO object storage  
✅ **OCR Processing** - Extract text from images  

## 🔧 Manual Operations

**Start only MinIO:**
```bash
cd minio_storage && ./start-minio.sh
```

**Start only Flask (with virtual environment):**
```bash
source venv/bin/activate  # or my_env/bin/activate
python app.py
```

**Kill specific ports:**
```bash
# Kill Flask (port 5000)
lsof -ti:5000 | xargs kill -9

# Kill MinIO (ports 9000, 9001)
lsof -ti:9000 | xargs kill -9
lsof -ti:9001 | xargs kill -9
```

## 🚨 Troubleshooting

**Virtual Environment Issues:**
```bash
# Create virtual environment manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Flask Won't Start:**
```bash
# Check if virtual environment is activated
which python  # Should show path in venv/

# Install dependencies manually
pip install flask flask-cors minio python-pptx
```

**Port Already in Use:**
```bash
# Stop all services first
./stop_all.sh

# Or kill specific ports
sudo lsof -ti:5000 | xargs kill -9
```

## 📁 Project Structure

```
/home/adebo/con/
├── start_all.sh      # 🚀 Start all services
├── stop_all.sh       # 🛑 Stop all services  
├── cleanup_tests.sh  # 🧹 Clean test files
├── app.py           # 🌐 Flask application
├── static/          # 📱 Web interface
├── processors/      # 🔄 Document processors
├── minio_storage/   # 🗄️ MinIO configuration
└── uploads/         # 📁 File storage
```

Enjoy your document converter! 🎉
