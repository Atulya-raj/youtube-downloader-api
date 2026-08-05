import os
import uuid
import threading
import time
import re
import shutil
import glob
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template_string
from flask_cors import CORS
import yt_dlp
from datetime import date
import datetime
import logging

# Disable Werkzeug logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Maximum concurrent downloads allowed
MAX_CONCURRENT_DOWNLOADS = 5

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# In-memory storage for active/completed download tasks
download_tasks = {}

def clean_old_files():
    """Background thread to remove temporary files older than 1 hour."""
    while True:
        time.sleep(300)  # Check every 5 mins
        now = time.time()
        for task_id, task in list(download_tasks.items()):
            file_path = task.get('filepath')
            created_at = task.get('created_at', now)
            if now - created_at > 3600:  # 1 hour expiration
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error removing expired file {file_path}: {e}")
                download_tasks.pop(task_id, None)

cleanup_thread = threading.Thread(target=clean_old_files, daemon=True)
cleanup_thread.start()


def get_ffmpeg_path():
    """Find ffmpeg executable path from project root, bin folder, static-ffmpeg package, or system PATH."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Check for ffmpeg.exe or ffmpeg in project directory or bin directory
    for path in [
        os.path.join(base_dir, 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg'),
        os.path.join(base_dir, 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'bin', 'ffmpeg')
    ]:
        if os.path.exists(path):
            return path

    # 2. Try static-ffmpeg python package if installed via pip
    try:
        import static_ffmpeg
        ffmpeg_bin, _ = static_ffmpeg.run.get_or_fetch_platform_executables_or_raise()
        if ffmpeg_bin and os.path.exists(ffmpeg_bin):
            return ffmpeg_bin
    except Exception:
        pass

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

    # 3. Fallback to system PATH
    sys_ffmpeg = shutil.which('ffmpeg')
    if sys_ffmpeg:
        return sys_ffmpeg

    return None


def sanitize_filename(name):
    """Remove characters illegal in Windows filenames and trim to safe length."""
    if not name:
        return 'video'
    # Remove characters illegal on Windows: \ / : * ? " < > | ' `
    sanitized = re.sub(r'[\\/:*?"<>|\'\`]', '', name)
    # Also remove control characters and leading/trailing dots/spaces
    sanitized = re.sub(r'[\x00-\x1f]', '', sanitized).strip('. ')
    # Limit length to 80 chars to avoid path-too-long errors
    if len(sanitized) > 80:
        sanitized = sanitized[:80].rstrip('. ')
    return sanitized or 'video'


def format_duration(seconds):
    if not seconds:
        return 'Unknown'
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_filesize(size_bytes):
    """Convert bytes to human-readable file size string."""
    if not size_bytes or size_bytes <= 0:
        return 'Unknown'
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"



def run_download_task(task_id, url, format_type, quality):
    task = download_tasks.get(task_id)
    if not task:
        task = {
            'task_id': task_id,
            'url': url,
            'status': 'queued',
            'percent': 0,
            'created_at': time.time()
        }
        download_tasks[task_id] = task

    task.update({
        'status': 'downloading',
        'speed': 'Connecting & resolving streams...',
        'percent': 0.0
    })

    # Use task_id as primary filename to avoid illegal character issues on Windows
    # The actual video title is stored in task metadata for display purposes
    def progress_hook(d):
        try:
            if d.get('status') == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta')

                # If total_bytes is 0 (fragmented downloads), fallback to fragment count if present
                if total_bytes <= 0 and d.get('fragment_count'):
                    frag_index = d.get('fragment_index', 0)
                    frag_count = d.get('fragment_count', 1)
                    calculated_percent = round((frag_index / frag_count * 100), 1)
                else:
                    calculated_percent = round((downloaded / total_bytes * 100), 1) if total_bytes > 0 else 0

                # Maintain monotonic percentage so dual-stream (video + audio) downloads never drop back to 0%
                current_percent = task.get('percent', 0.0)
                if current_percent >= 99.0:
                    percent = 99.0
                else:
                    percent = max(current_percent, calculated_percent)

                speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed else "Downloading..."
                try:
                    eta_str = f"{int(eta)}s" if eta is not None else "--"
                except (ValueError, TypeError):
                    eta_str = "--"

                task.update({
                    'status': 'downloading',
                    'percent': percent,
                    'speed': speed_str,
                    'eta': eta_str,
                    'downloaded_bytes': downloaded,
                    'total_bytes': total_bytes
                })
            elif d.get('status') == 'finished':
                task.update({
                    'status': 'processing',
                    'percent': 99.0,
                    'speed': 'Merging MP4...',
                    'eta': '0s'
                })
        except Exception as err:
            print(f"Error in progress hook: {err}")

    ffmpeg_path = get_ffmpeg_path()
    
    ydl_opts = {
        'paths': {'home': DOWNLOAD_DIR},
        'outtmpl': {'default': f"{task_id}.%(ext)s"},
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'js_runtimes': {'node': {}},
        'extractor_args': {'youtube': ['client=ios,android']},
    }
    
    # Use cookies if available to bypass YouTube's datacenter IP block
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cookies_path = os.path.join(current_dir, 'cookies.txt')
    if os.path.exists(cookies_path):
        ydl_opts['cookiefile'] = cookies_path
    
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path

    has_ffmpeg = ffmpeg_path is not None

    if format_type == 'audio':
        if has_ffmpeg:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'bestaudio/best',
            })
    else:
        match = re.search(r'\d+', str(quality or '1080'))
        target_height = min(int(match.group()), 1080) if match else 1080
        if has_ffmpeg:
            ydl_opts['format'] = (
                f"bestvideo[height={target_height}]+bestaudio/"
                f"bestvideo[height<={target_height}]+bestaudio/"
                f"best[height={target_height}]/"
                f"best[height<={target_height}]/best"
            )
            ydl_opts['merge_output_format'] = 'mp4'
        else:
            ydl_opts['format'] = (
                f"best[height={target_height}][ext=mp4]/"
                f"best[height={target_height}]/"
                f"best[height<={target_height}]"
            )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Find actual completed downloaded file on disk matching task_id
            target_file = None
            matches = glob.glob(os.path.join(DOWNLOAD_DIR, f"{task_id}.*"))
            for m in matches:
                if not m.endswith('.part') and not m.endswith('.ytdl'):
                    target_file = m
                    break

            if not target_file:
                target_file = os.path.join(DOWNLOAD_DIR, f"{task_id}.mp4")

            video_title = sanitize_filename(info.get('title', 'video'))
            file_ext = os.path.splitext(target_file)[1] or '.mp4'
            clean_filename = f"{video_title}{file_ext}"

            task.update({
                'status': 'ready',
                'percent': 100.0,
                'filepath': target_file,
                'filename': clean_filename,
                'title': info.get('title', 'video')
            })
            return task
    except Exception as e:
        import traceback
        import sys
        
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        error_msg = (
            f"\n{'='*50}\n"
            f"TIMESTAMP: {datetime.datetime.now()}\n"
            f"TASK ID: {task_id}\n"
            f"URL REQUESTED: {url}\n"
            f"FULL ERROR TRACEBACK:\n{tb_str}"
            f"{'='*50}\n"
        )
        
        print(f"DOWNLOAD TASK EXCEPTION FOR {task_id}:")
        print(error_msg)
        logging.error(error_msg)
        
        task.update({
            'status': 'failed',
            'error': str(e)
        })
        return task