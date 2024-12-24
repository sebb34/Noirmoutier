import os
import secrets

# Flask configuration
SECRET_KEY = secrets.token_hex(32)  # Generates a secure random key
SQLALCHEMY_DATABASE_URI = 'sqlite:///reservations.db'  # Changed to match existing database
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Upload configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Mail configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = None  # We'll set this up later if needed
MAIL_PASSWORD = None  # We'll set this up later if needed
MAIL_DEFAULT_SENDER = None  # We'll set this up later if needed
