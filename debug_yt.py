import requests
import json

def run_debug_test(video_id="SqXne2oEDX0"): # Rowan Atkinson video
    output = []
    
    RAPIDAPI_KEY = "3dff6e8761msha141d00a722452fp1719a7jsndbf50dbb5dbd"
    RAPIDAPI_HOST = "youtube-media-downloader.p.rapidapi.com"
    
    output.append(f"--- STEP 1: Fetching 1080p Video URL from RapidAPI ---")
    api_url = f"https://{RAPIDAPI_HOST}/v2/video/details?videoId={video_id}"
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": RAPIDAPI_KEY}
    
    response = requests.get(api_url, headers=headers, timeout=20)
    data = response.json()
    
    # Find 1080p video
    videos = data.get('videos', {}).get('items', [])
    video_1080p = next((v for v in videos if '1080p' in v.get('quality', '')), None)
    
    if not video_1080p:
        output.append("No 1080p video stream found.")
        return "\n".join(output)
        
    url_1080p = video_1080p.get('url')
    output.append(f"Found 1080p Video URL (itag {video_1080p.get('itag')})")
    
    output.append(f"\n--- STEP 2: Downloading 1080p Video stream from googlevideo.com ---")
    
    # Prepare the request to googlevideo.com
    # Using a standard user agent
    dl_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # We only want to stream a few bytes to see the response
        dl_response = requests.get(url_1080p, headers=dl_headers, stream=True, timeout=10)
        
        output.append("== REQUEST HEADERS (Sent to GoogleVideo) ==")
        for k, v in dl_response.request.headers.items():
            output.append(f"{k}: {v}")
            
        output.append(f"\n== RESPONSE STATUS ==")
        output.append(f"HTTP Status Code: {dl_response.status_code}")
        
        output.append(f"\n== RESPONSE HEADERS (Received from GoogleVideo) ==")
        for k, v in dl_response.headers.items():
            output.append(f"{k}: {v}")
            
        output.append(f"\n== RESPONSE BODY (First 100 bytes) ==")
        # Read the first 100 bytes
        chunk = next(dl_response.iter_content(chunk_size=100), b'')
        output.append(str(chunk))
        
        if dl_response.status_code == 403:
            output.append("\n!!! YOUTUBE BLOCKED THIS IP (403 FORBIDDEN) !!!")
        elif not chunk:
            output.append("\n!!! YOUTUBE BLOCKED THIS IP (0 BYTES RECEIVED) !!!")
        else:
            output.append("\nSUCCESS: Download started.")
            
    except Exception as e:
        output.append(f"\nError: {e}")
        
    return "\n".join(output)

if __name__ == "__main__":
    print(run_debug_test())
