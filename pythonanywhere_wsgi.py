import os
import sys

# Add your project directory to the sys.path
path = '/home/sebb34/Noirmoutier'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
