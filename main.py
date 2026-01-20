import os
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)
CORS(app)
ytmusic = YTMusic()

# --- 1. HYBRID SETUP (Cookies for Local, Android for Render) ---
def get_cookie_file():
    if os.path.exists('cookies.txt'):
        print("✅ Local Mode: Found 'cookies.txt'. Using it!")
        return 'cookies.txt'
    print("🚀 Cloud Mode: No cookies found. Switching to Android Client.")
    return None

COOKIE_FILE_PATH = get_cookie_file()

# --- 2. CORE LOGIC ---
def get_audio_url(video_id):
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Base settings
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': True,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        # LOGIC: If we have cookies, use them. If not, use Android Client.
        if COOKIE_FILE_PATH:
            ydl_opts['cookiefile'] = COOKIE_FILE_PATH
        else:
            # Android Client Mode (For Render)
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
            
    except Exception as e:
        print(f"❌ Extraction Error: {e}")
        return None

# --- 3. PROXY STREAM ROUTE ---
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

# --- 4. SEARCH ROUTE ---
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
