from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import subprocess
import asyncio
from pathlib import Path
import aiofiles

from downloader import start_download_task, stop_download, get_current_status, initialize_status
from config import DOWNLOADS_DIR, TEMP_DIR, BASE_DIR

app = FastAPI(title="TikTok, Instagram & Facebook Downloader")

# Mount downloads folder (base) - we'll handle sub-paths in the UI
app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

def validate_url(url: str):
    allowed = ["tiktok.com", "instagram.com", "facebook.com", "fb.watch"]
    if not any(domain in url for domain in allowed):
        raise HTTPException(status_code=400, detail="URL inválida. Use TikTok, Instagram ou Facebook.")

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = BASE_DIR / "index.html"
    async with aiofiles.open(index_path, mode='r', encoding='utf-8') as f:
        return await f.read()

@app.get("/script.js")
async def get_script():
    script_path = BASE_DIR / "script.js"
    async with aiofiles.open(script_path, mode='r', encoding='utf-8') as f:
        content = await f.read()
        return HTMLResponse(content=content, media_type="application/javascript")

@app.get("/style.css")
async def get_style():
    style_path = BASE_DIR / "style.css"
    async with aiofiles.open(style_path, mode='r', encoding='utf-8') as f:
        content = await f.read()
        return HTMLResponse(content=content, media_type="text/css")

@app.post("/download/video")
async def download_video(req: URLRequest, background_tasks: BackgroundTasks, x_session_id: str = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Session ID missing")
    validate_url(req.url)
    success = start_download_task(x_session_id, [req.url], background_tasks)
    if not success:
        raise HTTPException(status_code=400, detail="Já existe um download em andamento para esta sessão.")
    return {"message": "Download de vídeo iniciado!"}

@app.post("/download/profile")
async def download_profile(req: URLRequest, background_tasks: BackgroundTasks, x_session_id: str = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Session ID missing")
    validate_url(req.url)
    success = start_download_task(x_session_id, [req.url], background_tasks)
    if not success:
        raise HTTPException(status_code=400, detail="Já existe um download em andamento.")
    return {"message": "Download do perfil iniciado (isso pode levar tempo)!"}

@app.post("/download/list")
async def download_list(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks(), x_session_id: str = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Session ID missing")
    
    content = await file.read()
    urls = [line.strip() for line in content.decode().splitlines() if line.strip()]
    
    if not urls:
        raise HTTPException(status_code=400, detail="O arquivo está vazio.")
    
    success = start_download_task(x_session_id, urls, background_tasks)
    if not success:
        raise HTTPException(status_code=400, detail="Já existe um download em andamento.")
    return {"message": f"Download de lista iniciado ({len(urls)} vídeos)!"}

@app.get("/status")
async def get_status(x_session_id: str = Header(None)):
    if not x_session_id:
        return {"is_active": False, "logs": [], "progress": 0}
    return get_current_status(x_session_id)

@app.post("/stop")
async def stop(x_session_id: str = Header(None)):
    if x_session_id:
        stop_download(x_session_id)
    return {"message": "Sinal de parada enviado."}

@app.post("/initialize")
async def initialize(x_session_id: str = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Session ID missing")
    initialize_status(x_session_id)
    return {"message": "Sessão inicializada."}

@app.get("/files")
async def list_files(x_session_id: str = Header(None)):
    if not x_session_id:
        return []
    
    videos = []
    session_dir = DOWNLOADS_DIR / x_session_id
    if not session_dir.exists():
        return []

    try:
        for p in session_dir.rglob("*.mp4"):
            # URL will be /downloads/{session_id}/{filename}
            url_path = f"/downloads/{x_session_id}/{quote(p.name)}" 
            videos.append({
                "name": p.name,
                "url": url_path,
                "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                "folder": x_session_id
            })
    except Exception as e:
        print(f"Error listing files: {e}")
        
    # Return latest first
    return sorted(videos, key=lambda x: x['name'], reverse=True)
