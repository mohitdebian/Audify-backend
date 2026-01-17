const express = require('express');
const YTMusic = require('ytmusic-api');
const ytdl = require('@distube/ytdl-core'); // Changed to distube version
const cors = require('cors');

const app = express();
const ytmusic = new YTMusic();

app.use(cors());
app.use(express.json());

const initYT = async () => {
    try {
        await ytmusic.initialize();
        console.log("YT Music Initialized");
    } catch (err) {
        console.error("Failed to initialize YT Music:", err);
    }
};
initYT();

app.get('/', (req, res) => {
    res.send('Audyn Music Engine is Live.');
});

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

app.get('/stream/:id', async (req, res) => {
    try {
        const videoId = req.params.id;
        if (!videoId) return res.status(400).json({ error: "Video ID required" });

        const url = `https://www.youtube.com/watch?v=${videoId}`;
        
        // Added Basic Options to bypass some YouTube restrictions
        const info = await ytdl.getInfo(url, {
            requestOptions: {
                headers: {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                }
            }
        });

        const format = ytdl.chooseFormat(info.formats, { 
            quality: 'highestaudio', 
            filter: 'audioonly' 
        });

        if (!format) throw new Error("No audio format found");

        res.json({
            url: format.url,
            title: info.videoDetails.title,
            duration: info.videoDetails.lengthSeconds
        });
    } catch (err) {
        console.error("CRITICAL STREAM ERROR:", err.message); // This will show in Render Logs
        res.status(500).json({ error: err.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
