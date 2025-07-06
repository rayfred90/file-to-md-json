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
        self.outputs_bucket = os.getenv('MINIO_BUCKET_OUTPUTS', 'outputs')
        self.splits_bucket = os.getenv('MINIO_BUCKET_SPLITS', 'splits')
        
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
        buckets = [self.uploads_bucket, self.outputs_bucket, self.splits_bucket]
        
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
            user_id: User/session ID for organization
            
        Returns:
            Tuple of (success, file_id, storage_path)
        """
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Create storage path with user organization
            storage_path = f"{user_id}/{file_id}_{file_name}"
            
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
            user_id: User/session ID
            bucket_type: 'outputs' or 'splits'
            
        Returns:
            Tuple of (success, storage_path)
        """
        try:
            bucket = self.outputs_bucket if bucket_type == 'outputs' else self.splits_bucket
            storage_path = f"{user_id}/{filename}"
            
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
    
    def list_files(self, user_id: str, bucket_type: str = 'uploads') -> List[Dict[str, Any]]:
        """List files for a specific user"""
        try:
            if bucket_type == 'uploads':
                bucket = self.uploads_bucket
            elif bucket_type == 'outputs':
                bucket = self.outputs_bucket
            else:
                bucket = self.splits_bucket
            
            # List objects with user prefix
            objects = self.client.list_objects(bucket, prefix=f"{user_id}/", recursive=True)
            
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
                json.dump(metadata, f, indent=2)
            
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
    
    def get_user_files(self, user_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Get all files for a specific user, returns (success, files_list, error_msg)"""
        try:
            # Load all metadata files for this user
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
                        
                        # Filter by user_id
                        if metadata.get('user_id') == user_id:
                            # Map to expected format
                            file_record = {
                                'id': metadata['file_id'],
                                'file_id': metadata['file_id'],
                                'original_name': metadata['original_name'], 
                                'file_name': metadata['original_name'],
                                'file_type': metadata['file_type'],
                                'file_size': metadata['file_size'],
                                'storage_path': metadata['storage_path'],
                                'file_path': metadata['storage_path'],
                                'user_id': metadata['user_id'],
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
                json.dump(conversion_metadata, f, indent=2)
            
            return True, conversion_id
            
        except Exception as e:
            return False, str(e)
    
    def get_conversion_record(self, file_id: str, output_format: str, user_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Get conversion record by file_id and output_format"""
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
                        
                        # Check if this matches our criteria
                        if (conversion.get('file_id') == file_id and 
                            conversion.get('output_format') == output_format and
                            conversion.get('user_id') == user_id):
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
            # Create storage path with user organization
            storage_path = f"{user_id}/{file_name}"
            
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
