import base64
import os
import sys

def main():
    print("="*60)
    print("Cookie Base64 Encoder for Render")
    print("="*60)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_path = os.path.join(current_dir, 'cookies.txt')
    
    if not os.path.exists(cookies_path):
        print(f"❌ Error: Could not find 'cookies.txt' in {current_dir}")
        print("Please make sure you have exported your YouTube cookies and saved them as 'cookies.txt' in this folder.")
        sys.exit(1)
        
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies_content = f.read()
            
        b64_data = base64.b64encode(cookies_content.encode('utf-8')).decode('utf-8')
        
        print("\n✅ Successfully encoded cookies.txt!")
        print("\n" + "="*80)
        print("YOUR RENDER ENVIRONMENT VARIABLE VALUE:")
        print("="*80 + "\n")
        print(b64_data)
        print("\n" + "="*80)
        print("INSTRUCTIONS:")
        print("1. Copy the ENTIRE massive block of text above.")
        print("2. Go to your Render Dashboard -> Environment.")
        print("3. Create a new variable named: YOUTUBE_COOKIES_BASE64")
        print("4. Paste the text as the value and save changes.")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error reading or encoding cookies: {e}")

if __name__ == "__main__":
    main()
