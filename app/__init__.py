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

# Import routes at the end to avoid circular dependencies
from app import routes
