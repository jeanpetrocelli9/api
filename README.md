# SocialSaver Pro
TikTok, Instagram & Facebook Video Downloader

## Features
- **Multi-User Privacy**: Isolated session storage and progress tracking.
- **Cross-Platform**: Support for TikTok, Instagram Profiles/Reels, and Facebook Videos.
- **Premium UI**: Glassmorphism design with real-time terminal logs.
- **FastAPI Backend**: Efficient concurrent handling via `yt-dlp` and `ffmpeg`.

## Setup
1. `pip install -r requirements.txt`
2. `python main.py` or `uvicorn main:app --reload`
3. Open `index.html` in your browser.

## Deployment
Compatible with Railway. Requires `ffmpeg` in the environment.
