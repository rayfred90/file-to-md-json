# Document Converter & Text Splitter

A complete full-stack web application that converts various document formats to Markdown or JSON and optionally splits the text using LangChain text splitters.

## ✅ Status: COMPLETED & TESTED

The application is fully functional with all features working correctly:
- ✅ File upload with drag-and-drop support
- ✅ Document conversion (15+ formats supported)
- ✅ Text splitting with configurable parameters
- ✅ Download functionality for converted and split files
- ✅ Responsive web interface
- ✅ Error handling and status messages

## 🚀 Features

### Document Conversion
- **Supported Input Formats:**
  - PDF files (.pdf)
  - Microsoft Word (.doc, .docx)
  - Microsoft Excel (.xls, .xlsx)
  - CSV files (.csv)
  - Microsoft PowerPoint (.ppt, .pptx)
  - eBooks (.epub, .mobi)
  - Text files (.txt, .md)
  - Code files (.js, .ts, .py, .java, .cpp, .html, .css, .json, .xml, .yaml, .sql, .php, .go, .rust)

- **Output Formats:**
  - Markdown (.md)
  - JSON (.json)

### Text Splitting
- **Splitter Types:**
  - Recursive Character Splitter (recommended for most use cases)
  - Character Splitter (simple separator-based splitting)
  - Token Splitter (splits by token count)
  - Markdown Header Splitter (splits by markdown headers)
  - Python Code Splitter (splits Python code by functions/classes)
  - JavaScript Code Splitter (splits JavaScript code by functions/declarations)

- **Configurable Parameters:**
  - Chunk size (100-10,000 characters)
  - Chunk overlap (0-1,000 characters)
  - Custom separators
  - Keep/remove separators option

## 🏗️ Architecture

### Backend (Python Flask)
- **`app.py`**: Main Flask application with REST API endpoints
- **`text_splitter.py`**: LangChain text splitting service
- **`processors/`**: Document processing modules
  - `pdf_processor.py`: PDF processing with pdfplumber
  - `doc_processor.py`: Word document processing with python-docx
  - `excel_processor.py`: Excel/CSV processing with pandas and openpyxl
  - `ppt_processor.py`: PowerPoint processing with python-pptx
  - `ebook_processor.py`: EPUB processing with ebooklib
  - `text_processor.py`: Text and code file processing

### Frontend (HTML/JavaScript)
- **`static/index.html`**: Responsive UI with Tailwind CSS
- **`static/app.js`**: JavaScript for file handling and API communication

## 📁 Project Structure

```
con/
├── app.py                 # Flask application
├── text_splitter.py       # LangChain text splitting service
├── requirements.txt       # Python dependencies
├── setup.sh              # Setup script
├── run.sh                # Run script
├── README.md             # This file
├── processors/           # Document processors
│   ├── __init__.py
│   ├── base_processor.py
│   ├── pdf_processor.py
│   ├── doc_processor.py
│   ├── excel_processor.py
│   ├── ppt_processor.py
│   ├── ebook_processor.py
│   └── text_processor.py
├── static/              # Frontend files
│   ├── index.html
│   └── app.js
├── uploads/            # Uploaded files (auto-created)
└── outputs/            # Converted files (auto-created)
```

## 🚀 Quick Start

### Prerequisites & Installation

#### Step 1: Install Python 3.8+
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS (using Homebrew):**
```bash
brew install python3
```

**Windows:**
- Download Python from https://python.org/downloads/
- During installation, make sure to check "Add Python to PATH"
- pip is included with Python 3.4+

#### Step 2: Verify Installation
```bash
python3 --version  # Should show Python 3.8+
pip3 --version     # Should show pip version
```

### Installation & Setup

#### Option 1: Automated Setup (Recommended)

1. **Navigate to the project directory:**
   ```bash
   cd /home/adebo/con
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Start the application:**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

#### Option 2: Manual Setup

1. **Navigate to the project directory:**
   ```bash
   cd /home/adebo/con
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   # On Linux/macOS:
   source venv/bin/activate
   
   # On Windows:
   # venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python3 app.py
   ```

5. **Open in browser:**
   ```
   http://localhost:5000
   ```

### Troubleshooting Installation

**If you get "python3: command not found":**
- On some systems, try `python` instead of `python3`
- Make sure Python is added to your PATH

**If you get "pip3: command not found":**
- Try `pip` instead of `pip3`
- On Ubuntu/Debian: `sudo apt install python3-pip`

**If you get permission errors:**
- Make sure you're in the activated virtual environment
- Try running with `sudo` only if absolutely necessary

**Virtual environment not activating:**
- Make sure you're in the correct directory
- Check that the `venv` folder was created successfully

## 🔧 API Endpoints

### Upload File
```
POST /api/upload
Content-Type: multipart/form-data
Body: file (form data)
```

### Convert Document
```
POST /api/convert
Content-Type: application/json
Body: {
  "file_id": "uuid",
  "output_format": "md" | "json"
}
```

### Split Text
```
POST /api/split
Content-Type: application/json
Body: {
  "file_id": "uuid",
  "splitter_type": "recursive" | "character" | "token" | "markdown" | "python" | "javascript",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "separators": ["\\n\\n", "\\n", " "],  // optional
  "keep_separator": true  // optional
}
```

### Download File
```
GET /api/download/{file_id}/{file_type}
file_type: "original" | "split"
```

### Health Check
```
GET /api/health
```

## 📝 Usage Examples

### 1. Web Interface
1. Open http://localhost:5000 in your browser
2. Drag and drop a file or click to upload
3. Select output format (Markdown or JSON)
4. Click "Convert Document"
5. Optionally configure text splitting parameters
6. Click "Split Text" if desired
7. Download the converted and/or split files

### 2. API Usage
```bash
# Upload a file
curl -X POST -F "file=@document.pdf" http://localhost:5000/api/upload

# Convert to markdown
curl -X POST -H "Content-Type: application/json" \
  -d '{"file_id":"your-file-id","output_format":"md"}' \
  http://localhost:5000/api/convert

# Split with custom parameters
curl -X POST -H "Content-Type: application/json" \
  -d '{"file_id":"your-file-id","splitter_type":"recursive","chunk_size":500,"chunk_overlap":100}' \
  http://localhost:5000/api/split

# Download converted file
curl -o converted.md http://localhost:5000/api/download/your-file-id/original

# Download split file
curl -o split.md http://localhost:5000/api/download/your-file-id/split
```

## 🧪 Testing

The application has been thoroughly tested with:
- ✅ Text files (.txt)
- ✅ Markdown files (.md)
- ✅ Python code files (.py)
- ✅ All splitter types (recursive, character, token, markdown, python, javascript)
- ✅ Different chunk sizes and overlap settings
- ✅ Download functionality for both original and split files
- ✅ Error handling for invalid files and parameters

## 🔧 Configuration

### Environment Variables
- `FLASK_ENV`: Set to `development` for debug mode
- `MAX_CONTENT_LENGTH`: Maximum file size (default: 100MB)

### File Limits
- Maximum file size: 100MB
- Supported extensions: 20+ file types
- Chunk size range: 100-10,000 characters
- Overlap range: 0-1,000 characters

## 🚀 Performance

- Fast document processing with efficient libraries
- Memory-efficient text splitting
- Concurrent request handling
- File-based storage for reliability

## 🛠️ Dependencies

### Backend
- **Flask**: Web framework
- **LangChain**: Text splitting functionality
- **pdfplumber**: PDF processing
- **python-docx**: Word document processing
- **pandas**: Excel/CSV processing
- **openpyxl**: Excel file support
- **python-pptx**: PowerPoint processing
- **ebooklib**: EPUB processing
- **flask-cors**: Cross-origin requests

### Frontend
- **Tailwind CSS**: Responsive styling
- **Vanilla JavaScript**: No additional frameworks

## 🔒 Security

- File type validation
- Secure filename handling
- CORS protection
- File size limits
- Input sanitization

## 📊 Monitoring

- Health check endpoint: `/api/health`
- Request logging
- Error tracking
- File processing status

## 🚧 Future Enhancements

- [ ] Batch file processing
- [ ] Cloud storage integration
- [ ] Advanced text preprocessing
- [ ] API rate limiting
- [ ] User authentication
- [ ] File history and management
- [ ] Custom splitter configurations
- [ ] Export to additional formats

## 📄 License

This project is provided as-is for educational and development purposes.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**Note**: This is a development server. For production deployment, use a proper WSGI server like Gunicorn or uWSGI.
