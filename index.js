const express = require('express');
const YTMusic = require('ytmusic-api');
const ytdl = require('ytdl-core');
const cors = require('cors');

const app = express();
const ytmusic = new YTMusic();

app.use(cors());
app.use(express.json());

// Initialize YTMusic once when server starts
const initYT = async () => {
    await ytmusic.initialize();
    console.log("YT Music Initialized");
};
initYT();

// 1. Search Endpoint
app.get('/search', async (req, res) => {
    try {
        const query = req.query.q;
        if (!query) return res.status(400).json({ error: "Query required" });
        
        const results = await ytmusic.searchSongs(query);
        res.json(results);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// 2. Stream Link Endpoint (This is what your Android app plays)
app.get('/stream', async (req, res) => {
    try {
        const videoId = req.query.id;
        if (!videoId) return res.status(400).json({ error: "Video ID required" });

        const url = `https://www.youtube.com/watch?v=${videoId}`;
        
        // Get info to find the best audio format
        const info = await ytdl.getInfo(url);
        const format = ytdl.chooseFormat(info.formats, { 
            quality: 'highestaudio', 
            filter: 'audioonly' 
        });

        // Return the direct URL and metadata
        res.json({
            url: format.url,
            title: info.videoDetails.title,
            duration: info.videoDetails.lengthSeconds
        });
    } catch (err) {
        res.status(500).json({ error: "Could not get stream link" });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
