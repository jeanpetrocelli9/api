import asyncio
import yt_dlp
import logging
import os
from pathlib import Path
from fastapi import BackgroundTasks
from config import get_ytdlp_options, DOWNLOADS_DIR, FFMPEG_LOCATION

logger = logging.getLogger("downloader")
logger.setLevel(logging.INFO)

# Global status tracking by session_id
user_sessions = {}

def get_session_status(session_id: str):
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "is_active": False,
            "current_url": "",
            "current_file": "",
            "progress": 0,
            "downloaded_count": 0,
            "logs": [],
            "should_stop": False
        }
    return user_sessions[session_id]

def log_event(session_id: str, message: str):
    status = get_session_status(session_id)
    status["logs"].append(message)
    if len(status["logs"]) > 100:
        status["logs"].pop(0)
    print(f"[{session_id}] {message}")

def progress_hook_wrapper(session_id: str):
    def progress_hook(d):
        try:
            status = get_session_status(session_id)
            if status.get("should_stop"):
                raise Exception("Manual stop requested")

            if d['status'] == 'downloading':
                # Handle percent calculation manually if needed, or use _percent_str
                p_str = d.get('_percent_str', '0%').replace('%', '').strip()
                try:
                    status["progress"] = float(p_str)
                except:
                    status["progress"] = 0
                
                status["current_url"] = d.get('info_dict', {}).get('webpage_url', "")
                status["current_file"] = os.path.basename(d.get('filename', ''))

            elif d['status'] == 'finished':
                status["downloaded_count"] += 1
                log_event(session_id, f"Concluído: {os.path.basename(d.get('filename', 'Arquivo'))}")
                status["progress"] = 100.0
        except Exception as e:
            if "Manual stop requested" in str(e):
                raise yt_dlp.utils.DownloadCancelled()
    return progress_hook

def execute_download(session_id: str, urls: list):
    status = get_session_status(session_id)
    status["is_active"] = True
    status["should_stop"] = False
    
    # Create session-specific directory
    session_dir = DOWNLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': str(session_dir / '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook_wrapper(session_id)],
        'merge_output_format': 'mp4',
        'ffmpeg_location': FFMPEG_LOCATION,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in urls:
                if status["should_stop"]:
                    log_event(session_id, "Download interrompido pelo usuário.")
                    break
                
                log_event(session_id, f"Iniciando download: {url}")
                try:
                    ydl.download([url])
                except yt_dlp.utils.DownloadCancelled:
                    log_event(session_id, "Cancelado com sucesso.")
                    break
                except Exception as e:
                    log_event(session_id, f"Erro no vídeo {url}: {str(e)}")
                    
        log_event(session_id, "Processo de fila concluído.")
    except Exception as e:
        log_event(session_id, f"Erro fatal no downloader: {str(e)}")
    finally:
        status["is_active"] = False

def start_download_task(session_id: str, urls: list, background_tasks: BackgroundTasks):
    status = get_session_status(session_id)
    if status["is_active"]:
        return False
    
    # Reset status for new run
    status["downloaded_count"] = 0
    status["progress"] = 0
    status["logs"].clear()
    status["should_stop"] = False
    
    background_tasks.add_task(execute_download, session_id, urls)
    return True

def stop_download(session_id: str):
    if session_id in user_sessions:
        user_sessions[session_id]["should_stop"] = True
        log_event(session_id, "Sinal de parada enviado...")

def get_current_status(session_id: str):
    return get_session_status(session_id)

def initialize_status(session_id: str):
    status = get_session_status(session_id)
    status["is_active"] = False
    status["current_url"] = ""
    status["progress"] = 0.0
    status["downloaded_count"] = 0
    status["logs"].clear()
    status["should_stop"] = False
    log_event(session_id, "Sessão inicializada.")
    return True
