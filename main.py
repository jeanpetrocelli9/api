from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import subprocess
from pathlib import Path
import aiofiles

from downloader import start_download_task, stop_download, get_current_status, initialize_status
from config import DOWNLOADS_DIR, TEMP_DIR

app = FastAPI(title="TikTok Mass Downloader API")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok Mass Downloader API</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 48px 24px;
        }
        .container {
            max-width: 760px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 40px;
        }
        header h1 {
            font-size: 2rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 8px;
        }
        header p {
            color: #888;
            font-size: 1rem;
            line-height: 1.6;
        }
        h2 {
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #555;
            margin-bottom: 16px;
        }
        .endpoints {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 40px;
        }
        .endpoint {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 16px 20px;
            display: flex;
            align-items: flex-start;
            gap: 16px;
        }
        .method {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            padding: 3px 8px;
            border-radius: 4px;
            flex-shrink: 0;
            margin-top: 2px;
        }
        .method.get  { background: #1a3a2a; color: #4ade80; }
        .method.post { background: #1a2a3a; color: #60a5fa; }
        .endpoint-info { flex: 1; }
        .path {
            font-family: "SFMono-Regular", Consolas, monospace;
            font-size: 0.95rem;
            color: #ffffff;
            margin-bottom: 4px;
        }
        .desc {
            font-size: 0.875rem;
            color: #888;
            line-height: 1.5;
        }
        .usage {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 20px;
        }
        .usage p {
            font-size: 0.875rem;
            color: #888;
            line-height: 1.7;
        }
        code {
            font-family: "SFMono-Regular", Consolas, monospace;
            background: #2a2a2a;
            color: #e0e0e0;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.85em;
        }
        footer {
            margin-top: 48px;
            font-size: 0.8rem;
            color: #444;
            text-align: center;
        }
        footer a {
            color: #555;
            text-decoration: none;
        }
        footer a:hover { color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TikTok Mass Downloader API</h1>
            <p>Download TikTok and Instagram videos, profiles, and bulk lists via a simple REST API.</p>
        </header>

        <h2>Endpoints</h2>
        <div class="endpoints">
            <div class="endpoint">
                <span class="method post">POST</span>
                <div class="endpoint-info">
                    <div class="path">/download/profile</div>
                    <div class="desc">Download all videos from a TikTok or Instagram profile. Send a JSON body with a <code>url</code> field pointing to the profile page.</div>
                </div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <div class="endpoint-info">
                    <div class="path">/download/video</div>
                    <div class="desc">Download a single TikTok or Instagram video. Send a JSON body with a <code>url</code> field pointing to the video.</div>
                </div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <div class="endpoint-info">
                    <div class="path">/download/list</div>
                    <div class="desc">Download multiple videos from a <code>.txt</code> file. Upload the file as multipart form data — one URL per line.</div>
                </div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <div class="endpoint-info">
                    <div class="path">/status</div>
                    <div class="desc">Get the current download status, including progress and any active task information.</div>
                </div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <div class="endpoint-info">
                    <div class="path">/stop</div>
                    <div class="desc">Send a stop signal to cancel the currently running download task.</div>
                </div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <div class="endpoint-info">
                    <div class="path">/initialize</div>
                    <div class="desc">Reset and initialize the application state. Call this before starting a fresh session.</div>
                </div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <div class="endpoint-info">
                    <div class="path">/files</div>
                    <div class="desc">List the most recently downloaded video files (up to 50), including name, folder, size, and a direct download URL.</div>
                </div>
            </div>
        </div>

        <h2>Usage</h2>
        <div class="usage">
            <p>
                All endpoints that accept a URL expect a JSON body: <code>{"url": "https://..."}</code>.
                The <code>/download/list</code> endpoint accepts a multipart file upload instead.
                Poll <code>/status</code> to track download progress, and call <code>/stop</code> to cancel at any time.
                Interactive docs are available at <a href="/docs"><code>/docs</code></a> (Swagger UI) and <a href="/redoc"><code>/redoc</code></a>.
            </p>
        </div>

        <footer>
            TikTok Mass Downloader &mdash; <a href="/docs">Swagger UI</a> &middot; <a href="/redoc">ReDoc</a>
        </footer>
    </div>
</body>
</html>
"""


class URLRequest(BaseModel):
    url: str

@app.post("/download/profile")
async def download_profile(req: URLRequest):
    if not req.url or ("tiktok.com" not in req.url and "instagram.com" not in req.url and "http" in req.url):
        raise HTTPException(status_code=400, detail="Invalid TikTok/Instagram Profile URL")
    
    started = await start_download_task([req.url])
    if not started:
        raise HTTPException(status_code=400, detail="Download already in progress")
    return {"message": "Profile download started"}

@app.post("/download/video")
async def download_video(req: URLRequest):
    if not req.url or ("tiktok.com" not in req.url and "instagram.com" not in req.url and "http" in req.url):
         raise HTTPException(status_code=400, detail="Invalid TikTok or Instagram URL")
         
    started = await start_download_task([req.url])
    if not started:
        raise HTTPException(status_code=400, detail="Download already in progress")
    return {"message": "Video download started"}

@app.post("/download/list")
async def download_list(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
         raise HTTPException(status_code=400, detail="Please upload a .txt file")
         
    # Save locally temporarily
    temp_path = TEMP_DIR / file.filename
    async with aiofiles.open(temp_path, 'wb') as out_file:
         content = await file.read()
         await out_file.write(content)
         
    # parse links
    with open(temp_path, "r", encoding="utf-8") as f:
         urls = [line.strip() for line in f if line.strip() and "http" in line]
         
    if not urls:
         raise HTTPException(status_code=400, detail="No valid URLs found in file")
         
    started = await start_download_task(urls)
    if not started:
        raise HTTPException(status_code=400, detail="Download already in progress")
        
    return {"message": f"List download started with {len(urls)} URLs"}

@app.get("/status")
async def get_status():
    return get_current_status()

@app.post("/stop")
async def stop():
    stop_download()
    return {"message": "Stop signal sent"}

@app.post("/initialize")
async def initialize():
    initialize_status()
    return {"message": "Application initialized"}

@app.get("/files")
async def list_files():
    """Returns a list of recent downloaded video titles"""
    videos = []
    try:
        # Search recursively for mp4s in downloads
        for p in DOWNLOADS_DIR.rglob("*.mp4"):
            url_path = "/downloads/" + p.relative_to(DOWNLOADS_DIR).as_posix()
            videos.append({
                "name": p.name,
                "folder": p.parent.name,
                "size_mb": round(p.stat().st_size / (1024*1024), 2),
                "url": url_path,
                "mtime": p.stat().st_mtime
            })
        
        # Sort by modification time, newest first, limit 50
        videos.sort(key=lambda x: x['mtime'], reverse=True)
        return videos[:50]
    except Exception as e:
        print(f"Error reading files: {e}")
        return []

