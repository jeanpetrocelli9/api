import asyncio
import yt_dlp
import logging
from config import get_ytdlp_options

logger = logging.getLogger("downloader")
logger.setLevel(logging.INFO)

# Global status tracking
status_data = {
    "is_active": False,
    "current_url": None,
    "progress": 0.0,
    "downloaded_count": 0,
    "logs": [],
    "should_stop": False
}

def log_event(message: str):
    logger.info(message)
    status_data["logs"].append(message)
    # Keep log memory reasonable
    if len(status_data["logs"]) > 200:
        status_data["logs"] = status_data["logs"][-200:]

def update_progress(d):
    """
    Hook for yt-dlp to report progress back to our status_data.
    """
    try:
        if status_data["should_stop"]:
            raise yt_dlp.utils.DownloadCancelled("Download stopped by user")

        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                if total > 0:
                    status_data["progress"] = round((downloaded / total) * 100, 2)
                
                # Optionally update current url/file based on dictionary info
                filename = d.get('filename', '')
                if filename and filename != status_data.get('current_file'):
                     status_data['current_file'] = filename

            except Exception:
                pass

        elif d['status'] == 'finished':
            status_data["downloaded_count"] += 1
            filename = d.get('filename')
            if filename:
                try:
                    # Resolve to absolute just to be sure
                    abs_filename = Path(filename).resolve()
                    abs_downloads = Path(DOWNLOADS_DIR).resolve()
                    rel_path = abs_filename.relative_to(abs_downloads).as_posix()
                    status_data["finished_files"].append(rel_path)
                    log_event(f"Finished: {rel_path}")
                except Exception as e:
                    # Fallback
                    base = os.path.basename(filename)
                    status_data["finished_files"].append(base)
                    log_event(f"Finished: {base}")
            status_data["progress"] = 100.0
    except Exception as e:
        if not isinstance(e, yt_dlp.utils.DownloadCancelled):
             log_event(f"Progress hook error: {str(e)}")

def execute_download(urls: list[str]):
    """
    Runs yt-dlp in a separate thread/sync block.
    """
    status_data["is_active"] = True
    status_data["should_stop"] = False
    
    opts = get_ytdlp_options()
    opts['progress_hooks'] = [update_progress]
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            for url in urls:
                if status_data["should_stop"]:
                    log_event("Stopping process gracefully...")
                    break
                
                log_event(f"Starting extraction for: {url}")
                status_data["current_url"] = url
                status_data["progress"] = 0.0
                try:
                    # extract_info with download=True handles the actual DL
                    ydl.extract_info(url, download=True)
                except yt_dlp.utils.DownloadCancelled:
                    log_event(f"Download of {url} was cancelled.")
                except Exception as e:
                    log_event(f"Error processing {url}: {str(e)}")
                    
    except Exception as e:
         log_event(f"Fatal error in downloader: {str(e)}")
    finally:
         status_data["is_active"] = False
         status_data["current_url"] = None
         log_event("Download queue finished.")


async def start_download_task(urls: list[str]):
    """
    Wraps execution so we can trigger it from FastAPI asynchronously
    without blocking the API loop.
    """
    if status_data["is_active"]:
         log_event("A download is already active. Ignoring new request to avoid overlap constraints.")
         return False
         
    # Reset some status
    status_data["downloaded_count"] = 0
    status_data["logs"].clear()
    
    # Run in asyncio threadpool to avoid blocking API
    asyncio.create_task(asyncio.to_thread(execute_download, urls))
    return True

def stop_download():
    status_data["should_stop"] = True
    log_event("Stop signal sent...")

def initialize_status():
    status_data["is_active"] = False
    status_data["current_url"] = None
    status_data["progress"] = 0.0
    status_data["downloaded_count"] = 0
    status_data["logs"].clear()
    status_data["should_stop"] = False
    log_event("Aplicação inicializada.")

def get_current_status():
    return status_data
