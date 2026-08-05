from flask import request, jsonify, send_file
from flask_cors import CORS
from app import app
import logging
import os
import time
import uuid
import re
import requests
import subprocess
from app.ytdownload import run_download_task

# In-memory storage for active/completed download tasks
download_tasks = {}

@app.route('/')
def index():
    return f'Welcome to my Flask app! '


@app.route('/ytDownload', methods=['POST'])
def direct_download():
    """Single POST endpoint for production: takes {"url": "..."}, downloads highest quality <= 1080p, and returns file directly in response."""
    data = request.json or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    if not re.search(r'(?:youtube\.com|youtu\.be|youtube-nocookie\.com)', url):
        return jsonify({'error': 'Only YouTube URLs are supported'}), 400

    task_id = str(uuid.uuid4())
    
    # Import gracefully in case the app is run from a different entry point
    try:
        from app.ytdownload import run_download_task
    except ImportError:
        from ytdownload import run_download_task

    # Run download synchronously. 
    # run_download_task initializes the state internally, making it immune to dictionary desyncs
    task = run_download_task(task_id, url, 'video', '1080p')
    
    if not task or task.get('status') != 'ready':
        error_msg = task.get('error') if task else 'Download failed'
        if not error_msg:
            error_msg = 'Download failed'
        return jsonify({'error': str(error_msg)}), 500

    filepath = task.get('filepath')
    filename = task.get('filename', 'video.mp4')

    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File missing on server'}), 404

    import threading
    
    def cleanup_file(path):
        # Wait 5 minutes to ensure the file is fully sent to the client, then delete it
        time.sleep(300)
        try:
            if os.path.exists(path):
                os.remove(path)
                logging.info(f"Cleaned up file: {path}")
        except Exception as e:
            logging.error(f"Failed to cleanup {path}: {e}")

    # Start cleanup thread
    threading.Thread(target=cleanup_file, args=(filepath,), daemon=True).start()

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )