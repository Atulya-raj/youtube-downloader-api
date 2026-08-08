import os
import shutil
import base64
import tempfile
import yt_dlp
import sys

def main():
    print("="*60)
    print("YouTube OAuth2 Generator for Render")
    print("="*60)
    print("This script will prompt you to log into YouTube.")
    print("Once logged in, it will generate a Base64 string that you must")
    print("paste into your Render Environment Variables.")
    print("="*60)
    
    # We will use a temporary directory to keep things clean
    temp_dir = tempfile.mkdtemp()
    cache_dir = os.path.join(temp_dir, '.yt-dlp-cache')
    
    ydl_opts = {
        'cachedir': cache_dir,
        'username': 'oauth2',
        'password': '',
        'quiet': False, # We want to see the login prompt
    }
    
    print("\n[Action Required] Look closely at the terminal output below.")
    print("yt-dlp will provide a link (google.com/device) and a CODE.")
    print("Open the link in your browser, enter the code, and sign in.")
    print("Waiting for authentication...\n")
    
    try:
        # Extract info for a tiny dummy video just to trigger the login flow
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Using a very short, generic video just to force authentication
            ydl.extract_info('https://www.youtube.com/watch?v=BaW_jenozKc', download=False)
            
        print("\n\n✅ Authentication Successful!")
        print("Packaging your secure tokens...")
        
        # Zip the cache directory
        zip_path = os.path.join(temp_dir, 'yt_cache')
        shutil.make_archive(zip_path, 'zip', cache_dir)
        
        # Read the zip file and encode to base64
        with open(f"{zip_path}.zip", 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
            
        print("\n" + "="*80)
        print("YOUR RENDER ENVIRONMENT VARIABLE VALUE:")
        print("="*80 + "\n")
        print(b64_data)
        print("\n" + "="*80)
        print("INSTRUCTIONS:")
        print("1. Copy the ENTIRE massive block of text above (it's very long!).")
        print("2. Go to your Render Dashboard -> Environment.")
        print("3. Create a new variable named: YOUTUBE_OAUTH_CACHE_BASE64")
        print("4. Paste the text as the value and save changes.")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == "__main__":
    main()
