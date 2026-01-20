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

# --- 1. COOKIE SETUP ---
def setup_cookies():
    # Priority 1: Local file
    if os.path.exists('cookies.txt'):
        print("✅ Found local 'cookies.txt'.")
        return 'cookies.txt'
    
    # Priority 2: Render Env Var
    cookie_content = os.environ.get('YOUTUBE_COOKIES')
    if cookie_content:
        print("✅ Found 'YOUTUBE_COOKIES' env var. Creating temp file!")
        try:
            temp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            temp.write(cookie_content)
            temp.close()
            return temp.name
        except Exception as e:
            print(f"❌ Error creating temp cookie file: {e}")
            return None

    print("⚠️ NO COOKIES FOUND. Server may be blocked by YouTube.")
    return None

COOKIE_FILE_PATH = setup_cookies()

# --- 2. CORE LOGIC ---
def get_audio_url(video_id):
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Base Options
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': True,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        # CRITICAL: Use Cookies if available
        if COOKIE_FILE_PATH:
            ydl_opts['cookiefile'] = COOKIE_FILE_PATH
        else:
            # Fallback: Try iOS Client (Often works better than Android on Render)
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['ios']
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
            
    except Exception as e:
        print(f"❌ Extraction Error: {e}")
        return None

# --- 3. PROXY STREAM ---
@app.route('/stream')
def stream_audio():
    video_id = request.args.get('id')
    if not video_id: return "Missing ID", 400

    print(f"🎵 Streaming: {video_id}")
    google_url = get_audio_url(video_id)
    
    if not google_url:
        return "Audio not found (Extraction Failed)", 404

    try:
        req = requests.get(google_url, stream=True)
        return Response(stream_with_context(req.iter_content(chunk_size=8192)), 
                        content_type='audio/mp4')
    except Exception as e:
        print(f"❌ Stream Error: {e}")
        return "Stream Failed", 500

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
