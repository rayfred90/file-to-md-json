"""
Configuration manager for Document Converter v2.0
Handles environment configuration and settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 104857600))  # 100MB default
    UPLOAD_FOLDER = 'uploads'  # Keep for backward compatibility during migration
    OUTPUT_FOLDER = 'outputs'  # Keep for backward compatibility during migration
    
    # MinIO Configuration
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')  # No default value
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
    MINIO_DATA_DIR = os.getenv('MINIO_DATA_DIR', '/home/adebo/con/minio/data')
    
    # MinIO Storage Buckets
    MINIO_BUCKET_UPLOADS = os.getenv('MINIO_BUCKET_UPLOADS', 'uploads')
    MINIO_BUCKET_OUTPUTS = os.getenv('MINIO_BUCKET_OUTPUTS', 'outputs')
    MINIO_BUCKET_SPLITS = os.getenv('MINIO_BUCKET_SPLITS', 'splits')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Application Settings
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'ppt', 'pptx',
        'epub', 'mobi', 'txt', 'md', 'js', 'ts', 'py', 'java', 'cpp',
        'html', 'css', 'json', 'xml', 'yaml', 'yml', 'sql', 'php', 'go', 'rs'
    }
    
    # Text Splitter Configuration
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    MIN_CHUNK_SIZE = 100
    MAX_CHUNK_SIZE = 10000
    MIN_CHUNK_OVERLAP = 0
    MAX_CHUNK_OVERLAP = 1000
    
    AVAILABLE_SPLITTERS = {
        'recursive': 'Recursive Character Splitter',
        'character': 'Character Splitter',
        'token': 'Token Splitter',
        'markdown': 'Markdown Header Splitter',
        'python': 'Python Code Splitter',
        'javascript': 'JavaScript Code Splitter'
    }
    
    OUTPUT_FORMATS = ['md', 'json']
    
    @staticmethod
    def is_supabase_configured():
        """Check if Supabase is properly configured"""
        return bool(Config.SUPABASE_URL and Config.SUPABASE_KEY)
    
    @staticmethod
    def get_storage_mode():
        """Get current storage mode"""
        return 'supabase' if Config.is_supabase_configured() else 'local'
    
    @staticmethod
    def validate_file_extension(filename):
        """Validate if file extension is allowed"""
        if '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in Config.ALLOWED_EXTENSIONS
    
    @staticmethod
    def validate_chunk_size(chunk_size):
        """Validate chunk size"""
        try:
            size = int(chunk_size)
            return Config.MIN_CHUNK_SIZE <= size <= Config.MAX_CHUNK_SIZE
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_chunk_overlap(chunk_overlap):
        """Validate chunk overlap"""
        try:
            overlap = int(chunk_overlap)
            return Config.MIN_CHUNK_OVERLAP <= overlap <= Config.MAX_CHUNK_OVERLAP
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_splitter_type(splitter_type):
        """Validate splitter type"""
        return splitter_type in Config.AVAILABLE_SPLITTERS
    
    @staticmethod
    def validate_output_format(output_format):
        """Validate output format"""
        return output_format in Config.OUTPUT_FORMATS

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on FLASK_ENV"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
