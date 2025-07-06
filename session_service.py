"""
Session Service for Document Converter v2.0
Handles session-based file isolation without user registration
"""

import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import session, request
import hashlib

class SessionService:
    """Service class for handling user sessions and file isolation"""
    
    def __init__(self, session_dir: str = "sessions"):
        """Initialize session service"""
        self.session_dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
        self.session_timeout = timedelta(hours=24)  # 24 hour session timeout
    
    def get_or_create_session_id(self) -> str:
        """Get existing session ID or create a new one"""
        if 'session_id' not in session:
            # Create new session ID
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            session['created_at'] = datetime.now().isoformat()
            
            # Create session metadata file
            self._create_session_metadata(session_id)
        else:
            session_id = session['session_id']
            # Check if session is still valid
            if not self._is_session_valid(session_id):
                # Create new session if expired
                session_id = str(uuid.uuid4())
                session['session_id'] = session_id
                session['created_at'] = datetime.now().isoformat()
                self._create_session_metadata(session_id)
        
        return session_id
    
    def get_session_id(self) -> Optional[str]:
        """Get current session ID without creating new one"""
        return session.get('session_id')
    
    def _create_session_metadata(self, session_id: str):
        """Create session metadata file"""
        try:
            metadata = {
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat(),
                'user_agent': request.headers.get('User-Agent', ''),
                'ip_address': self._get_client_ip(),
                'files_uploaded': 0,
                'files_converted': 0,
                'total_file_size': 0
            }
            
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            with open(session_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not create session metadata: {e}")
    
    def _is_session_valid(self, session_id: str) -> bool:
        """Check if session is still valid"""
        try:
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            if not os.path.exists(session_file):
                return False
            
            with open(session_file, 'r') as f:
                metadata = json.load(f)
            
            created_at = datetime.fromisoformat(metadata['created_at'])
            if datetime.now() - created_at > self.session_timeout:
                return False
            
            return True
        except Exception:
            return False
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp"""
        try:
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    metadata = json.load(f)
                
                metadata['last_activity'] = datetime.now().isoformat()
                
                with open(session_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not update session activity: {e}")
    
    def increment_file_counter(self, session_id: str, counter_type: str, file_size: int = 0):
        """Increment file counters for session"""
        try:
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    metadata = json.load(f)
                
                if counter_type == 'upload':
                    metadata['files_uploaded'] = metadata.get('files_uploaded', 0) + 1
                    metadata['total_file_size'] = metadata.get('total_file_size', 0) + file_size
                elif counter_type == 'convert':
                    metadata['files_converted'] = metadata.get('files_converted', 0) + 1
                
                metadata['last_activity'] = datetime.now().isoformat()
                
                with open(session_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not update file counter: {e}")
    
    def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Get session metadata"""
        try:
            session_file = os.path.join(self.session_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {}
    
    def get_session_files_dir(self, session_id: str) -> str:
        """Get session-specific directory for file storage"""
        session_files_dir = os.path.join("uploads", session_id)
        os.makedirs(session_files_dir, exist_ok=True)
        return session_files_dir
    
    def get_session_outputs_dir(self, session_id: str) -> str:
        """Get session-specific directory for output storage"""
        session_outputs_dir = os.path.join("outputs", session_id)
        os.makedirs(session_outputs_dir, exist_ok=True)
        return session_outputs_dir
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions and their files"""
        try:
            current_time = datetime.now()
            
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # Remove .json extension
                    
                    try:
                        with open(os.path.join(self.session_dir, filename), 'r') as f:
                            metadata = json.load(f)
                        
                        created_at = datetime.fromisoformat(metadata['created_at'])
                        if current_time - created_at > self.session_timeout:
                            # Session expired, clean up
                            self._cleanup_session_files(session_id)
                            os.remove(os.path.join(self.session_dir, filename))
                            print(f"Cleaned up expired session: {session_id}")
                    
                    except Exception as e:
                        print(f"Error cleaning up session {session_id}: {e}")
        
        except Exception as e:
            print(f"Error during session cleanup: {e}")
    
    def _cleanup_session_files(self, session_id: str):
        """Remove all files associated with a session"""
        try:
            # Clean up uploads
            session_uploads = os.path.join("uploads", session_id)
            if os.path.exists(session_uploads):
                import shutil
                shutil.rmtree(session_uploads)
            
            # Clean up outputs
            session_outputs = os.path.join("outputs", session_id)
            if os.path.exists(session_outputs):
                import shutil
                shutil.rmtree(session_outputs)
                
        except Exception as e:
            print(f"Error cleaning up session files for {session_id}: {e}")
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        active_sessions = []
        try:
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]
                    if self._is_session_valid(session_id):
                        metadata = self.get_session_metadata(session_id)
                        active_sessions.append(metadata)
        except Exception as e:
            print(f"Error listing active sessions: {e}")
        
        return active_sessions
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        if request.environ.get('HTTP_X_FORWARDED_FOR'):
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
        elif request.environ.get('HTTP_X_REAL_IP'):
            return request.environ['HTTP_X_REAL_IP']
        else:
            return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def generate_session_hash(self, session_id: str) -> str:
        """Generate a short hash for session identification"""
        return hashlib.md5(session_id.encode()).hexdigest()[:8]
