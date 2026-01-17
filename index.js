const express = require('express');
const YTMusic = require('ytmusic-api');
const ytdl = require('@distube/ytdl-core');
const fs = require('fs');
const cors = require('cors');

const app = express();
const ytmusic = new YTMusic();

app.use(cors());
app.use(express.json());

// --- SECURE COOKIE AGENT SETUP ---
let agent;
try {
    // This reads the JSON array you just provided
    const cookieData = JSON.parse(fs.readFileSync('cookies.json', 'utf8'));
    agent = ytdl.createAgent(cookieData);
    console.log("✅ YouTube Agent successfully created with cookies.");
} catch (err) {
    console.error("❌ Failed to load cookies.json:", err.message);
    console.warn("Continuing without cookies (Bot detection likely).");
}

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
        const url = `https://www.youtube.com/watch?v=${videoId}`;
        
        // Passing the 'agent' with your cookies into the getInfo call
        const info = await ytdl.getInfo(url, { agent });

        const format = ytdl.chooseFormat(info.formats, { 
            quality: 'highestaudio', 
            filter: 'audioonly' 
        });

        res.json({
            url: format.url,
            title: info.videoDetails.title,
            duration: info.videoDetails.lengthSeconds
        });
    } catch (err) {
        console.error("CRITICAL STREAM ERROR:", err.message);
        res.status(500).json({ error: err.message });
    }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
