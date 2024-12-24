import os

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'  # For Gmail
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your-email@gmail.com'  # Replace with your Gmail address
MAIL_PASSWORD = 'your-app-password'  # Replace with your Gmail app password
MAIL_DEFAULT_SENDER = 'your-email@gmail.com'  # Replace with your Gmail address

# Secret key for session management
# Generate a secure key in production!
SECRET_KEY = 'your-secret-key-here'

# Database Configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///reservations.db'

# Upload Configuration
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max file size
UPLOAD_FOLDER = os.path.join('static', 'images', 'rooms')
