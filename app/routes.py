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

    logging.info("Imported run_download_task successfully!")
    # Run download synchronously. 
    # run_download_task initializes the state internally, making it immune to dictionary desyncs
    task = run_download_task(task_id, url, 'video', '1080p')
    logging.info(f"run_download_task finished! Task: {task}")
    
    if not task or task.get('status') != 'ready':
        error_msg = task.get('error') if task else 'Download failed'
        if not error_msg:
            error_msg = 'Download failed'
        
        with open("flask_routes_task.txt", "w") as f:
            f.write(str(task))
            
        return jsonify({'error': str(error_msg)}), 500

    download_url = task.get('download_url')
    filename = task.get('filename', 'video.mp4')
    
    if not download_url:
        return jsonify({'error': 'Failed to get download URL from API'}), 500

    return jsonify({
        'download_url': download_url,
        'filename': filename
    })

@app.route('/downloadVideoProxy', methods=['GET'])
def proxy_download():
    """GET endpoint that extracts the direct video URL and proxies the video stream to the client."""
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    if not re.search(r'(?:youtube\.com|youtu\.be|youtube-nocookie\.com)', url):
        return jsonify({'error': 'Only YouTube URLs are supported'}), 400

    task_id = str(uuid.uuid4())
    try:
        from app.ytdownload import run_download_task
    except ImportError:
        from ytdownload import run_download_task

    # Extract URL synchronously
    task = run_download_task(task_id, url, 'video', '1080p')
    
    if not task or task.get('status') != 'ready':
        error_msg = task.get('error') if task else 'Download failed'
        return jsonify({'error': str(error_msg)}), 500

    download_url = task.get('download_url')
    filename = task.get('filename', 'video.mp4')
    
    if not download_url:
        return jsonify({'error': 'Failed to extract download URL'}), 404

    from flask import Response
    
    try:
        req = requests.get(download_url, stream=True)
        
        def generate():
            for chunk in req.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk
                    
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': req.headers.get('Content-Type', 'video/mp4')
        }
        if 'Content-Length' in req.headers:
            headers['Content-Length'] = req.headers['Content-Length']
            
        return Response(generate(), headers=headers)
    except Exception as e:
        logging.error(f"Error proxying stream: {e}")
        return jsonify({'error': 'Error proxying stream'}), 500

@app.route('/streamUrl', methods=['GET'])
def stream_url():
    """Proxies an already extracted download_url to the client with Content-Disposition attachment."""
    url = request.args.get('url', '').strip()
    filename = request.args.get('filename', 'video.mp4').strip()
    
    if not filename.lower().endswith('.mp4'):
        filename += '.mp4'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    from flask import Response
    import requests
    
    try:
        req = requests.get(url, stream=True)
        
        def generate():
            for chunk in req.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk
                    
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': req.headers.get('Content-Type', 'video/mp4')
        }
        if 'Content-Length' in req.headers:
            headers['Content-Length'] = req.headers['Content-Length']
            
        return Response(generate(), headers=headers)
    except Exception as e:
        logging.error(f"Error proxying stream: {e}")
        return jsonify({'error': 'Error proxying stream'}), 500

@app.route('/downloadLocal', methods=['GET'])
def download_local():
    """Serves the locally downloaded and merged MP4 file to the client."""
    from flask import send_file
    
    task_id = request.args.get('task_id', '').strip()
    filename = request.args.get('filename', 'video.mp4').strip()
    
    if not filename.lower().endswith('.mp4'):
        filename += '.mp4'
        
    if not task_id:
        return jsonify({'error': 'task_id is required'}), 400
        
    from app.ytdownload import download_tasks
    task = download_tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found or expired'}), 404
        
    filepath = task.get('filepath')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found on server'}), 404
        
    try:
        # Use send_file to stream the local file efficiently
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    except Exception as e:
        logging.error(f"Error serving local file: {e}")
        return jsonify({'error': 'Error serving file'}), 500