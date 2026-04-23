from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import subprocess
from pathlib import Path
import aiofiles

from downloader import start_download_task, stop_download, get_current_status, initialize_status
from config import DOWNLOADS_DIR, TEMP_DIR, BASE_DIR

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
    try:
        async with aiofiles.open(BASE_DIR / "index.html", mode='r', encoding='utf-8') as f:
            content = await f.read()
            return HTMLResponse(content=content)
    except Exception as e:
        return f"Erro ao carregar index.html: {e}"

@app.get("/script.js")
async def get_js():
    try:
        async with aiofiles.open(BASE_DIR / "script.js", mode='r', encoding='utf-8') as f:
            content = await f.read()
            return HTMLResponse(content=content, media_type="application/javascript")
    except Exception as e:
        return f"// Erro ao carregar script.js: {e}"

@app.get("/style.css")
async def get_css():
    try:
        async with aiofiles.open(BASE_DIR / "style.css", mode='r', encoding='utf-8') as f:
            content = await f.read()
            return HTMLResponse(content=content, media_type="text/css")
    except Exception as e:
        return f"/* Erro ao carregar style.css: {e} */"


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

