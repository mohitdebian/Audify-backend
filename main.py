import os
import tempfile
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)
CORS(app)
ytmusic = YTMusic()

# ==============================================================================
# ✅ USER AGENT CONFIGURED
# This matches the browser you used to get the cookies.
# ==============================================================================
MY_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

# --- 1. COOKIE SETUP ---
def setup_cookies():
    # Priority 1: Local file (for testing on your laptop)
    if os.path.exists('cookies.txt'):
        return 'cookies.txt'
    
    # Priority 2: Render Env Var (for production)
    # This reads the Netscape text you pasted in Render
    cookie_content = os.environ.get('YOUTUBE_COOKIES')
    if cookie_content:
        try:
            temp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            temp.write(cookie_content)
            temp.close()
            return temp.name
        except Exception:
            return None
    return None

COOKIE_FILE_PATH = setup_cookies()

# --- 2. EXTRACTION LOGIC ---
def get_audio_url(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'quiet': True,
        'noplaylist': True,
        
        # 1. TELL YOUTUBE WE ARE YOUR LINUX CHROME BROWSER
        'user_agent': MY_USER_AGENT,

        # 2. PROVE WE ARE LOGGED IN
        'cookiefile': COOKIE_FILE_PATH,
        
        # 3. FAKE BROWSER HEADERS
        'http_headers': {
            'User-Agent': MY_USER_AGENT,
            'Referer': 'https://www.youtube.com/',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    try:
        print(f"🍪 Extracting with User-Agent: {MY_USER_AGENT[:30]}...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
            
    except Exception as e:
        print(f"❌ Extraction Failed: {e}")
        return None

# --- 3. PROXY STREAM ---
@app.route('/stream')
def stream_audio():
    video_id = request.args.get('id')
    if not video_id: return "Missing ID", 400

    print(f"🎵 Streaming: {video_id}")
    google_url = get_audio_url(video_id)
    
    if not google_url:
        return jsonify({"error": "YouTube blocked the request. Check Render Logs."}), 403

    try:
        # We must use the SAME User Agent to fetch the actual file
        headers = {'User-Agent': MY_USER_AGENT}
        req = requests.get(google_url, headers=headers, stream=True)
        return Response(stream_with_context(req.iter_content(chunk_size=8192)), 
                        content_type='audio/mp4')
    except Exception as e:
        print(f"❌ Stream Proxy Error: {e}")
        return "Stream Proxy Failed", 500

# --- 4. SEARCH ---
@app.route('/search', methods=['GET'])
def search_music():
    query = request.args.get('query')
    if not query: return jsonify({"error": "Missing query"}), 400
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

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Audify Backend Live", "status": "active"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
