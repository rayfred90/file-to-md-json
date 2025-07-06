# Changelog

All notable changes to the Document Converter & Text Splitter project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-07-06

### 🐛 Bug Fixes
- **Fixed JSON Serialization Error for Excel Files with Timestamps**
  - Resolved "Object of type Timestamp is not JSON serializable" error when converting Excel files containing date/time columns
  - Added `CustomJSONEncoder` class to handle pandas Timestamp objects, datetime objects, and numpy data types
  - Updated all JSON serialization points throughout the application (`app.py`, `minio_storage/minio_service.py`)
  - Enhanced Excel processor to preprocess datetime columns before JSON conversion
  - Timestamps are now converted to ISO format strings (e.g., "2023-01-01T12:00:00")

### 🔧 Technical Improvements
- **Enhanced Data Type Handling**
  - Added support for pandas NaT (Not a Time) values → converted to `null` in JSON
  - Added support for numpy integer/float types → converted to native Python types
  - Added support for numpy arrays → converted to Python lists
  - Added support for timezone-aware timestamps

### ✅ Testing
- Created comprehensive test suite for timestamp handling
- Verified Excel files with various date/time formats convert successfully
- Tested edge cases including NaT values and timezone-aware timestamps
- Validated both JSON and Markdown output formats

### 📋 Files Modified
- `app.py`: Added CustomJSONEncoder and updated JSON serialization calls
- `processors/excel_processor.py`: Enhanced timestamp preprocessing
- `minio_storage/minio_service.py`: Updated metadata serialization

## [1.0.0] - 2025-06-02

### 🎉 Initial Release

#### Added
- **Document Conversion System**
  - Support for 15+ file formats (PDF, Word, Excel, PowerPoint, EPUB, text, code files)
  - Conversion to Markdown (.md) and JSON (.json) formats
  - Modular processor architecture with dedicated handlers for each file type

- **LangChain Text Splitting**
  - 6 different splitter types: Recursive Character, Character, Token, Markdown Header, Python Code, JavaScript Code
  - Configurable parameters: chunk size (100-10,000), chunk overlap (0-1,000)
  - Custom separator support and keep/remove separator options

- **Web Interface**
  - Responsive design with Tailwind CSS
  - Drag-and-drop file upload with visual feedback
  - Real-time status updates and progress indicators
  - Download functionality for converted and split files
  - Error handling with user-friendly messages

- **REST API**
  - Complete RESTful API with JSON responses
  - Endpoints: `/api/upload`, `/api/convert`, `/api/split`, `/api/download`, `/api/health`
  - CORS support for cross-origin requests
  - Comprehensive error handling and validation

- **Backend Architecture**
  - Flask web framework with modular design
  - Document processors: PDF (pdfplumber), Word (python-docx), Excel (pandas/openpyxl), PowerPoint (python-pptx), EPUB (ebooklib)
  - Text processor for code files and plain text
  - File-based storage system with organized uploads/outputs directories

- **Development Tools**
  - Setup script (`setup.sh`) for automated environment configuration
  - Run script (`run.sh`) for easy application startup
  - Comprehensive requirements.txt with all dependencies
  - Detailed README with usage examples and API documentation

#### Features
- **File Upload**: Drag-and-drop interface supporting 20+ file extensions
- **Document Processing**: Intelligent content extraction from various document formats
- **Text Splitting**: Advanced text chunking using LangChain with multiple algorithms
- **Download System**: Separate downloads for original converted files and split versions
- **Security**: File type validation, secure filename handling, file size limits (100MB)
- **Performance**: Memory-efficient processing, concurrent request handling

#### Technical Specifications
- **Backend**: Python 3.8+, Flask, LangChain
- **Frontend**: HTML5, Tailwind CSS, Vanilla JavaScript
- **Dependencies**: 15+ specialized libraries for document processing
- **Storage**: File-based system with automatic directory creation
- **API**: RESTful with JSON responses and proper HTTP status codes

#### Supported File Formats
**Input**: PDF, DOC, DOCX, XLS, XLSX, CSV, PPT, PPTX, EPUB, MOBI, TXT, MD, JS, TS, PY, JAVA, CPP, HTML, CSS, JSON, XML, YAML, SQL, PHP, GO, RUST

**Output**: Markdown (.md), JSON (.json)

#### Testing
- ✅ Complete workflow testing (upload → convert → split → download)
- ✅ Multiple file format validation
- ✅ All text splitter types verified
- ✅ API endpoint functionality confirmed
- ✅ Error handling and edge cases covered

### 🔧 Technical Details
- **Architecture**: Clean separation between frontend, API, and processing layers
- **Error Handling**: Comprehensive error catching with user-friendly messages
- **Logging**: Request logging and error tracking
- **Configuration**: Environment-based configuration with sensible defaults

### 📋 Requirements
- Python 3.8 or higher
- pip package manager
- Modern web browser for frontend interface

### 🚀 Installation
```bash
git clone <repository-url>
cd document-converter
chmod +x setup.sh && ./setup.sh
chmod +x run.sh && ./run.sh
```

### 🌐 Access
- Web Interface: http://localhost:5000
- API Base URL: http://localhost:5000/api
- Health Check: http://localhost:5000/api/health
