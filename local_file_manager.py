"""
Local File Manager for Document Converter v2.0
Handles file operations in local mode with session isolation
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import mimetypes

class LocalFileManager:
    """File manager for local storage with session isolation"""
    
    def __init__(self, base_upload_dir: str = "uploads", base_output_dir: str = "outputs"):
        """Initialize local file manager"""
        self.base_upload_dir = base_upload_dir
        self.base_output_dir = base_output_dir
        self.metadata_dir = "file_metadata"
        
        # Create base directories
        os.makedirs(base_upload_dir, exist_ok=True)
        os.makedirs(base_output_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
    
    def save_file(self, file_content: bytes, filename: str, session_id: str) -> Tuple[bool, str, str]:
        """
        Save file to session-specific directory
        Returns: (success, file_id, file_path)
        """
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Get file extension
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            stored_filename = f"{file_id}.{file_extension}"
            
            # Create session directory
            session_dir = os.path.join(self.base_upload_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(session_dir, stored_filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Create metadata
            metadata = {
                'file_id': file_id,
                'session_id': session_id,
                'original_name': filename,
                'stored_filename': stored_filename,
                'file_path': file_path,
                'file_type': file_extension,
                'file_size': len(file_content),
                'mime_type': mimetypes.guess_type(filename)[0],
                'upload_time': datetime.now().isoformat(),
                'upload_status': 'completed'
            }
            
            # Save metadata
            metadata_file = os.path.join(self.metadata_dir, f"{file_id}.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True, file_id, file_path
            
        except Exception as e:
            return False, f"Save error: {str(e)}", ""
    
    def get_file(self, file_id: str) -> Tuple[bool, bytes, str]:
        """
        Get file content by file ID
        Returns: (success, file_content, error_message)
        """
        try:
            # Get metadata
            success, metadata, error_msg = self.get_file_metadata(file_id)
            if not success:
                return False, b"", error_msg
            
            # Read file
            file_path = metadata['file_path']
            if not os.path.exists(file_path):
                return False, b"", "File not found on disk"
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return True, content, ""
            
        except Exception as e:
            return False, b"", f"Read error: {str(e)}"
    
    def get_file_metadata(self, file_id: str, session_id: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get file metadata by file ID and session ID
        Returns: (success, metadata, error_message)
        """
        try:
            metadata_file = os.path.join(self.metadata_dir, f"{file_id}.json")
            
            if not os.path.exists(metadata_file):
                return False, {}, "File metadata not found"
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Verify session ownership
            if metadata.get('session_id') != session_id:
                return False, {}, "File not found in current session"
            
            return True, metadata, ""
            
        except Exception as e:
            return False, {}, f"Metadata read error: {str(e)}"
    
    def save_converted_file(self, file_content: bytes, original_file_id: str, output_format: str, session_id: str) -> Tuple[bool, str, str]:
        """
        Save converted file to session-specific output directory
        Returns: (success, output_file_id, file_path)
        """
        try:
            # Generate unique file ID for converted file
            output_file_id = str(uuid.uuid4())
            
            # Create session output directory
            session_output_dir = os.path.join(self.base_output_dir, session_id)
            os.makedirs(session_output_dir, exist_ok=True)
            
            # Save converted file
            output_filename = f"{original_file_id}.{output_format}"
            output_path = os.path.join(session_output_dir, output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(file_content)
            
            # Create conversion metadata
            conversion_metadata = {
                'output_file_id': output_file_id,
                'original_file_id': original_file_id,
                'session_id': session_id,
                'output_format': output_format,
                'output_path': output_path,
                'output_filename': output_filename,
                'file_size': len(file_content),
                'created_at': datetime.now().isoformat(),
                'type': 'converted'
            }
            
            # Save conversion metadata
            conversion_metadata_file = os.path.join(self.metadata_dir, f"{output_file_id}_conversion.json")
            with open(conversion_metadata_file, 'w') as f:
                json.dump(conversion_metadata, f, indent=2)
            
            return True, output_file_id, output_path
            
        except Exception as e:
            return False, str(e), ""
    
    def get_converted_file_path(self, file_id: str, session_id: str) -> Tuple[bool, str, str, str]:
        """
        Get converted file path for download
        Returns: (success, file_path, filename, error_message)
        """
        try:
            # Look for conversion metadata
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('_conversion.json'):
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    if (metadata.get('original_file_id') == file_id and 
                        metadata.get('session_id') == session_id and
                        metadata.get('type') == 'converted'):
                        
                        file_path = metadata['output_path']
                        if os.path.exists(file_path):
                            return True, file_path, metadata['output_filename'], ""
            
            return False, "", "", "Converted file not found"
            
        except Exception as e:
            return False, "", "", f"Error finding converted file: {str(e)}"
    
    def get_split_file_path(self, file_id: str, session_id: str) -> Tuple[bool, str, str, str]:
        """
        Get split file path for download
        Returns: (success, file_path, filename, error_message)
        """
        try:
            # Look for split metadata
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('_split.json'):
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    if (metadata.get('original_file_id') == file_id and 
                        metadata.get('session_id') == session_id and
                        metadata.get('type') == 'split'):
                        
                        file_path = metadata['output_path']
                        if os.path.exists(file_path):
                            return True, file_path, metadata['output_filename'], ""
            
            return False, "", "", "Split file not found"
            
        except Exception as e:
            return False, "", "", f"Error finding split file: {str(e)}"
    
    def list_session_files(self, session_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        List all files in a session
        Returns: (success, files_list, error_message)
        """
        try:
            files = []
            
            # Scan metadata directory for files belonging to this session
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('.json') and not filename.endswith('_conversion.json') and not filename.endswith('_split.json'):
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        if metadata.get('session_id') == session_id:
                            # Add conversion information
                            conversions = []
                            
                            # Look for conversions
                            for conv_filename in os.listdir(self.metadata_dir):
                                if conv_filename.endswith('_conversion.json'):
                                    conv_path = os.path.join(self.metadata_dir, conv_filename)
                                    with open(conv_path, 'r') as f:
                                        conv_metadata = json.load(f)
                                    
                                    if conv_metadata.get('original_file_id') == metadata['file_id']:
                                        conversions.append({
                                            'output_file_id': conv_metadata['output_file_id'],
                                            'output_format': conv_metadata['output_format'],
                                            'created_at': conv_metadata['created_at'],
                                            'file_size': conv_metadata['file_size']
                                        })
                            
                            metadata['conversions'] = conversions
                            files.append(metadata)
                            
                    except Exception as e:
                        continue  # Skip corrupted metadata files
            
            return True, files, ""
            
        except Exception as e:
            return False, [], f"Error listing files: {str(e)}"
    
    def get_session_statistics(self, session_id: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get statistics for a session
        Returns: (success, statistics, error_message)
        """
        try:
            stats = {
                'file_count': 0,
                'conversion_count': 0,
                'total_file_size': 0,
                'session_id': session_id
            }
            
            # Count files and conversions
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('.json'):
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        if metadata.get('session_id') == session_id:
                            if filename.endswith('_conversion.json'):
                                stats['conversion_count'] += 1
                            elif not filename.endswith('_split.json'):
                                stats['file_count'] += 1
                                stats['total_file_size'] += metadata.get('file_size', 0)
                                
                    except Exception:
                        continue
            
            return True, stats, ""
            
        except Exception as e:
            return False, {}, f"Error getting statistics: {str(e)}"
    
    def cleanup_session_data(self, session_id: str) -> Tuple[bool, str]:
        """Clean up all data for a session"""
        try:
            cleaned_files = 0
            
            # Clean up files and metadata
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(self.metadata_dir, filename), 'r') as f:
                            metadata = json.load(f)
                        
                        if metadata.get('session_id') == session_id:
                            # Delete actual file if it exists
                            if 'file_path' in metadata and os.path.exists(metadata['file_path']):
                                os.remove(metadata['file_path'])
                            
                            if 'output_path' in metadata and os.path.exists(metadata['output_path']):
                                os.remove(metadata['output_path'])
                            
                            # Delete metadata
                            os.remove(os.path.join(self.metadata_dir, filename))
                            cleaned_files += 1
                    except Exception:
                        continue
            
            # Clean up session directories
            session_upload_dir = os.path.join(self.base_upload_dir, session_id)
            if os.path.exists(session_upload_dir):
                shutil.rmtree(session_upload_dir)
            
            session_output_dir = os.path.join(self.base_output_dir, session_id)
            if os.path.exists(session_output_dir):
                shutil.rmtree(session_output_dir)
            
            return True, f"Cleaned up {cleaned_files} files"
            
        except Exception as e:
            return False, f"Cleanup error: {str(e)}"
    
    def delete_file(self, file_id: str, session_id: str) -> Tuple[bool, str]:
        """
        Delete a file and all its associated data
        Returns: (success, error_message)
        """
        try:
            # Get file metadata
            success, metadata, error_msg = self.get_file_metadata(file_id, session_id)
            if not success:
                return False, error_msg
            
            # Delete the actual file
            file_path = metadata['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete file metadata
            metadata_file = os.path.join(self.metadata_dir, f"{file_id}.json")
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            
            # Delete conversion files and metadata
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('_conversion.json'):
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    try:
                        with open(metadata_path, 'r') as f:
                            conv_metadata = json.load(f)
                        
                        if conv_metadata.get('original_file_id') == file_id and conv_metadata.get('session_id') == session_id:
                            # Delete conversion output file
                            output_path = conv_metadata.get('output_path')
                            if output_path and os.path.exists(output_path):
                                os.remove(output_path)
                            
                            # Delete conversion metadata
                            os.remove(metadata_path)
                    except Exception:
                        continue
            
            # Delete split files and metadata
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('_split.json'):
                    metadata_path = os.path.join(self.metadata_dir, filename)
                    try:
                        with open(metadata_path, 'r') as f:
                            split_metadata = json.load(f)
                        
                        if split_metadata.get('original_file_id') == file_id and split_metadata.get('session_id') == session_id:
                            # Delete split output file
                            output_path = split_metadata.get('output_path')
                            if output_path and os.path.exists(output_path):
                                os.remove(output_path)
                            
                            # Delete split metadata
                            os.remove(metadata_path)
                    except Exception:
                        continue
            
            return True, ""
            
        except Exception as e:
            return False, f"Delete error: {str(e)}"
