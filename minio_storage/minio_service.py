"""
MinIO Storage Service
Handles file upload, download, and management using MinIO object storage
"""

import os
import uuid
import json
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any
from minio import Minio
from minio.error import S3Error
import io
import pandas as pd
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


class MinIOService:
    """MinIO storage service for handling file operations"""
    
    def __init__(self):
        """Initialize MinIO client with configuration from environment"""
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        
        # Bucket names
        self.uploads_bucket = os.getenv('MINIO_BUCKET_UPLOADS', 'uploads')
        self.outputs_bucket = os.getenv('MINIO_BUCKET_OUTPUTS', 'outputs')  # Now contains folders
        self.splits_bucket = os.getenv('MINIO_BUCKET_SPLITS', 'splits')
        self.documents_bucket = os.getenv('MINIO_BUCKET_DOCUMENTS', 'documents')  # Legacy - keeping for compatibility
        
        # Initialize MinIO client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure buckets exist (defer to first use if this fails)
        try:
            self._create_buckets()
        except Exception as e:
            print(f"⚠️  Warning: Could not verify buckets during initialization: {e}")
            print("   Buckets will be created on first use")
    
    def _create_buckets(self):
        """Create necessary buckets if they don't exist"""
        buckets = [self.uploads_bucket, self.outputs_bucket, self.splits_bucket, self.documents_bucket]
        
        for bucket in buckets:
            try:
                # Add timeout to bucket operations
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    print(f"✅ Created MinIO bucket: {bucket}")
                else:
                    print(f"✅ MinIO bucket exists: {bucket}")
            except Exception as e:
                print(f"❌ Error with bucket {bucket}: {e}")
                # Don't raise, just warn - buckets can be created later
                continue
    
    def upload_file(self, file_content: bytes, file_name: str, user_id: str) -> Tuple[bool, str, str]:
        """
        Upload file to MinIO storage
        
        Args:
            file_content: File content as bytes
            file_name: Original filename
            user_id: User/session ID (ignored for global storage)
            
        Returns:
            Tuple of (success, file_id, storage_path)
        """
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Create storage path without user organization (global storage)
            storage_path = f"{file_id}_{file_name}"
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.uploads_bucket,
                object_name=storage_path,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=self._get_content_type(file_name)
            )
            
            print(f"✅ File uploaded to MinIO: {storage_path}")
            return True, file_id, storage_path
            
        except S3Error as e:
            print(f"❌ MinIO upload error: {e}")
            return False, str(e), ""
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False, str(e), ""
    
    def download_file(self, storage_path: str, bucket: str = None) -> Tuple[bool, bytes, str]:
        """
        Download file from MinIO storage
        
        Args:
            storage_path: Path to file in storage
            bucket: Bucket name (defaults to uploads_bucket)
            
        Returns:
            Tuple of (success, file_content, error_msg)
        """
        try:
            bucket_name = bucket or self.uploads_bucket
            response = self.client.get_object(bucket_name, storage_path)
            file_content = response.read()
            return True, file_content, ""
            
        except S3Error as e:
            error_msg = f"MinIO download error: {e}"
            print(f"❌ {error_msg}")
            return False, b"", error_msg
        except Exception as e:
            error_msg = f"Download error: {e}"
            print(f"❌ {error_msg}")
            return False, b"", error_msg
    
    def save_output(self, content: str, filename: str, user_id: str, bucket_type: str = 'outputs') -> Tuple[bool, str]:
        """
        Save converted output to MinIO
        
        Args:
            content: File content as string
            filename: Output filename
            user_id: User/session ID (ignored for global storage)
            bucket_type: 'outputs' or 'splits'
            
        Returns:
            Tuple of (success, storage_path)
        """
        try:
            bucket = self.outputs_bucket if bucket_type == 'outputs' else self.splits_bucket
            storage_path = filename  # Store directly without user organization
            
            # Convert content to bytes
            content_bytes = content.encode('utf-8')
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=bucket,
                object_name=storage_path,
                data=io.BytesIO(content_bytes),
                length=len(content_bytes),
                content_type=self._get_content_type(filename)
            )
            
            print(f"✅ Output saved to MinIO: {storage_path}")
            return True, storage_path
            
        except S3Error as e:
            print(f"❌ MinIO save error: {e}")
            return False, ""
        except Exception as e:
            print(f"❌ Save error: {e}")
            return False, ""
    
    def download_output(self, storage_path: str, bucket_type: str = 'outputs') -> Tuple[bool, str]:
        """
        Download output file from MinIO
        
        Args:
            storage_path: Path to file in storage
            bucket_type: 'outputs' or 'splits'
            
        Returns:
            Tuple of (success, content)
        """
        try:
            bucket = self.outputs_bucket if bucket_type == 'outputs' else self.splits_bucket
            response = self.client.get_object(bucket, storage_path)
            content = response.read().decode('utf-8')
            return True, content
            
        except S3Error as e:
            print(f"❌ MinIO download error: {e}")
            return False, ""
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False, ""
    
    def delete_file(self, storage_path: str, bucket_type: str = 'uploads') -> bool:
        """Delete file from MinIO storage"""
        try:
            if bucket_type == 'uploads':
                bucket = self.uploads_bucket
            elif bucket_type == 'outputs':
                bucket = self.outputs_bucket
            else:
                bucket = self.splits_bucket
                
            self.client.remove_object(bucket, storage_path)
            print(f"✅ File deleted from MinIO: {storage_path}")
            return True
            
        except S3Error as e:
            print(f"❌ MinIO delete error: {e}")
            return False
        except Exception as e:
            print(f"❌ Delete error: {e}")
            return False
    
    def list_files(self, user_id: str = None, bucket_type: str = 'uploads') -> List[Dict[str, Any]]:
        """List all files in bucket (no user filtering for global storage)"""
        try:
            if bucket_type == 'uploads':
                bucket = self.uploads_bucket
            elif bucket_type == 'outputs':
                bucket = self.outputs_bucket
            else:
                bucket = self.splits_bucket
            
            # List all objects without user prefix (global storage)
            objects = self.client.list_objects(bucket, recursive=True)
            
            files = []
            for obj in objects:
                files.append({
                    'name': obj.object_name.split('/')[-1],  # Extract filename
                    'storage_path': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'bucket': bucket_type
                })
            
            return files
            
        except S3Error as e:
            print(f"❌ MinIO list error: {e}")
            return []
        except Exception as e:
            print(f"❌ List error: {e}")
            return []
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        extension = filename.lower().split('.')[-1]
        
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'json': 'application/json',
            'csv': 'text/csv',
            'epub': 'application/epub+zip'
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    def create_file_record(self, file_id: str, original_name: str, storage_path: str, 
                          file_size: int, user_id: str) -> Tuple[bool, str]:
        """Create metadata record for uploaded file (using local file metadata)"""
        try:
            # Extract file extension
            file_extension = original_name.split('.')[-1].lower() if '.' in original_name else ''
            
            # Create metadata record
            metadata = {
                'file_id': file_id,
                'original_name': original_name,
                'storage_path': storage_path,
                'file_size': file_size,
                'file_type': file_extension,
                'user_id': user_id,
                'upload_date': datetime.now().isoformat(),
                'storage_type': 'minio'
            }
            
            # Save metadata to local file (we can enhance this later)
            metadata_dir = 'file_metadata'
            os.makedirs(metadata_dir, exist_ok=True)
            
            metadata_path = os.path.join(metadata_dir, f"{file_id}.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, cls=CustomJSONEncoder)
            
            return True, "Metadata saved successfully"
            
        except Exception as e:
            return False, str(e)
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata by file ID"""
        try:
            metadata_path = os.path.join('file_metadata', f"{file_id}.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"❌ Error loading metadata: {e}")
            return None
    
    def get_file_record(self, file_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Get file record by file ID, returns (success, file_record, error_msg)"""
        try:
            metadata = self.get_file_metadata(file_id)
            if metadata is None:
                return False, None, f"File record not found for ID: {file_id}"
            
            # Map storage_path to file_path for compatibility with app.py expectations
            file_record = metadata.copy()
            if 'storage_path' in file_record:
                file_record['file_path'] = file_record['storage_path']
            
            return True, file_record, ""
            
        except Exception as e:
            error_msg = f"Error retrieving file record: {str(e)}"
            print(f"❌ {error_msg}")
            return False, None, error_msg

    def health_check(self) -> Dict[str, Any]:
        """Check MinIO service health"""
        try:
            # Try to list buckets to verify connection
            buckets = self.client.list_buckets()
            return {
                'status': 'healthy',
                'endpoint': self.endpoint,
                'buckets': [bucket.name for bucket in buckets],
                'secure': self.secure
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'endpoint': self.endpoint
            }
    
    def get_user_files(self, user_id: str = None) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Get all files (no user filtering for global storage), returns (success, files_list, error_msg)"""
        try:
            # Load all metadata files (no user filtering)
            metadata_dir = 'file_metadata'
            if not os.path.exists(metadata_dir):
                return True, [], ""
            
            user_files = []
            for metadata_file in os.listdir(metadata_dir):
                if metadata_file.endswith('.json'):
                    try:
                        metadata_path = os.path.join(metadata_dir, metadata_file)
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        # Include all files (no user filtering for global storage)
                        file_record = {
                            'id': metadata['file_id'],
                            'file_id': metadata['file_id'],
                            'original_name': metadata['original_name'], 
                            'file_name': metadata['original_name'],
                            'file_type': metadata['file_type'],
                            'file_size': metadata['file_size'],
                            'storage_path': metadata['storage_path'],
                            'file_path': metadata['storage_path'],
                            'user_id': metadata.get('user_id'),  # Keep for compatibility but don't filter
                            'upload_date': metadata['upload_date'],
                            'conversions': []  # We'll populate this if needed
                        }
                        user_files.append(file_record)
                    except Exception as e:
                        print(f"Error loading metadata file {metadata_file}: {e}")
                        continue
            
            return True, user_files, ""
            
        except Exception as e:
            error_msg = f"Error retrieving user files: {str(e)}"
            print(f"❌ {error_msg}")
            return False, [], error_msg
    
    def create_conversion_record(self, file_id: str, output_format: str, output_path: str, 
                               user_id: str, content_length: int) -> Tuple[bool, str]:
        """Create a conversion record using local metadata"""
        try:
            conversion_id = str(uuid.uuid4())
            conversion_metadata = {
                'id': conversion_id,
                'file_id': file_id,
                'user_id': user_id,
                'output_format': output_format,
                'output_path': output_path,
                'content_length': content_length,
                'status': 'completed',
                'created_at': datetime.now().isoformat()
            }
            
            # Save conversion metadata to local file
            conversions_dir = 'conversion_metadata'
            os.makedirs(conversions_dir, exist_ok=True)
            
            conversion_path = os.path.join(conversions_dir, f"{conversion_id}.json")
            with open(conversion_path, 'w') as f:
                json.dump(conversion_metadata, f, indent=2, cls=CustomJSONEncoder)
            
            return True, conversion_id
            
        except Exception as e:
            return False, str(e)
    
    def get_conversion_record(self, file_id: str, output_format: str, user_id: str = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Get conversion record by file_id and output_format (no user filtering for global storage)"""
        try:
            conversions_dir = 'conversion_metadata'
            if not os.path.exists(conversions_dir):
                return False, None, "No conversions found"
            
            # Search through all conversion records
            for conversion_file in os.listdir(conversions_dir):
                if conversion_file.endswith('.json'):
                    try:
                        conversion_path = os.path.join(conversions_dir, conversion_file)
                        with open(conversion_path, 'r') as f:
                            conversion = json.load(f)
                        
                        # Check if this matches our criteria (no user filtering for global storage)
                        if (conversion.get('file_id') == file_id and 
                            conversion.get('output_format') == output_format):
                            return True, conversion, ""
                    except Exception as e:
                        print(f"Error loading conversion file {conversion_file}: {e}")
                        continue
            
            return False, None, f"Conversion not found for file_id: {file_id}, format: {output_format}"
            
        except Exception as e:
            error_msg = f"Error retrieving conversion record: {str(e)}"
            print(f"❌ {error_msg}")
            return False, None, error_msg

    def upload_output_file(self, file_content: bytes, file_name: str, user_id: str) -> Tuple[bool, str, str]:
        """Upload converted output file to outputs bucket"""
        try:
            # Create storage path without user organization (global storage)
            storage_path = file_name
            
            # Upload to outputs bucket
            self.client.put_object(
                bucket_name=self.outputs_bucket,
                object_name=storage_path,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=self._get_content_type(file_name)
            )
            
            print(f"✅ Output file uploaded to MinIO: {storage_path}")
            return True, str(uuid.uuid4()), storage_path  # Return a generated output_file_id
            
        except S3Error as e:
            print(f"❌ MinIO upload error: {e}")
            return False, str(e), ""
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False, str(e), ""
    
    # New folder-based document organization methods
    
    def create_document_folder(self, document_name: str, session_id: str = None) -> str:
        """
        Create a new document folder structure
        
        Args:
            document_name: Original document name
            session_id: Optional session ID for organization
            
        Returns:
            Document folder ID (UUID)
        """
        document_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create folder metadata
        folder_metadata = {
            'document_id': document_id,
            'document_name': document_name,
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'folder_structure': {
                'original': f"{document_id}/original/",
                'converted': f"{document_id}/converted/",
                'split': f"{document_id}/split/", 
                'images': f"{document_id}/images/"
            },
            'files': {
                'original': None,
                'converted': [],
                'split': [],
                'images': []
            }
        }
        
        # Save metadata to documents bucket
        metadata_path = f"{document_id}/metadata.json"
        metadata_content = json.dumps(folder_metadata, indent=2, cls=CustomJSONEncoder).encode('utf-8')
        
        try:
            self.client.put_object(
                bucket_name=self.documents_bucket,
                object_name=metadata_path,
                data=io.BytesIO(metadata_content),
                length=len(metadata_content),
                content_type='application/json'
            )
            print(f"✅ Document folder created: {document_id}")
            return document_id
            
        except Exception as e:
            print(f"❌ Error creating document folder: {e}")
            raise e
    
    def upload_to_document_folder(self, document_id: str, file_content: bytes, 
                                 file_name: str, file_type: str) -> Tuple[bool, str]:
        """
        Upload file to specific document folder
        
        Args:
            document_id: Document folder ID
            file_content: File content as bytes
            file_name: File name
            file_type: 'original', 'converted', 'split', or 'images'
            
        Returns:
            Tuple of (success, file_path)
        """
        try:
            # Create file path within document folder
            file_path = f"{document_id}/{file_type}/{file_name}"
            
            # Upload file
            self.client.put_object(
                bucket_name=self.documents_bucket,
                object_name=file_path,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=self._get_content_type(file_name)
            )
            
            # Update metadata
            self._update_document_metadata(document_id, file_type, file_name, file_path)
            
            print(f"✅ File uploaded to document folder: {file_path}")
            return True, file_path
            
        except Exception as e:
            print(f"❌ Error uploading to document folder: {e}")
            return False, ""
    
    def save_images_to_document_folder(self, document_id: str, images: List[Dict[str, Any]]) -> List[str]:
        """
        Save extracted images to document folder
        
        Args:
            document_id: Document folder ID
            images: List of image dictionaries with base64_data
            
        Returns:
            List of saved image paths
        """
        saved_paths = []
        
        for img in images:
            try:
                import base64
                
                # Decode base64 image data
                img_data = base64.b64decode(img['base64_data'])
                filename = img['filename']
                
                # Upload image to images folder
                success, file_path = self.upload_to_document_folder(
                    document_id, img_data, filename, 'images'
                )
                
                if success:
                    saved_paths.append(file_path)
                    
            except Exception as e:
                print(f"❌ Error saving image {img.get('filename', 'unknown')}: {e}")
                continue
        
        return saved_paths
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document folder metadata"""
        try:
            metadata_path = f"{document_id}/metadata.json"
            response = self.client.get_object(self.documents_bucket, metadata_path)
            content = response.read().decode('utf-8')
            return json.loads(content)
            
        except Exception as e:
            print(f"❌ Error getting document metadata: {e}")
            return None
    
    def _update_document_metadata(self, document_id: str, file_type: str, 
                                 file_name: str, file_path: str):
        """Update document metadata with new file"""
        try:
            metadata = self.get_document_metadata(document_id)
            if not metadata:
                return
            
            # Update files list
            if file_type == 'original':
                metadata['files']['original'] = {
                    'name': file_name,
                    'path': file_path,
                    'uploaded_at': datetime.now().isoformat()
                }
            else:
                metadata['files'][file_type].append({
                    'name': file_name,
                    'path': file_path,
                    'uploaded_at': datetime.now().isoformat()
                })
            
            # Update last modified
            metadata['last_modified'] = datetime.now().isoformat()
            
            # Save updated metadata
            metadata_path = f"{document_id}/metadata.json"
            metadata_content = json.dumps(metadata, indent=2, cls=CustomJSONEncoder).encode('utf-8')
            
            self.client.put_object(
                bucket_name=self.documents_bucket,
                object_name=metadata_path,
                data=io.BytesIO(metadata_content),
                length=len(metadata_content),
                content_type='application/json'
            )
            
        except Exception as e:
            print(f"❌ Error updating document metadata: {e}")
    
    def list_document_folders(self, session_id: str = None) -> List[Dict[str, Any]]:
        """List all document folders, optionally filtered by session"""
        try:
            folders = []
            
            # List all objects in documents bucket
            objects = self.client.list_objects(self.documents_bucket, recursive=True)
            
            # Find all metadata files
            for obj in objects:
                if obj.object_name.endswith('/metadata.json'):
                    try:
                        response = self.client.get_object(self.documents_bucket, obj.object_name)
                        metadata = json.loads(response.read().decode('utf-8'))
                        
                        # Filter by session if specified
                        if session_id is None or metadata.get('session_id') == session_id:
                            folders.append(metadata)
                            
                    except Exception as e:
                        print(f"⚠️  Error reading metadata for {obj.object_name}: {e}")
                        continue
            
            # Sort by creation date (newest first)
            folders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return folders
            
        except Exception as e:
            print(f"❌ Error listing document folders: {e}")
            return []
    
    def download_from_document_folder(self, document_id: str, file_path: str) -> Tuple[bool, bytes]:
        """Download file from document folder"""
        try:
            response = self.client.get_object(self.documents_bucket, file_path)
            content = response.read()
            return True, content
            
        except Exception as e:
            print(f"❌ Error downloading from document folder: {e}")
            return False, b""
    
    def delete_document_folder(self, document_id: str) -> bool:
        """Delete entire document folder and all its contents"""
        try:
            # List all objects in the document folder
            objects = self.client.list_objects(
                self.documents_bucket, 
                prefix=f"{document_id}/", 
                recursive=True
            )
            
            # Delete all objects
            for obj in objects:
                self.client.remove_object(self.documents_bucket, obj.object_name)
            
            print(f"✅ Document folder deleted: {document_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting document folder: {e}")
            return False
    
    # ========================================================================
    # Enhanced Folder-Based Conversion System (New Implementation)
    # ========================================================================
    
    def create_conversion_folder(self, file_id: str, original_filename: str, session_id: str = None) -> str:
        """
        Create a new conversion folder in outputs bucket
        Folder name format: {original-filename}-{uuid}
        
        Args:
            file_id: Original file ID
            original_filename: Original filename (without extension)
            session_id: Session ID for metadata
            
        Returns:
            folder_id: Unique folder identifier
        """
        try:
            # Generate folder ID
            folder_uuid = str(uuid.uuid4())
            
            # Clean filename for folder name (remove extension and invalid chars)
            clean_filename = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
            clean_filename = "".join(c for c in clean_filename if c.isalnum() or c in ('-', '_')).strip()
            clean_filename = clean_filename[:50]  # Limit length
            
            folder_name = f"{clean_filename}-{folder_uuid}"
            
            # Create metadata for the conversion folder
            metadata = {
                'folder_id': folder_name,
                'original_file_id': file_id,
                'original_filename': original_filename,
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'files': {},
                'extraction_summary': {
                    'text_extracted': False,
                    'images_extracted': 0,
                    'tables_extracted': 0
                }
            }
            
            # Save metadata.json to the folder
            metadata_content = json.dumps(metadata, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            metadata_path = f"{folder_name}/metadata.json"
            
            success, error_msg = self._upload_to_bucket(
                bucket=self.outputs_bucket,
                object_name=metadata_path,
                data=metadata_content.encode('utf-8'),
                content_type='application/json'
            )
            
            if not success:
                print(f"❌ Failed to create conversion folder metadata: {error_msg}")
                return None
            
            print(f"✅ Conversion folder created: {folder_name}")
            return folder_name
            
        except Exception as e:
            print(f"❌ Error creating conversion folder: {e}")
            return None
    
    def add_file_to_conversion_folder(self, folder_id: str, file_content: bytes, filename: str, 
                                    file_type: str, content_type: str = None) -> Tuple[bool, str]:
        """
        Add a file to an existing conversion folder
        
        Args:
            folder_id: Conversion folder ID
            file_content: File content as bytes
            filename: Name of the file (e.g., 'converted.md', 'converted.json')
            file_type: Type of file ('markdown', 'json', 'image', 'metadata')
            content_type: MIME content type
            
        Returns:
            (success, file_path)
        """
        try:
            # Determine file path within folder
            if file_type == 'image':
                file_path = f"{folder_id}/images/{filename}"
            else:
                file_path = f"{folder_id}/{filename}"
            
            # Auto-detect content type if not provided
            if not content_type:
                if filename.endswith('.md'):
                    content_type = 'text/markdown'
                elif filename.endswith('.json'):
                    content_type = 'application/json'
                elif filename.endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif filename.endswith('.png'):
                    content_type = 'image/png'
                else:
                    content_type = 'application/octet-stream'
            
            # Upload file to folder
            success, error_msg = self._upload_to_bucket(
                bucket=self.outputs_bucket,
                object_name=file_path,
                data=file_content,
                content_type=content_type
            )
            
            if success:
                # Update folder metadata
                self._update_conversion_folder_metadata(folder_id, filename, file_type, len(file_content))
                print(f"✅ Added {file_type} file to folder: {file_path}")
                return True, file_path
            else:
                print(f"❌ Failed to add file to folder: {file_path}")
                return False, ""
            
        except Exception as e:
            print(f"❌ Error adding file to conversion folder: {e}")
            return False, ""
    
    def add_images_to_conversion_folder(self, folder_id: str, images: List[Dict]) -> List[str]:
        """
        Add multiple images to conversion folder
        
        Args:
            folder_id: Conversion folder ID
            images: List of image dictionaries with 'data' (base64) and metadata
            
        Returns:
            List of saved image paths
        """
        saved_paths = []
        
        try:
            for i, image_data in enumerate(images):
                # Get image data (base64 encoded)
                image_base64 = image_data.get('data', '')
                if not image_base64:
                    continue
                
                # Decode base64 image
                import base64
                try:
                    image_bytes = base64.b64decode(image_base64)
                except Exception as e:
                    print(f"⚠️  Failed to decode image {i}: {e}")
                    continue
                
                # Generate image filename
                image_format = image_data.get('format', 'jpeg').lower()
                if image_format not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                    image_format = 'jpeg'
                
                image_filename = f"image_{i+1:03d}.{image_format}"
                
                # Add image to folder
                success, image_path = self.add_file_to_conversion_folder(
                    folder_id=folder_id,
                    file_content=image_bytes,
                    filename=image_filename,
                    file_type='image'
                )
                
                if success:
                    saved_paths.append(image_path)
                    # Update image metadata to include path
                    image_data['relative_path'] = f"images/{image_filename}"
                
            print(f"✅ Added {len(saved_paths)} images to conversion folder")
            return saved_paths
            
        except Exception as e:
            print(f"❌ Error adding images to conversion folder: {e}")
            return saved_paths
    
    def _update_conversion_folder_metadata(self, folder_id: str, filename: str, file_type: str, file_size: int):
        """Update conversion folder metadata with new file information"""
        try:
            # Download existing metadata
            metadata_path = f"{folder_id}/metadata.json"
            success, metadata_content = self._download_from_bucket(self.outputs_bucket, metadata_path)
            
            if success:
                metadata = json.loads(metadata_content.decode('utf-8'))
            else:
                # Create new metadata if doesn't exist
                metadata = {
                    'folder_id': folder_id,
                    'created_at': datetime.now().isoformat(),
                    'files': {},
                    'extraction_summary': {
                        'text_extracted': False,
                        'images_extracted': 0,
                        'tables_extracted': 0
                    }
                }
            
            # Update metadata
            metadata['updated_at'] = datetime.now().isoformat()
            metadata['files'][filename] = {
                'type': file_type,
                'size': file_size,
                'added_at': datetime.now().isoformat()
            }
            
            # Update extraction summary
            if file_type == 'image':
                metadata['extraction_summary']['images_extracted'] += 1
            elif file_type in ['markdown', 'json']:
                metadata['extraction_summary']['text_extracted'] = True
            
            # Save updated metadata
            updated_metadata = json.dumps(metadata, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            self._upload_to_bucket(
                bucket=self.outputs_bucket,
                object_name=metadata_path,
                data=updated_metadata.encode('utf-8'),
                content_type='application/json'
            )
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to update folder metadata: {e}")
    
    def get_conversion_folder_metadata(self, folder_id: str) -> Tuple[bool, Dict]:
        """Get metadata for a conversion folder"""
        try:
            metadata_path = f"{folder_id}/metadata.json"
            success, content = self._download_from_bucket(self.outputs_bucket, metadata_path)
            
            if success:
                metadata = json.loads(content.decode('utf-8'))
                return True, metadata
            else:
                return False, {}
                
        except Exception as e:
            print(f"❌ Error getting conversion folder metadata: {e}")
            return False, {}
    
    def list_conversion_folders(self, session_id: str = None) -> List[Dict]:
        """
        List all conversion folders, optionally filtered by session
        
        Args:
            session_id: Optional session filter
            
        Returns:
            List of folder metadata dictionaries
        """
        folders = []
        
        try:
            # List all objects in outputs bucket
            objects = self.client.list_objects(self.outputs_bucket, recursive=False, prefix="")
            
            # Get folder names (objects ending with /)
            folder_names = set()
            for obj in objects:
                if '/' in obj.object_name:
                    folder_name = obj.object_name.split('/')[0]
                    folder_names.add(folder_name)
            
            # Get metadata for each folder
            for folder_name in folder_names:
                success, metadata = self.get_conversion_folder_metadata(folder_name)
                if success:
                    # Filter by session if specified
                    if session_id is None or metadata.get('session_id') == session_id:
                        folders.append(metadata)
            
            # Sort by creation date (newest first)
            folders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return folders
            
        except Exception as e:
            print(f"❌ Error listing conversion folders: {e}")
            return []
    
    def download_from_conversion_folder(self, folder_id: str, filename: str) -> Tuple[bool, bytes]:
        """Download a specific file from conversion folder"""
        try:
            file_path = f"{folder_id}/{filename}"
            return self._download_from_bucket(self.outputs_bucket, file_path)
            
        except Exception as e:
            print(f"❌ Error downloading from conversion folder: {e}")
            return False, b""
    
    def list_conversion_folder_files(self, folder_id: str) -> List[Dict]:
        """List all files in a conversion folder with their metadata"""
        try:
            # List all objects in the folder
            objects = self.client.list_objects(
                self.outputs_bucket, 
                prefix=f"{folder_id}/", 
                recursive=True
            )
            
            files = []
            for obj in objects:
                # Remove folder prefix to get relative path
                relative_path = obj.object_name[len(folder_id)+1:]
                
                if relative_path:  # Skip empty paths
                    file_info = {
                        'name': os.path.basename(relative_path),
                        'path': relative_path,
                        'full_path': obj.object_name,
                        'size': obj.size,
                        'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                        'type': self._determine_file_type(relative_path)
                    }
                    files.append(file_info)
            
            return files
            
        except Exception as e:
            print(f"❌ Error listing conversion folder files: {e}")
            return []
    
    def delete_conversion_folder(self, folder_id: str) -> bool:
        """Delete entire conversion folder and all its contents"""
        try:
            # List all objects in the folder
            objects = self.client.list_objects(
                self.outputs_bucket, 
                prefix=f"{folder_id}/", 
                recursive=True
            )
            
            # Delete all objects
            for obj in objects:
                self.client.remove_object(self.outputs_bucket, obj.object_name)
            
            print(f"✅ Conversion folder deleted: {folder_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting conversion folder: {e}")
            return False
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determine file type based on path and extension"""
        if file_path.startswith('images/'):
            return 'image'
        elif file_path.endswith('.md'):
            return 'markdown'
        elif file_path.endswith('.json'):
            return 'json'
        elif file_path == 'metadata.json':
            return 'metadata'
        else:
            return 'other'
    
    def _upload_to_bucket(self, bucket: str, object_name: str, data: bytes, content_type: str = None) -> Tuple[bool, str]:
        """
        Upload data to a specific bucket
        
        Args:
            bucket: Bucket name
            object_name: Object path/name
            data: Data to upload
            content_type: MIME content type
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if content_type is None:
                content_type = self._get_content_type(object_name)
            
            self.client.put_object(
                bucket,
                object_name,
                io.BytesIO(data),
                len(data),
                content_type=content_type
            )
            
            return True, ""
            
        except S3Error as e:
            error_msg = f"MinIO upload error: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Upload error: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def _download_from_bucket(self, bucket: str, object_name: str) -> Tuple[bool, bytes]:
        """
        Download data from a specific bucket
        
        Args:
            bucket: Bucket name
            object_name: Object path/name
            
        Returns:
            Tuple of (success, data)
        """
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            
            return True, data
            
        except S3Error as e:
            error_msg = f"MinIO download error: {e}"
            print(f"❌ {error_msg}")
            return False, b""
        except Exception as e:
            error_msg = f"Download error: {e}"
            print(f"❌ {error_msg}")
            return False, b""
    
    def upload_output_file(self, file_content: bytes, file_name: str, user_id: str) -> Tuple[bool, str, str]:
        """
        Upload output file to outputs bucket (backward compatibility method)
        
        Args:
            file_content: File content as bytes
            file_name: Name of the file
            user_id: User ID (ignored for global storage)
            
        Returns:
            Tuple of (success, file_id, storage_path)
        """
        try:
            # Generate file ID
            file_id = str(uuid.uuid4())
            
            # Use just the filename without user prefix for global storage
            storage_path = file_name
            
            # Upload to outputs bucket
            success, error_msg = self._upload_to_bucket(
                bucket=self.outputs_bucket,
                object_name=storage_path,
                data=file_content
            )
            
            if success:
                print(f"✅ File uploaded to outputs bucket: {storage_path}")
                return True, file_id, storage_path
            else:
                print(f"❌ Failed to upload file to outputs bucket: {error_msg}")
                return False, error_msg, ""
                
        except Exception as e:
            error_msg = f"Error uploading output file: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg, ""
