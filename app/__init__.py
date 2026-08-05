from flask import Flask
from flask_cors import CORS
import os
import logging

app = Flask(__name__, static_folder='../public', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.config['WORKING_DIRECTORY'] = current_dir

# Setup logging
os.makedirs(os.path.join(current_dir, 'logs'), exist_ok=True)
logging.basicConfig(filename=os.path.join(current_dir, 'logs/error.log'), level=logging.INFO)

# Write YouTube cookies to a file if provided in environment variables
cookies_env = os.environ.get('YOUTUBE_COOKIES')
if cookies_env:
    cookies_path = os.path.join(current_dir, 'cookies.txt')
    with open(cookies_path, 'w') as f:
        f.write(cookies_env)
        
# Import routes at the end to avoid circular dependencies
from app import routes
