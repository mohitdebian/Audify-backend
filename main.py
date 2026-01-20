import os
import tempfile
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (Fixes browser blocking)
ytmusic = YTMusic()

# --- 1. SMART COOKIE SETUP (Works Locally & on Render) ---
def setup_cookies():
    """
    Locates the cookies file.
    1. Priority: Looks for 'cookies.txt' in the folder (For Local Testing).
    2. Fallback: Looks for 'YOUTUBE_COOKIES' env var (For Render Deployment).
    """
    # Check Local File
    if os.path.exists('cookies.txt'):
        print("✅ Found local 'cookies.txt'. Using it!")
        return 'cookies.txt'
    
    # Check Render Environment Variable
    cookie_content = os.environ.get('YOUTUBE_COOKIES')
    if cookie_content:
        print("✅ Found 'YOUTUBE_COOKIES' env var. Creating temp file!")
        try:
            # Create a secure temporary file for yt-dlp to read
            temp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            temp.write(cookie_content)
            temp.close()
            return temp.name
        except Exception as e:
            print(f"❌ Error creating temp cookie file: {e}")
            return None

    print("⚠️ WARNING: No cookies found. YouTube will likely block this server.")
    return None

COOKIE_FILE_PATH = setup_cookies()

# --- 2. CORE LOGIC: Get Google's Audio URL ---
def get_audio_url(video_id):
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': True,
            'noplaylist': True,
            'extract_flat': False,
            'cookiefile': COOKIE_FILE_PATH,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
            
    except Exception as e:
        print(f"❌ Extraction Error: {e}")
        return None

# --- 3. PROXY STREAM ROUTE (Fixes CORS for Web Apps) ---
@app.route('/stream')
def stream_audio():
    """
    Streams audio through this server with seekbar support.
    Forwards Range headers to Google for proper seeking.
    Usage: <audio src="https://your-app.onrender.com/stream?id=VIDEO_ID" />
    """
    video_id = request.args.get('id')
    if not video_id:
        return "Missing ID", 400

    print(f"🎵 Streaming ID via Proxy: {video_id}")
    
    # A. Get the direct Google link
    google_url = get_audio_url(video_id)
    
    if not google_url:
        return "Failed to fetch stream URL", 404

    # B. Forward the Range header from browser (for seeking)
    headers_to_forward = {}
    if 'Range' in request.headers:
        headers_to_forward['Range'] = request.headers['Range']
        print(f"📍 Seeking with Range: {request.headers['Range']}")

    # C. Stream the data from Google -> Backend -> Frontend
    try:
        req = requests.get(google_url, headers=headers_to_forward, stream=True)
        
        # Build response headers
        response_headers = {
            'Content-Type': req.headers.get('Content-Type', 'audio/mp4'),
            'Access-Control-Allow-Origin': '*',
            'Accept-Ranges': 'bytes'
        }
        
        # Forward Content-Length and Content-Range for seeking
        if 'Content-Length' in req.headers:
            response_headers['Content-Length'] = req.headers['Content-Length']
        if 'Content-Range' in req.headers:
            response_headers['Content-Range'] = req.headers['Content-Range']
        
        # Return 206 Partial Content if Range was requested, else 200
        status_code = 206 if 'Content-Range' in req.headers else 200
        
        return Response(
            stream_with_context(req.iter_content(chunk_size=8192)),
            status=status_code,
            headers=response_headers
        )
                        
    except Exception as e:
        print(f"❌ Proxy Error: {e}")
        return "Stream Proxy Failed", 500

# --- 4. SEARCH ROUTE ---
@app.route('/search', methods=['GET'])
def search_music():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Missing 'query'"}), 400

    print(f"🔍 Searching for: {query}")
    try:
        results = ytmusic.search(query, filter="songs")
        clean_results = []
        
        for song in results[:15]: 
            clean_results.append({
                "videoId": song.get('videoId'),
                "title": song.get('title'),
                "artist": song['artists'][0]['name'] if song.get('artists') else "Unknown",
                "thumbnail": song['thumbnails'][-1]['url'] if song.get('thumbnails') else "",
                "duration": song.get('duration', "")
            })
            
        return jsonify({"status": "success", "results": clean_results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 5. HEALTH CHECK ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Audify Backend is Live!", "platform": "Render/Local"})

if __name__ == '__main__':
    # Run locally
    app.run(host='0.0.0.0', port=5000, debug=True)
