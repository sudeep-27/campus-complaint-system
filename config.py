import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'campus-voice-secret-key-1029384756'

    # Session configurations
    SESSION_TYPE = 'filesystem'

    # Upload configurations
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB Max Upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    # MySQL Database Configuration (loaded securely from .env)
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD')   # No hardcoded fallback
    DB_NAME = os.environ.get('DB_NAME') or 'campus_complaints'
    DB_PORT = int(os.environ.get('DB_PORT') or 3306)

    # local SQLite Fallback (extreme resilience)
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'campus_complaints.db')
