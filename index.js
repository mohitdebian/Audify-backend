const express = require('express');
const YTMusic = require('ytmusic-api');
const ytdl = require('@distube/ytdl-core');
const fs = require('fs');
const cors = require('cors');

const app = express();
const ytmusic = new YTMusic();

// Allow your frontend to access the server
app.use(cors());
app.use(express.json());

// --- COOKIE SETUP ---
let agent;
try {
    const cookieData = JSON.parse(fs.readFileSync('cookies.json', 'utf8'));
    agent = ytdl.createAgent(cookieData);
    console.log("✅ YouTube Agent created with cookies.");
} catch (err) {
    console.warn("⚠️ No cookies found. Streams might fail on cloud servers.");
}

// Initialize YTMusic
const initYT = async () => {
    await ytmusic.initialize();
    console.log("✅ YT Music Initialized");
};
initYT();

// 1. Search Endpoint
app.get('/search', async (req, res) => {
    try {
        const query = req.query.q;
        const results = await ytmusic.searchSongs(query);
        res.json(results);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

/**
 * 2. PROXY STREAM ENDPOINT
 * This is the fix for CORS and 403.
 * Usage: <audio src="https://your-app.com/stream/VIDEO_ID" />
 */
app.get('/stream/:id', async (req, res) => {
    try {
        const videoId = req.params.id;
        const url = `https://www.youtube.com/watch?v=${videoId}`;

        // Set Headers so the browser knows this is a continuous audio stream
        res.setHeader('Content-Type', 'audio/mpeg');
        res.setHeader('Transfer-Encoding', 'chunked');

        // Pipe the ytdl stream directly into the 'res' (response) object
        ytdl(url, {
            agent,
            filter: 'audioonly',
            quality: 'highestaudio',
            // Helps with buffering and seeking
            highWaterMark: 1 << 25 
        })
        .on('error', (err) => {
            console.error("YTDL Stream Error:", err.message);
            if (!res.headersSent) {
                res.status(500).send("Streaming failed");
            }
        })
        .pipe(res);

    } catch (err) {
        console.error("Route Error:", err.message);
        res.status(500).send("Internal Server Error");
    }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`🚀 Proxy Server running on port ${PORT}`));
