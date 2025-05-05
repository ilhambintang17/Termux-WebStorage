import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///termux_nas.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Storage configuration
    STORAGE_PATH = os.environ.get('STORAGE_PATH') or '/data/data/com.termux/files/home/nasmux'

    # File upload configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE') or 50 * 1024 * 1024 * 1024)  # 50GB default

    # Sharing configuration
    SHARE_LINK_EXPIRY = int(os.environ.get('SHARE_LINK_EXPIRY') or 7)  # 7 days default

    # Network configuration
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)

    # Authentication
    AUTH_REQUIRED = os.environ.get('AUTH_REQUIRED', 'True').lower() in ('true', 'yes', '1')

    # Theme
    DEFAULT_THEME = os.environ.get('DEFAULT_THEME') or 'light'  # 'light' or 'dark'
