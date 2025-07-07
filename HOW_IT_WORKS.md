# How the File-to-MD-JSON Agent Works

## Overview

The File-to-MD-JSON agent is a comprehensive full-stack web application that converts various document formats to Markdown or JSON and provides advanced text splitting capabilities using LangChain. This document explains the architecture, workflow, and key components of the system.

![Agent Interface](https://github.com/user-attachments/assets/c8085b72-3070-47fd-b04e-c4e764353706)

## Architecture Overview

### Backend Components (Python Flask)

#### 1. **Main Application (`app.py`)**
- **Flask REST API**: Provides endpoints for file upload, conversion, splitting, and download
- **Session Management**: Handles user sessions for file isolation without requiring user registration
- **Progress Tracking**: Real-time progress updates during document processing
- **Storage Abstraction**: Supports both local storage and cloud storage (MinIO) modes

#### 2. **Document Processors (`processors/`)**
The system uses a modular processor architecture to handle different document types:

- **`PDFProcessor`**: Processes PDF files using `pdfplumber` and `PyMuPDF`
- **`DocProcessor`**: Handles Word documents (.doc, .docx) using `python-docx`
- **`ExcelProcessor`**: Processes Excel/CSV files using `pandas` and `openpyxl`
- **`PPTProcessor`**: Handles PowerPoint files using `python-pptx`
- **`TextProcessor`**: Processes text and code files directly
- **`EbookProcessor`**: Handles EPUB/MOBI files (temporarily disabled)
- **`OCRProcessor`**: Extracts text from images using Tesseract (temporarily disabled)

#### 3. **Text Splitting Service (`text_splitter.py`)**
Leverages LangChain's text splitting capabilities:

- **Recursive Character Splitter**: Splits text hierarchically (recommended)
- **Character Splitter**: Simple separator-based splitting
- **Token Splitter**: Splits by token count
- **Markdown Header Splitter**: Splits by markdown headers
- **Python/JavaScript Code Splitters**: Language-specific splitting

#### 4. **File Management**
- **`LocalFileManager`**: Handles local file storage with session isolation
- **`MinIOService`**: Manages cloud storage using MinIO (S3-compatible)
- **`SessionService`**: Provides session-based file isolation without user accounts

### Frontend Components (JavaScript/HTML)

#### 1. **User Interface (`static/index.html`)**
- **Responsive Design**: Built with Tailwind CSS for modern, mobile-friendly interface
- **Step-by-Step Workflow**: Guided 4-step process for document processing
- **Real-time Updates**: Progress bars and status messages
- **Drag-and-Drop Upload**: Intuitive file upload interface

#### 2. **Application Logic (`static/app.js`)**
- **DocumentConverter Class**: Main JavaScript class handling all frontend logic
- **File Upload**: Handles drag-and-drop and file selection with progress tracking
- **API Communication**: Manages REST API calls with error handling
- **Progress Polling**: Real-time updates during document processing
- **Download Management**: Handles file downloads for processed documents

#### 3. **File Manager (`static/file-manager.html`)**
- **File Organization**: View and manage uploaded/processed files
- **Folder Structure**: Groups files by conversion sessions
- **File Operations**: Download, delete, and organize files

## Workflow Explanation

### Step 1: File Upload
1. User selects or drags a file to the upload area
2. JavaScript validates file type and size
3. File is uploaded via `POST /api/upload` with progress tracking
4. Server stores file in session-isolated directory (local) or cloud bucket (MinIO)
5. File metadata is saved and unique file ID is returned

### Step 2: Document Conversion
1. User selects output format (Markdown or JSON)
2. Conversion request sent to `POST /api/convert` with file ID and format
3. Server retrieves file and selects appropriate processor based on file extension
4. Processor extracts content from document:
   - **PDF**: Text extraction with layout preservation
   - **Word**: Document structure and formatting
   - **Excel**: Table data with metadata
   - **PowerPoint**: Slide content and notes
   - **Text/Code**: Direct content reading
5. Content is formatted as Markdown or JSON
6. Processed file is saved and available for download

### Step 3: Text Splitting (Optional)
1. User configures splitting parameters:
   - **Splitter Type**: Choose from 6 different splitting strategies
   - **Chunk Size**: Set character limit per chunk (100-10,000)
   - **Chunk Overlap**: Set overlap between chunks (0-1,000)
   - **Custom Separators**: Define custom splitting delimiters
2. Request sent to `POST /api/split` with configuration
3. Server retrieves converted content and applies LangChain text splitter
4. Text is split into chunks according to specified parameters
5. Split chunks are saved as downloadable file

### Step 4: Download Results
1. User can download converted document via `GET /api/download/{file_id}/original`
2. User can download split chunks via `GET /api/download/{file_id}/split`
3. Files are served with appropriate MIME types and filenames

## Key Features

### 1. **Multi-Format Support**
- **Documents**: PDF, Word (.doc, .docx), Excel (.xls, .xlsx, .csv), PowerPoint (.ppt, .pptx)
- **Text Files**: Plain text (.txt), Markdown (.md)
- **Code Files**: JavaScript, TypeScript, Python, Java, C++, HTML, CSS, JSON, XML, YAML, SQL, PHP, Go, Rust
- **eBooks**: EPUB, MOBI (when ebooklib is available)
- **Images**: PNG, JPG, JPEG, TIFF, BMP, GIF, WebP (with OCR when tesseract is available)

### 2. **Flexible Output Formats**
- **Markdown**: Preserves document structure with headers, lists, and formatting
- **JSON**: Structured data format with metadata and content organization

### 3. **Advanced Text Splitting**
- **Multiple Strategies**: 6 different splitting algorithms optimized for different use cases
- **Configurable Parameters**: Customizable chunk size, overlap, and separators
- **LangChain Integration**: Leverages industry-standard text processing library

### 4. **Session Management**
- **No User Registration**: Anonymous sessions for privacy
- **File Isolation**: Each session has isolated file storage
- **Automatic Cleanup**: Sessions expire after 24 hours

### 5. **Storage Flexibility**
- **Local Mode**: Files stored on server filesystem
- **Cloud Mode**: Files stored in MinIO (S3-compatible) buckets
- **Automatic Fallback**: Gracefully switches to local mode if cloud storage unavailable

### 6. **Real-time Progress Tracking**
- **Upload Progress**: Real-time upload speed and ETA
- **Conversion Progress**: Step-by-step processing updates
- **Error Handling**: Comprehensive error messages and recovery options

## API Endpoints

### File Operations
- `POST /api/upload` - Upload a file
- `POST /api/convert` - Convert uploaded file to Markdown/JSON
- `POST /api/split` - Split converted text into chunks
- `GET /api/download/{file_id}/{type}` - Download processed files
- `GET /api/progress/{file_id}` - Get conversion progress

### System
- `GET /api/health` - Health check endpoint
- `GET /` - Main application interface
- `GET /static/file-manager.html` - File management interface

## Configuration

### Environment Variables
- `FLASK_ENV`: Set to 'development' or 'production'
- `SECRET_KEY`: Flask session secret key
- `MAX_CONTENT_LENGTH`: Maximum file upload size (default: 100MB)
- `MINIO_ENDPOINT`: MinIO server endpoint (optional)
- `MINIO_ACCESS_KEY`: MinIO access key (optional)
- `MINIO_SECRET_KEY`: MinIO secret key (optional)

### Storage Modes
- **Local Mode**: When MinIO configuration is not provided
- **Cloud Mode**: When MinIO credentials are configured and server is available

## Technical Implementation Details

### Session Isolation
Each user session gets a unique UUID-based identifier that isolates their files from other users. This provides privacy without requiring user registration.

### Progress Tracking System
The application uses a background polling system to provide real-time updates during long-running operations like PDF processing.

### Error Handling
Comprehensive error handling at multiple levels:
- Frontend validation for file types and sizes
- Backend processing error recovery
- User-friendly error messages with actionable guidance

### Scalability Considerations
- Stateless session management allows horizontal scaling
- Cloud storage support enables distributed file handling
- Modular processor architecture allows easy extension

## Testing and Validation

The application has been tested with:
- ✅ File upload with drag-and-drop interface
- ✅ Document conversion (text files successfully tested)
- ✅ Progress tracking and status updates
- ✅ Error handling and recovery
- ✅ Local storage mode functionality
- ✅ Session isolation and management

![Working Application](https://github.com/user-attachments/assets/4d895da1-02a8-411b-b3b9-824a24703e9b)

## Future Enhancements

The architecture supports easy extension for:
- Additional document processors
- New text splitting strategies
- Enhanced cloud storage options
- Batch processing capabilities
- API rate limiting and authentication
- Advanced file management features

## Conclusion

The File-to-MD-JSON agent provides a robust, scalable solution for document processing with a clean separation of concerns, comprehensive error handling, and flexible deployment options. The modular architecture makes it easy to extend and maintain while providing a smooth user experience through its intuitive web interface.