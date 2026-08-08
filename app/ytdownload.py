import os
import time
import requests
import re
import urllib.parse
import logging

def extract_video_id(url):
    pattern = r'(?:v=|\/|youtu\.be\/|embed\/|e\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def run_download_task(task_id, url, format_type, quality):
    task = {
        'task_id': task_id,
        'url': url,
        'status': 'processing',
        'percent': 0,
        'created_at': time.time()
    }

    video_id = extract_video_id(url)
    if not video_id:
        task.update({'status': 'failed', 'error': 'Could not extract video ID from URL.'})
        return task

    RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "3dff6e8761msha141d00a722452fp1719a7jsndbf50dbb5dbd")
    RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "youtube-media-downloader.p.rapidapi.com")

    api_url = f"https://{RAPIDAPI_HOST}/v2/video/details?videoId={video_id}"
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": RAPIDAPI_KEY}

    try:
        response = requests.get(api_url, headers=headers, timeout=20)
        if response.status_code == 403:
            task.update({'status': 'failed', 'error': 'RapidAPI Subscription Required.'})
            return task
        elif response.status_code != 200:
            task.update({'status': 'failed', 'error': f'RapidAPI returned error: {response.status_code}'})
            return task

        data = response.json()
        videos = data.get('videos', {}).get('items', [])
        
        if not videos:
            task.update({'status': 'failed', 'error': 'No video streams found.'})
            return task

        videos_with_audio = [v for v in videos if v.get('hasAudio')]
        if not videos_with_audio:
            best_video = videos[0]
        else:
            def quality_val(v):
                q = v.get('quality', '0p')
                match = re.search(r'\d+', q)
                return int(match.group()) if match else 0
                
            videos_with_audio.sort(key=quality_val, reverse=True)
            best_video = videos_with_audio[0]

        download_url = best_video.get('url')
        if not download_url:
            task.update({'status': 'failed', 'error': 'Failed to extract URL from RapidAPI response.'})
            return task

        title = data.get('title', 'video')
        safe_title = re.sub(r'[\\/:*?"<>|\'\`]', '', title)
        filename = f"{safe_title}.mp4"

        task.update({
            'status': 'ready',
            'percent': 100.0,
            'download_url': download_url,
            'filename': filename,
            'title': title
        })
        return task

    except Exception as e:
        import traceback
        logging.error(f"RapidAPI request failed: {traceback.format_exc()}")
        task.update({'status': 'failed', 'error': str(e)})
        return task
