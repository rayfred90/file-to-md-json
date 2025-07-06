import os
import json
import io
import glob
import tempfile
import uuid
import threading
import time
from io import BytesIO
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, send_file, send_from_directory, session
from flask_cors import CORS
import tempfile
import uuid
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import numpy as np

# Custom JSON encoder to handle pandas Timestamp and other non-serializable types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super().default(obj)

# Document processors
from processors.pdf_processor import PDFProcessor
from processors.doc_processor import DocProcessor
from processors.excel_processor import ExcelProcessor
from processors.ppt_processor import PPTProcessor
from processors.ebook_processor import EbookProcessor
from processors.text_processor import TextProcessor
from processors.ocr_processor import OCRProcessor

# Text splitter
from text_splitter import TextSplitterService

# MinIO service
from minio_storage.minio_service import MinIOService
from config import Config

# Session and file management services
from session_service import SessionService
from local_file_manager import LocalFileManager

app = Flask(__name__, static_folder='static')
CORS(app)

# Configure Flask session for session management
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Load configuration
config = Config()

# Progress tracking
progress_store = {}
progress_lock = threading.Lock()

def update_progress(session_id: str, file_id: str, percentage: int, message: str):
    """Update progress for a conversion task"""
    with progress_lock:
        key = f"{session_id}:{file_id}"
        progress_store[key] = {
            'percentage': percentage,
            'message': message,
            'timestamp': time.time()
        }

def get_progress(session_id: str, file_id: str) -> dict:
    """Get progress for a conversion task"""
    with progress_lock:
        key = f"{session_id}:{file_id}"
        return progress_store.get(key, {'percentage': 0, 'message': 'Starting...', 'timestamp': time.time()})

def cleanup_old_progress():
    """Clean up old progress entries (older than 1 hour)"""
    with progress_lock:
        current_time = time.time()
        keys_to_remove = []
        for key, data in progress_store.items():
            if current_time - data['timestamp'] > 3600:  # 1 hour
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del progress_store[key]

# Start cleanup thread
def start_cleanup_thread():
    def cleanup_worker():
        while True:
            time.sleep(300)  # Clean up every 5 minutes
            cleanup_old_progress()
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

start_cleanup_thread()

# Configuration
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 
    'ppt', 'pptx', 'epub', 'mobi', 'txt', 'md',
    'js', 'ts', 'py', 'java', 'cpp', 'html', 'css', 
    'json', 'xml', 'yaml', 'sql', 'php', 'go', 'rust',
    'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'gif', 'webp'
}

app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Initialize MinIO service
try:
    # Check if we have valid MinIO configuration
    if config.MINIO_ENDPOINT:
        minio_service = MinIOService()
        print("✅ MinIO service initialized successfully")
        print(f"🗄️  MinIO endpoint: {config.MINIO_ENDPOINT}")
    else:
        print("⚠️  MinIO configuration not found - running in local mode")
        print("   Please configure .env file with your MinIO credentials for cloud storage")
        minio_service = None
except Exception as e:
    print(f"❌ Failed to initialize MinIO service: {e}")
    print("   Running in local mode - files will be stored locally")
    minio_service = None

# Initialize session service and local file manager
session_service = SessionService()
local_file_manager = LocalFileManager()

# Storage mode detection
STORAGE_MODE = "cloud" if minio_service else "local"
print(f"🗄️  Storage mode: {STORAGE_MODE.upper()}")

# For backward compatibility during transition - keep local folders for fallback
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize processors
processors = {
    'pdf': PDFProcessor(),
    'doc': DocProcessor(),
    'docx': DocProcessor(),
    'xls': ExcelProcessor(),
    'xlsx': ExcelProcessor(),
    'csv': ExcelProcessor(),
    'ppt': PPTProcessor(),
    'pptx': PPTProcessor(),
    'epub': EbookProcessor(),
    'mobi': EbookProcessor(),
    'txt': TextProcessor(),
    'md': TextProcessor(),
    'js': TextProcessor(),
    'ts': TextProcessor(),
    'py': TextProcessor(),
    'java': TextProcessor(),
    'cpp': TextProcessor(),
    'html': TextProcessor(),
    'css': TextProcessor(),
    'json': TextProcessor(),
    'xml': TextProcessor(),
    'yaml': TextProcessor(),
    'sql': TextProcessor(),
    'php': TextProcessor(),
    'go': TextProcessor(),
    'rust': TextProcessor(),
    'png': OCRProcessor(),
    'jpg': OCRProcessor(),
    'jpeg': OCRProcessor(),
    'tiff': OCRProcessor(),
    'tif': OCRProcessor(),
    'bmp': OCRProcessor(),
    'gif': OCRProcessor(),
    'webp': OCRProcessor()
}

text_splitter_service = TextSplitterService()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/progress/<file_id>', methods=['GET'])
def get_conversion_progress(file_id):
    """Get the progress of a conversion task"""
    try:
        # Get current session (for progress tracking compatibility)
        session_id = session_service.get_session_id()
        if not session_id:
            # Create a temporary session for progress tracking
            session_id = session_service.get_or_create_session_id()
        
        progress = get_progress(session_id, file_id)
        return jsonify(progress)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        # Get or create session
        session_id = session_service.get_or_create_session_id()
        
        # Read file content
        file_content = file.read()
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if minio_service:
            # MinIO mode - upload to cloud storage (no session isolation)
            success, file_id, storage_path = minio_service.upload_file(
                file_content=file_content,
                file_name=filename,
                user_id=None  # Remove session isolation - store files globally
            )
            
            if not success:
                return jsonify({'error': f'Upload failed: {file_id}'}), 500
            
            # Create metadata record (MinIO doesn't have database, so we'll store metadata in file_metadata)
            file_size = len(file_content)
            success_db, error_msg = minio_service.create_file_record(
                file_id=file_id,
                original_name=filename,
                storage_path=storage_path,
                file_size=file_size,
                user_id=None  # Remove session isolation - store metadata globally
            )
            
            if not success_db:
                # Clean up uploaded file if metadata record creation fails
                minio_service.delete_file(storage_path)
                return jsonify({'error': f'Metadata error: {error_msg}'}), 500
            
            return jsonify({
                'file_id': file_id,
                'filename': filename,
                'file_type': file_extension,
                'storage_path': storage_path,
                'file_size': file_size,
                'storage_mode': 'minio',
                'session_id': None,  # Remove session tracking
                'message': 'File uploaded successfully to MinIO storage'
            })
        else:
            # Local mode - save using local file manager with session isolation
            success, file_id, file_path = local_file_manager.save_file(
                file_content=file_content,
                filename=filename,
                session_id=session_id
            )
            
            if not success:
                return jsonify({'error': f'Upload failed: {file_id}'}), 500
            
            return jsonify({
                'file_id': file_id,
                'filename': filename,
                'file_type': file_extension,
                'storage_path': file_path,
                'file_size': len(file_content),
                'storage_mode': 'local',
                'session_id': session_id,
                'message': 'File uploaded successfully to local storage'
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert', methods=['POST'])
def convert_file():
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        output_format = data.get('output_format', 'md')  # 'md' or 'json'
        
        if not file_id:
            return jsonify({'error': 'No file_id provided'}), 400
        
        # Get current session
        session_id = session_service.get_session_id()
        # Note: Keeping session for local mode compatibility, but removing session filtering for MinIO mode
        
        if minio_service:
            # MinIO mode - get file from cloud storage (no session filtering)
            success, file_record, error_msg = minio_service.get_file_record(file_id)
            if not success:
                return jsonify({'error': f'File not found: {error_msg}'}), 404
            
            # Remove session verification - allow access to any file
            # if file_record['user_id'] != session_id:
            #     return jsonify({'error': 'File not found in current session'}), 404
            
            # Download file from Supabase Storage
            success, file_content, error_msg = minio_service.download_file(file_record['file_path'])
            if not success:
                return jsonify({'error': f'Failed to download file: {error_msg}'}), 500
            
            file_extension = file_record['file_type']
            filename = file_record['original_name']
            
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                temp_file.write(file_content)
                temp_filepath = temp_file.name
                
        else:
            # Local mode - get file using local file manager
            success, file_metadata, error_msg = local_file_manager.get_file_metadata(file_id, session_id)
            if not success:
                return jsonify({'error': f'File not found: {error_msg}'}), 404
            
            # Get file path and verify it exists
            temp_filepath = file_metadata['file_path']
            if not os.path.exists(temp_filepath):
                return jsonify({'error': 'File not found on disk'}), 404
            
            file_extension = file_metadata['file_type']
            filename = file_metadata['original_name']
        
        try:
            # Initialize progress
            update_progress(session_id, file_id, 0, "Starting conversion...")
            
            # Process file based on extension
            processor = processors.get(file_extension)
            if not processor:
                return jsonify({'error': f'No processor found for {file_extension}'}), 400
            
            # Set up progress callback for PDF processor
            if file_extension == 'pdf' and hasattr(processor, 'set_progress_callback'):
                def progress_callback(percentage: int, message: str):
                    update_progress(session_id, file_id, percentage, message)
                processor.set_progress_callback(progress_callback)
            else:
                update_progress(session_id, file_id, 20, "Processing document...")
            
            # Convert to text/structured data
            content = processor.process(temp_filepath)
            
            update_progress(session_id, file_id, 90, "Formatting output...")
            
            # Format output
            if output_format == 'json':
                output_content = json.dumps(content, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
                output_filename = f"{file_id}.json"
                output_extension = 'json'
            else:  # markdown
                if isinstance(content, dict):
                    output_content = processor.to_markdown(content)
                else:
                    output_content = str(content)
                output_filename = f"{file_id}.md"
                output_extension = 'md'
            
            update_progress(session_id, file_id, 95, "Saving converted file...")
            
            if minio_service:
                # NEW: Enhanced folder-based conversion system for outputs bucket
                update_progress(session_id, file_id, 96, "Creating conversion folder...")
                
                # Create conversion folder (ALWAYS use folders for ALL conversions)
                folder_id = minio_service.create_conversion_folder(
                    file_id=file_id,
                    original_filename=filename,
                    session_id=session_id
                )
                
                if not folder_id:
                    return jsonify({'error': 'Failed to create conversion folder'}), 500
                
                # Extract images and other content
                images = content.get('images', []) if isinstance(content, dict) else []
                tables = content.get('tables', []) if isinstance(content, dict) else []
                
                update_progress(session_id, file_id, 97, "Saving converted files to folder...")
                
                # Save markdown version
                md_success, md_path = minio_service.add_file_to_conversion_folder(
                    folder_id=folder_id,
                    file_content=output_content.encode('utf-8'),
                    filename='converted.md',
                    file_type='markdown'
                )
                
                # Save JSON version
                json_content = json.dumps(content, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
                json_success, json_path = minio_service.add_file_to_conversion_folder(
                    folder_id=folder_id,
                    file_content=json_content.encode('utf-8'),
                    filename='converted.json',
                    file_type='json'
                )
                
                # Save images if any
                saved_image_paths = []
                if images:
                    update_progress(session_id, file_id, 98, f"Saving {len(images)} extracted images...")
                    saved_image_paths = minio_service.add_images_to_conversion_folder(folder_id, images)
                
                # Create a comprehensive summary
                extraction_summary = {
                    'text_extracted': True,
                    'images_extracted': len(images),
                    'images_saved': len(saved_image_paths),
                    'tables_extracted': len(tables),
                    'folder_id': folder_id,
                    'files_created': []
                }
                
                if md_success:
                    extraction_summary['files_created'].append('converted.md')
                if json_success:
                    extraction_summary['files_created'].append('converted.json')
                if saved_image_paths:
                    extraction_summary['files_created'].extend([f"images/{os.path.basename(path)}" for path in saved_image_paths])
                
                # Also save to traditional outputs bucket for backward compatibility with existing APIs
                output_bytes = output_content.encode('utf-8')
                compat_success, output_file_id, compat_storage_path = minio_service.upload_output_file(
                    file_content=output_bytes,
                    file_name=output_filename,
                    user_id=None
                )
                
                if compat_success:
                    # Record conversion in local metadata for compatibility
                    success_conversion, conversion_id = minio_service.create_conversion_record(
                        file_id=file_id,
                        output_format=output_format,
                        output_path=compat_storage_path,
                        user_id=session_id,
                        content_length=len(output_content)
                    )
                
                update_progress(session_id, file_id, 100, "Conversion completed with enhanced folder organization!")
                
                return jsonify({
                    'file_id': file_id,
                    'output_file_id': output_file_id if compat_success else None,
                    'output_format': output_format,
                    'content_preview': output_content[:500] + '...' if len(output_content) > 500 else output_content,
                    'content_length': len(output_content),
                    'storage_path': compat_storage_path if compat_success else None,
                    'storage_mode': 'enhanced_folders',
                    'session_id': session_id,
                    'conversion_folder': {
                        'folder_id': folder_id,
                        'folder_path': f"outputs/{folder_id}/",
                        'extraction_summary': extraction_summary,
                        'files_available': extraction_summary['files_created']
                    },
                    'message': f'File converted successfully to folder with {len(images)} images and {len(tables)} tables extracted'
                })
            else:
                # Local mode - save converted file using local file manager
                output_bytes = output_content.encode('utf-8')
                success, output_file_id, output_path = local_file_manager.save_converted_file(
                    file_content=output_bytes,
                    original_file_id=file_id,
                    output_format=output_format,
                    session_id=session_id
                )
                
                if not success:
                    return jsonify({'error': f'Failed to save converted file: {output_file_id}'}), 500
                
                update_progress(session_id, file_id, 100, "Conversion completed successfully!")
                
                return jsonify({
                    'file_id': file_id,
                    'output_file_id': output_file_id,
                    'output_format': output_format,
                    'content_preview': output_content[:500] + '...' if len(output_content) > 500 else output_content,
                    'content_length': len(output_content),
                    'storage_path': output_path,
                    'storage_mode': 'local',
                    'session_id': session_id,
                    'message': 'File converted successfully'
                })
            
        finally:
            # Clean up temporary file if in MinIO mode
            if minio_service and 'temp_filepath' in locals():
                try:
                    os.unlink(temp_filepath)
                except:
                    pass  # Ignore cleanup errors
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/split', methods=['POST'])
def split_text():
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        splitter_params = data.get('splitter_params', {})
        output_format = data.get('output_format', 'md')
        
        if not file_id:
            return jsonify({'error': 'No file_id provided'}), 400
        
        # Get current session
        session_id = session_service.get_session_id()
        # Note: Keeping session for local mode compatibility, but removing session filtering for MinIO mode
        
        if minio_service:
            # MinIO mode - find the converted file (no session filtering)
            success, conversion_record, error_msg = minio_service.get_conversion_record(
                file_id=file_id,
                output_format=output_format,
                user_id=None  # Remove session filtering - access any file
            )
            
            if not success:
                return jsonify({'error': f'Converted file not found. Please convert first. {error_msg}'}), 404
            
            # Download converted file from MinIO outputs bucket
            success, file_content, error_msg = minio_service.download_file(
                storage_path=conversion_record['output_path'],
                bucket=minio_service.outputs_bucket
            )
            
            if not success:
                return jsonify({'error': f'Failed to download converted file: {error_msg}'}), 500
            
            # Read content
            content = file_content.decode('utf-8')
            
            # Split text
            chunks = text_splitter_service.split_text(content, splitter_params)
            
            # Create split output
            split_filename = f"{file_id}_split.{output_format}"
            
            if output_format == 'json':
                split_content = json.dumps({
                    'chunks': chunks,
                    'chunk_count': len(chunks),
                    'splitter_params': splitter_params
                }, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            else:  # markdown
                split_content = f"# Split Document\n\n**Chunk Count:** {len(chunks)}\n\n**Splitter Parameters:** {json.dumps(splitter_params, indent=2, cls=CustomJSONEncoder)}\n\n---\n\n"
                for i, chunk in enumerate(chunks, 1):
                    split_content += f"## Chunk {i}\n\n{chunk}\n\n---\n\n"
            
            # Upload split file to MinIO splits bucket
            split_bytes = split_content.encode('utf-8')
            success, split_storage_path = minio_service.save_output(
                content=split_content,
                filename=split_filename,
                user_id=session_id,
                bucket_type='splits'
            )
            
            if not success:
                return jsonify({'error': 'Failed to save split file'}), 500
            
            return jsonify({
                'file_id': file_id,
                'chunk_count': len(chunks),
                'splitter_params': splitter_params,
                'preview': chunks[:3] if len(chunks) > 3 else chunks,
                'storage_path': split_storage_path,
                'message': 'Text split successfully'
            })
        else:
            # Local mode - use the existing local file manager logic
            success, file_metadata, error_msg = local_file_manager.get_file_metadata(file_id, session_id)
            if not success:
                return jsonify({'error': f'File not found: {error_msg}'}), 404
            
            # Get converted file
            success, converted_path, error_msg = local_file_manager.get_converted_file_path(file_id, session_id, output_format)
            if not success:
                return jsonify({'error': f'Converted file not found: {error_msg}'}), 404
            
            # Read and split content
            with open(converted_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = text_splitter_service.split_text(content, splitter_params)
            
            # Save split file locally
            success, output_file_id, output_path = local_file_manager.save_split_file(
                chunks=chunks,
                original_file_id=file_id,
                output_format=output_format,
                session_id=session_id,
                splitter_params=splitter_params
            )
            
            if not success:
                return jsonify({'error': f'Failed to save split file: {output_file_id}'}), 500
            
            return jsonify({
                'file_id': file_id,
                'chunk_count': len(chunks),
                'splitter_params': splitter_params,
                'preview': chunks[:3] if len(chunks) > 3 else chunks,
                'storage_path': output_path,
                'storage_mode': 'local',
                'message': 'Text split successfully'
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<file_id>/<file_type>')
def download_file(file_id, file_type):
    try:
        # Get current session
        session_id = session_service.get_session_id()
        # Note: Keeping session for local mode compatibility, but removing session filtering for MinIO mode
        
        if minio_service:
            # MinIO mode
            if file_type == 'original':
                # Download the original uploaded file (not converted file)
                success, file_record, error_msg = minio_service.get_file_record(file_id)
                if not success:
                    return jsonify({'error': f'File not found: {error_msg}'}), 404
                
                storage_path = file_record['storage_path']
                filename = file_record['original_name']
                bucket = minio_service.uploads_bucket
                
            elif file_type == 'converted':
                # Find converted file (no session filtering)
                success, conversion_record, error_msg = minio_service.get_conversion_record(
                    file_id=file_id,
                    output_format='md',  # Default format, could be enhanced
                    user_id=None  # Remove session filtering
                )
                
                if not success:
                    # Try json format as fallback
                    success, conversion_record, error_msg = minio_service.get_conversion_record(
                        file_id=file_id,
                        output_format='json',
                        user_id=None  # Remove session filtering
                    )
                
                if not success:
                    return jsonify({'error': 'Converted file not found'}), 404
                
                storage_path = conversion_record['output_path']
                output_format = conversion_record['output_format']
                filename = f"{file_id}.{output_format}"
                bucket = minio_service.outputs_bucket
                
            elif file_type == 'split':
                # Find split file - look for conversion first, then find split file
                success, conversion_record, error_msg = minio_service.get_conversion_record(
                    file_id=file_id,
                    output_format='md',  # Default format
                    user_id=None  # Remove session filtering
                )
                
                if not success:
                    # Try json format as fallback
                    success, conversion_record, error_msg = minio_service.get_conversion_record(
                        file_id=file_id,
                        output_format='json',
                        user_id=None  # Remove session filtering
                    )
                
                if not success:
                    return jsonify({'error': 'No split files found for this file'}), 404
                
                output_format = conversion_record['output_format']
                
                # Look for split file with naming pattern (global storage, no user prefix)
                split_filename = f"{file_id}_split.{output_format}"
                storage_path = split_filename  # No session prefix for global storage
                filename = split_filename
                bucket = minio_service.splits_bucket
                
            else:
                return jsonify({'error': 'Invalid file type. Use "original", "converted", or "split"'}), 400
            
            # Download file from MinIO
            success, file_content, error_msg = minio_service.download_file(storage_path, bucket)
            
            if not success:
                return jsonify({'error': f'File not found: {error_msg}'}), 404
            
            # Return file as download
            return send_file(
                io.BytesIO(file_content),
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        else:
            # Local mode - download using local file manager
            if file_type == 'original':
                success, file_path, filename, error_msg = local_file_manager.get_converted_file_path(file_id, session_id)
            elif file_type == 'split':
                success, file_path, filename, error_msg = local_file_manager.get_split_file_path(file_id, session_id)
            else:
                return jsonify({'error': 'Invalid file type. Use "original" or "split"'}), 400
            
            if not success:
                return jsonify({'error': f'File not found: {error_msg}'}), 404
            
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found on disk'}), 404
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health')
def health_check():
    session_id = session_service.get_session_id()
    
    health_info = {
        'status': 'healthy', 
        'message': 'Document converter API is running',
        'version': '2.0.0',
        'storage_mode': STORAGE_MODE,
        'minio_connected': minio_service is not None,
        'session_active': session_id is not None,
        'session_id': session_id,
        'features': {
            'file_upload': True,
            'document_conversion': True,
            'text_splitting': True,
            'session_isolation': True,
            'cloud_storage': minio_service is not None,
            'local_storage': True
        }
    }
    
    return jsonify(health_info)

@app.route('/api/files')
def list_files():
    """List files (all files, no session filtering)"""
    try:
        if minio_service:
            # MinIO mode - get ALL files (no session filtering)
            success, files, error_msg = minio_service.get_user_files(user_id=None)
            
            if not success:
                return jsonify({'error': f'Failed to retrieve files: {error_msg}'}), 500
            
            # For MinIO mode, we don't have detailed conversion tracking
            # but we can add basic info
            for file_record in files:
                file_record['conversions'] = []  # Will be populated by file listing
                
            return jsonify({
                'files': files,
                'total_count': len(files),
                'session_id': None,  # Remove session tracking
                'storage_mode': 'minio',
                'message': 'Files retrieved successfully'
            })
        else:
            # Local mode - get current session for compatibility
            session_id = session_service.get_session_id()
            if not session_id:
                return jsonify({
                    'files': [],
                    'total_count': 0,
                    'session_id': None,
                    'message': 'No active session'
                })
            
            # Local mode - get files using local file manager
            success, files, error_msg = local_file_manager.list_session_files(session_id)
            
            if not success:
                return jsonify({'error': f'Failed to retrieve files: {error_msg}'}), 500
            
            return jsonify({
                'files': files,
                'total_count': len(files),
                'session_id': session_id,
                'storage_mode': 'local',
                'message': 'Files retrieved successfully'
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file_endpoint(file_id):
    """Delete a file and all its associated data (no session filtering)"""
    try:
        if minio_service:
            # MinIO mode with local metadata (no session filtering)
            # Get file record without session verification
            success, file_record, error_msg = minio_service.get_file_record(file_id)
            if not success:
                return jsonify({'error': f'File not found: {error_msg}'}), 404
            
            # Remove session verification - allow deletion of any file
            # if file_record['user_id'] != session_id:
            #     return jsonify({'error': 'File not found in current session'}), 404
            
            # Delete from MinIO storage
            if not minio_service.delete_file(file_record['storage_path']):
                print(f"⚠️  Warning: Could not delete file from storage: {file_record['storage_path']}")
            
            # Delete local metadata file
            try:
                metadata_path = os.path.join('file_metadata', f"{file_id}.json")
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)
                    print(f"✅ Deleted metadata file: {metadata_path}")
            except Exception as e:
                print(f"⚠️  Warning: Could not delete metadata file: {e}")
            
            # Delete any output files (converted files) - search all sessions
            try:
                user_outputs = glob.glob(f"outputs/*")
                for output_file in user_outputs:
                    if file_id in output_file:
                        os.remove(output_file)
                        print(f"✅ Deleted output file: {output_file}")
            except Exception as e:
                print(f"⚠️  Warning: Could not delete output files: {e}")
            
            return jsonify({
                'message': 'File deleted successfully',
                'file_id': file_id,
                'storage_mode': 'minio'
            })
        else:
            # Local mode - get current session for compatibility
            session_id = session_service.get_session_id()
            if not session_id:
                return jsonify({'error': 'No active session'}), 400
            
            # Local mode - delete using local file manager
            success, error_msg = local_file_manager.delete_file(file_id, session_id)
            
            if not success:
                return jsonify({'error': f'Failed to delete file: {error_msg}'}), 500
            
            return jsonify({
                'message': 'File deleted successfully',
                'file_id': file_id,
                'storage_mode': 'local'
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session')
def get_session_info():
    """Get current session information"""
    try:
        session_id = session_service.get_session_id()
        
        if not session_id:
            return jsonify({
                'session_id': None,
                'active': False,
                'message': 'No active session'
            })
        
        # Get session statistics
        if minio_service:
            # MinIO mode - get file count from local metadata
            success, files, error_msg = minio_service.get_user_files(user_id=session_id)
            file_count = len(files) if success else 0
            
            return jsonify({
                'session_id': session_id,
                'active': True,
                'storage_mode': 'minio',
                'statistics': {
                    'file_count': file_count,
                    'conversion_count': 0  # We could implement this later if needed
                },
                'created_at': session.get('created_at'),
                'message': 'Session active'
            })
        else:
            # Local mode - get statistics from local file manager
            success, stats, error_msg = local_file_manager.get_session_statistics(session_id)
            
            if not success:
                stats = {'file_count': 0, 'conversion_count': 0, 'total_file_size': 0}
            
            return jsonify({
                'session_id': session_id,
                'active': True,
                'storage_mode': 'local',
                'statistics': stats,
                'created_at': session.get('created_at'),
                'message': 'Session active'
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session', methods=['DELETE'])
def clear_session():
    """Clear current session and optionally delete associated files"""
    try:
        session_id = session_service.get_session_id()
        if not session_id:
            return jsonify({'message': 'No active session to clear'})
        
        # Get query parameter for file deletion
        delete_files = request.args.get('delete_files', 'false').lower() == 'true'
        
        if delete_files:
            if minio_service:
                # MinIO mode - delete all session files
                success, files, error_msg = minio_service.get_user_files(user_id=session_id)
                if success and files:
                    for file_record in files:
                        # Delete file from uploads storage
                        minio_service.delete_file(file_record['storage_path'], bucket_type='uploads')
                        
                        # Delete metadata file
                        try:
                            metadata_path = os.path.join('file_metadata', f"{file_record['file_id']}.json")
                            if os.path.exists(metadata_path):
                                os.remove(metadata_path)
                        except Exception as e:
                            print(f"Warning: Could not delete metadata: {e}")
                    
                    # Clean up conversion metadata
                    try:
                        conversions_dir = 'conversion_metadata'
                        if os.path.exists(conversions_dir):
                            for conversion_file in os.listdir(conversions_dir):
                                if conversion_file.endswith('.json'):
                                    conversion_path = os.path.join(conversions_dir, conversion_file)
                                    try:
                                        with open(conversion_path, 'r') as f:
                                            conversion = json.load(f)
                                        if conversion.get('user_id') == session_id:
                                            # Delete output and split files
                                            if conversion.get('output_path'):
                                                minio_service.delete_file(conversion['output_path'], bucket_type='outputs')
                                            # Delete conversion metadata
                                            os.remove(conversion_path)
                                    except Exception as e:
                                        print(f"Warning: Could not clean up conversion {conversion_file}: {e}")
                    except Exception as e:
                        print(f"Warning: Could not clean up conversions: {e}")
            else:
                # Local mode - cleanup session files
                local_file_manager.cleanup_session_data(session_id)
        
        # Clear Flask session
        session.clear()
        
        return jsonify({
            'message': 'Session cleared successfully',
            'files_deleted': delete_files,
            'previous_session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# File Manager API Routes
@app.route('/api/files/<bucket_name>')
def list_bucket_files(bucket_name):
    """List all files in a specific MinIO bucket (no session filtering)"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        # List ALL files in the bucket (remove session filtering)
        files = []
        try:
            objects = minio_service.client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                # Get object stats for more info
                stat = minio_service.client.stat_object(bucket_name, obj.object_name)
                
                # Use the full object name as display name (no session prefix removal)
                display_name = obj.object_name
                
                file_info = {
                    'name': display_name,
                    'full_path': obj.object_name,  # Keep full path for downloads
                    'size': obj.size,
                    'lastModified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'type': obj.object_name.split('.')[-1] if '.' in obj.object_name else 'unknown',
                    'bucket': bucket_name,
                    'etag': obj.etag
                }
                files.append(file_info)
                
        except Exception as e:
            print(f"Error listing files in bucket {bucket_name}: {e}")
            # Return empty list if bucket doesn't exist or is empty
            pass
        
        return jsonify({
            'files': files,
            'bucket': bucket_name,
            'count': len(files),
            'session_id': None  # Remove session tracking
        })
        
    except Exception as e:
        print(f"Error in list_bucket_files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversion-folders')
def list_conversion_folders():
    """List all conversion folders in outputs bucket"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Get all conversion folders
        folders = minio_service.list_conversion_folders()
        
        return jsonify({
            'folders': folders,
            'count': len(folders),
            'bucket': 'outputs'
        })
        
    except Exception as e:
        print(f"Error in list_conversion_folders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversion-folders/<folder_id>/files')
def list_conversion_folder_files(folder_id):
    """List all files in a specific conversion folder"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Get folder metadata
        success, metadata = minio_service.get_conversion_folder_metadata(folder_id)
        if not success:
            return jsonify({'error': 'Folder not found'}), 404
        
        # Get files in folder
        files = minio_service.list_conversion_folder_files(folder_id)
        
        return jsonify({
            'folder_id': folder_id,
            'metadata': metadata,
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        print(f"Error in list_conversion_folder_files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversion-folders/<folder_id>/download/<path:filename>')
def download_from_conversion_folder(folder_id, filename):
    """Download a specific file from a conversion folder"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Construct full file path
        file_path = f"{folder_id}/{filename}"
        
        # Download file from MinIO
        success, file_content, error_msg = minio_service.download_from_conversion_folder(folder_id, filename)
        
        if not success:
            return jsonify({'error': f'File not found: {error_msg}'}), 404
        
        # Determine content type based on file extension
        content_type = 'application/octet-stream'
        if filename.endswith('.md'):
            content_type = 'text/markdown'
        elif filename.endswith('.json'):
            content_type = 'application/json'
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            content_type = f'image/{filename.split(".")[-1]}'
        
        return send_file(
            BytesIO(file_content),
            as_attachment=True,
            download_name=filename,
            mimetype=content_type
        )
        
    except Exception as e:
        print(f"Error downloading from conversion folder: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversion-folders/<folder_id>', methods=['DELETE'])
def delete_conversion_folder(folder_id):
    """Delete entire conversion folder and all its contents"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Delete the entire folder
        success, error_msg = minio_service.delete_conversion_folder(folder_id)
        
        if not success:
            return jsonify({'error': f'Failed to delete folder: {error_msg}'}), 500
        
        return jsonify({
            'message': f'Conversion folder {folder_id} deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting conversion folder: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-delete/<bucket_name>', methods=['DELETE'])
def bulk_delete_files(bucket_name):
    """Delete multiple files from a MinIO bucket"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({'error': 'Filenames list required'}), 400
        
        filenames = data['filenames']
        if not isinstance(filenames, list) or len(filenames) == 0:
            return jsonify({'error': 'Invalid filenames list'}), 400
        
        deleted_files = []
        failed_files = []
        
        # Delete each file
        for filename in filenames:
            try:
                minio_service.client.remove_object(bucket_name, filename)
                deleted_files.append(filename)
            except Exception as e:
                print(f"Error deleting file {filename} from {bucket_name}: {e}")
                failed_files.append({'filename': filename, 'error': str(e)})
        
        response = {
            'message': f'Bulk delete completed',
            'deleted_count': len(deleted_files),
            'failed_count': len(failed_files),
            'deleted_files': deleted_files
        }
        
        if failed_files:
            response['failed_files'] = failed_files
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in bulk_delete_files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-download/<bucket_name>', methods=['POST'])
def bulk_download_files(bucket_name):
    """Create a zip file with multiple files from a MinIO bucket"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({'error': 'Filenames list required'}), 400
        
        filenames = data['filenames']
        if not isinstance(filenames, list) or len(filenames) == 0:
            return jsonify({'error': 'Invalid filenames list'}), 400
        
        import zipfile
        import io
        from datetime import datetime
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            downloaded_files = []
            failed_files = []
            
            for filename in filenames:
                try:
                    # Get file from MinIO
                    response = minio_service.client.get_object(bucket_name, filename)
                    file_data = response.read()
                    response.close()
                    
                    # Add file to zip
                    zip_file.writestr(filename, file_data)
                    downloaded_files.append(filename)
                    
                except Exception as e:
                    print(f"Error downloading file {filename} from {bucket_name}: {e}")
                    failed_files.append({'filename': filename, 'error': str(e)})
        
        if len(downloaded_files) == 0:
            return jsonify({'error': 'No files could be downloaded'}), 400
        
        zip_buffer.seek(0)
        
        # Generate zip filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"{bucket_name}_files_{timestamp}.zip"
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"Error in bulk_download_files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert-again', methods=['POST'])
def convert_again():
    """Re-convert a file that's already uploaded"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Filename required'}), 400
        
        filename = data['filename']
        bucket = data.get('bucket', 'uploads')
        
        # Validate bucket name
        if bucket not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        # Check if file exists
        try:
            minio_service.client.stat_object(bucket, filename)
        except Exception as e:
            return jsonify({'error': 'File not found'}), 404
        
        # Get the file for conversion
        try:
            response = minio_service.client.get_object(bucket, filename)
            file_data = response.read()
            response.close()
            
            # Determine file type
            file_ext = filename.split('.')[-1].lower()
            if file_ext not in processors:
                return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
            
            # Process the file
            processor = processors[file_ext]
            
            # Write file data to a temporary file for processing
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_file:
                temp_file.write(file_data)
                temp_filepath = temp_file.name
            
            try:
                result = processor.process(temp_filepath)
                
                # Check if result indicates an error (for processors that include error info)
                if isinstance(result, dict) and 'error' in result:
                    return jsonify({'error': f'Conversion failed: {result["error"]}'}), 500
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_filepath):
                    os.unlink(temp_filepath)
            
            # Convert to markdown format
            if isinstance(result, dict):
                output_content = processor.to_markdown(result)
            else:
                output_content = str(result)
            
            # Generate new file ID for the converted file
            file_id = str(uuid.uuid4())
            output_filename = f"{file_id}.md"
            
            # Upload to outputs bucket
            output_bytes = output_content.encode('utf-8')
            try:
                minio_service.client.put_object(
                    'outputs',
                    output_filename,
                    io.BytesIO(output_bytes),
                    len(output_bytes),
                    content_type='text/markdown'
                )
                
                return jsonify({
                    'success': True,
                    'message': f'File {filename} converted successfully',
                    'output_file': output_filename,
                    'file_id': file_id
                })
                
            except Exception as e:
                return jsonify({'error': f'Failed to save converted file: {str(e)}'}), 500
                
        except Exception as e:
            print(f"Error converting file {filename}: {e}")
            return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in convert_again: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/view/<bucket_name>/<path:filename>', methods=['GET'])
def view_file(bucket_name, filename):
    """View a file directly from MinIO bucket (opens in new tab/window)"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        # Check if file exists
        try:
            minio_service.client.stat_object(bucket_name, filename)
        except Exception as e:
            return jsonify({'error': 'File not found'}), 404
        
        # Get file from MinIO
        try:
            response = minio_service.client.get_object(bucket_name, filename)
            file_data = response.read()
            response.close()
            
            # Determine content type
            file_ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            
            # Set content type based on file extension
            content_type_map = {
                'pdf': 'application/pdf',
                'txt': 'text/plain; charset=utf-8',
                'md': 'text/markdown; charset=utf-8',
                'json': 'application/json; charset=utf-8',
                'html': 'text/html; charset=utf-8',
                'css': 'text/css; charset=utf-8',
                'js': 'application/javascript; charset=utf-8',
                'xml': 'application/xml; charset=utf-8',
                'csv': 'text/csv; charset=utf-8',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'bmp': 'image/bmp',
                'webp': 'image/webp',
                'svg': 'image/svg+xml'
            }
            
            content_type = content_type_map.get(file_ext, 'application/octet-stream')
            
            # Create response with proper headers
            from flask import Response
            response = Response(file_data)
            response.headers['Content-Type'] = content_type
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            response.headers['Cache-Control'] = 'no-cache'
            
            return response
            
        except Exception as e:
            print(f"Error viewing file {filename} from {bucket_name}: {e}")
            return jsonify({'error': f'Failed to view file: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in view_file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview/<bucket_name>/<path:filename>', methods=['GET'])
def preview_file(bucket_name, filename):
    """Preview a file from MinIO bucket (for file manager frontend)"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        # Check if file exists
        try:
            minio_service.client.stat_object(bucket_name, filename)
        except Exception as e:
            return jsonify({'error': 'File not found'}), 404
        
        # Get file from MinIO
        try:
            response = minio_service.client.get_object(bucket_name, filename)
            file_data = response.read()
            response.close()
            
            # Determine file type
            file_ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            
            # Handle different file types for preview
            if file_ext in ['md', 'txt', 'json', 'xml', 'yaml', 'html', 'css', 'js', 'py', 'java', 'cpp', 'sql', 'php', 'go', 'rust']:
                # Text-based files - return content as text
                try:
                    content = file_data.decode('utf-8')
                    return jsonify({
                        'success': True,
                        'content': content,
                        'type': 'text',
                        'file_type': file_ext,
                        'filename': filename,
                        'size': len(file_data)
                    })
                except UnicodeDecodeError:
                    return jsonify({'error': 'File contains binary data and cannot be previewed as text'}), 400
            
            elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'tif']:
                # Image files - return as base64 encoded data
                import base64
                encoded_data = base64.b64encode(file_data).decode('utf-8')
                return jsonify({
                    'success': True,
                    'content': encoded_data,
                    'type': 'image',
                    'file_type': file_ext,
                    'filename': filename,
                    'size': len(file_data)
                })
            
            elif file_ext == 'pdf':
                # PDF files - return basic info (could be extended to extract text preview)
                return jsonify({
                    'success': True,
                    'content': f'PDF file: {filename}\nSize: {len(file_data)} bytes\n\nUse download to view the full PDF.',
                    'type': 'binary',
                    'file_type': file_ext,
                    'filename': filename,
                    'size': len(file_data)
                })
            
            else:
                # Other binary files
                return jsonify({
                    'success': True,
                    'content': f'Binary file: {filename}\nSize: {len(file_data)} bytes\nType: {file_ext}\n\nThis file type cannot be previewed. Use download to access the file.',
                    'type': 'binary',
                    'file_type': file_ext,
                    'filename': filename,
                    'size': len(file_data)
                })
            
        except Exception as e:
            print(f"Error previewing file {filename} from {bucket_name}: {e}")
            return jsonify({'error': f'Failed to preview file: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in preview_file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<bucket_name>/<path:filename>', methods=['GET'])
def download_file_by_filename(bucket_name, filename):
    """Download a file from MinIO bucket by filename (for file manager frontend)"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        # Check if file exists
        try:
            minio_service.client.stat_object(bucket_name, filename)
        except Exception as e:
            return jsonify({'error': 'File not found'}), 404
        
        # Get file from MinIO
        try:
            response = minio_service.client.get_object(bucket_name, filename)
            file_data = response.read()
            response.close()
            
            # Determine content type based on file extension
            file_ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            content_type_map = {
                'pdf': 'application/pdf',
                'txt': 'text/plain',
                'md': 'text/markdown',
                'json': 'application/json',
                'html': 'text/html',
                'css': 'text/css',
                'js': 'application/javascript',
                'xml': 'application/xml',
                'csv': 'text/csv',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'bmp': 'image/bmp',
                'webp': 'image/webp',
                'svg': 'image/svg+xml'
            }
            
            content_type = content_type_map.get(file_ext, 'application/octet-stream')
            
            # Get just the filename for download (not the full path)
            download_filename = filename.split('/')[-1]
            
            # Create response for download
            from flask import Response
            response = Response(file_data)
            response.headers['Content-Type'] = content_type
            response.headers['Content-Disposition'] = f'attachment; filename="{download_filename}"'
            response.headers['Content-Length'] = str(len(file_data))
            
            return response
            
        except Exception as e:
            print(f"Error downloading file {filename} from {bucket_name}: {e}")
            return jsonify({'error': f'Failed to download file: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in download_file_by_filename: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<bucket_name>/<path:filename>', methods=['DELETE'])
def delete_file_by_filename(bucket_name, filename):
    """Delete a file from MinIO bucket by filename (for file manager frontend)"""
    try:
        if not minio_service:
            return jsonify({'error': 'MinIO service not available'}), 503
        
        # Validate bucket name
        if bucket_name not in ['uploads', 'outputs', 'splits']:
            return jsonify({'error': 'Invalid bucket name'}), 400
        
        # Check if file exists
        try:
            minio_service.client.stat_object(bucket_name, filename)
        except Exception as e:
            return jsonify({'error': 'File not found'}), 404
        
        # Delete the file from MinIO
        try:
            minio_service.client.remove_object(bucket_name, filename)
            
            # If it's an uploads file, also try to clean up related metadata
            if bucket_name == 'uploads':
                # Extract potential file_id from filename if it follows the pattern
                # filename format might be: file_id_originalname.ext
                parts = filename.split('_', 1)
                if len(parts) > 1:
                    potential_file_id = parts[0]
                    # Try to clean up metadata file
                    try:
                        metadata_path = os.path.join('file_metadata', f"{potential_file_id}.json")
                        if os.path.exists(metadata_path):
                            os.remove(metadata_path)
                            print(f"✅ Cleaned up metadata for {potential_file_id}")
                    except Exception as e:
                        print(f"⚠️  Could not clean up metadata: {e}")
            
            return jsonify({
                'message': f'File {filename} deleted successfully from {bucket_name}',
                'filename': filename,
                'bucket': bucket_name
            })
            
        except Exception as e:
            print(f"Error deleting file {filename} from {bucket_name}: {e}")
            return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in delete_file_by_filename: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
