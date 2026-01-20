import os
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)
CORS(app)
ytmusic = YTMusic()

# --- THE CLIENT ROTATOR (Tries multiple ways to unblock) ---
def get_audio_url_rotator(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Strategy 1: iOS (Best for Cloud Servers)
    # This mimics an iPhone, which often bypasses the "Sign in" check.
    ios_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios']
            }
        }
    }

    # Strategy 2: Android (Backup)
    android_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        }
    }

    # Try iOS first
    print("🔄 Attempt 1: Switching to iOS Client...")
    try:
        with yt_dlp.YoutubeDL(ios_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            url = info.get('url')
            if url:
                print("✅ Success with iOS!")
                return url
    except Exception as e:
        print(f"⚠️ iOS Failed: {e}")

    # Try Android second
    print("🔄 Attempt 2: Switching to Android Client...")
    try:
        with yt_dlp.YoutubeDL(android_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
    except Exception as e:
        print(f"❌ Android Failed: {e}")
    
    return None

# --- STREAM ROUTE ---
@app.route('/stream')
def stream_audio():
    video_id = request.args.get('id')
    if not video_id: return "Missing ID", 400

    print(f"🎵 Streaming Request: {video_id}")
    
    # Use the rotator to find a working link
    google_url = get_audio_url_rotator(video_id)
    
    if not google_url:
        print("⛔ ALL STRATEGIES FAILED. YouTube is blocking this IP.")
        return jsonify({"error": "Server Blocked"}), 403

    try:
        # Stream the data
        # We DO NOT send a custom User-Agent here to avoid mismatches
        req = requests.get(google_url, stream=True)
        return Response(stream_with_context(req.iter_content(chunk_size=8192)), 
                        content_type='audio/mp4')
    except Exception as e:
        print(f"❌ Stream Proxy Error: {e}")
        return "Stream Proxy Failed", 500

# --- SEARCH ---
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
