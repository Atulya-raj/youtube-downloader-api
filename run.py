import os
import sys

# Add the parent directory to the python path so the 'app' module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    # You can change the port here if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
