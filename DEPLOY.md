# Deployment Guide - PythonAnywhere

## Pre-deployment Steps

1. Log in to your PythonAnywhere account at https://www.pythonanywhere.com/user/sebb34/
2. Go to the Web tab: https://www.pythonanywhere.com/user/sebb34/webapps/

## Deployment Steps

1. Open a Bash console in PythonAnywhere and run:
```bash
# Clone the repository (if using Git)
git clone https://github.com/YOUR_REPO_URL/Noirmoutier.git

# Or upload files using PythonAnywhere's Files tab
# Then in console, navigate to your directory:
cd /home/sebb34/Noirmoutier

# Create and activate virtual environment
mkvirtualenv --python=/usr/bin/python3.10 noirmoutier-env
workon noirmoutier-env

# Install dependencies
pip install -r requirements.txt
```

2. Create configuration file:
```bash
# Create config.py in the project directory
nano config.py
```

Add the following content (with your actual values):
```python
import os

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'bourrut@gmail.com'
MAIL_PASSWORD = 'your-app-password'  # Your Gmail app password
MAIL_DEFAULT_SENDER = 'bourrut@gmail.com'

# Secret key for session management
SECRET_KEY = 'your-secure-secret-key'  # Change this to a secure random value

# Database Configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:////home/sebb34/Noirmoutier/instance/reservations.db'

# Upload Configuration
MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max file size
UPLOAD_FOLDER = os.path.join('static', 'images', 'rooms')
```

3. Configure the Web App in PythonAnywhere:

- Go to the "Web" tab
- Click "Add a new web app"
- Choose "Manual configuration"
- Choose Python 3.10
- Set the following configuration:
  - Source code: /home/sebb34/Noirmoutier
  - Working directory: /home/sebb34/Noirmoutier
  - Virtual environment: /home/sebb34/.virtualenvs/noirmoutier-env

4. Configure the WSGI file:
- In the Web tab, click on the WSGI configuration file link
- Replace the contents with the contents of your pythonanywhere_wsgi.py file

5. Set up static files in the Web tab:
- Add these static directory mappings:
  - URL: /static/
  - Directory: /home/sebb34/Noirmoutier/static/

6. Initialize the database:
```python
# In PythonAnywhere console
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
...     from app import init_db
...     init_db()
```

7. Create required directories:
```bash
mkdir -p /home/sebb34/Noirmoutier/instance
mkdir -p /home/sebb34/Noirmoutier/static/images/rooms
```

## Post-deployment Steps

1. Test the application by visiting: http://sebb34.pythonanywhere.com
2. Verify email functionality works by testing the password reset
3. Log in with the default admin account and change the password

## Troubleshooting

If you encounter any issues:
1. Check the error logs in the PythonAnywhere web app dashboard
2. Ensure all paths are correct (they should start with /home/sebb34/Noirmoutier)
3. Verify the virtual environment is activated when running commands
4. Check file permissions:
```bash
chmod 755 /home/sebb34/Noirmoutier
chmod 755 /home/sebb34/Noirmoutier/static
chmod 755 /home/sebb34/Noirmoutier/static/images
chmod 755 /home/sebb34/Noirmoutier/static/images/rooms
chmod 664 /home/sebb34/Noirmoutier/instance/reservations.db
