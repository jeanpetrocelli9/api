import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"
ARCHIVE_FILE = BASE_DIR / "logs.txt"

# Ensure directories exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# yt-dlp configuration strategy for TikTok mass downloads
def get_ytdlp_options(is_list=False):
    # Base options suitable for fast mass extraction and high quality mp4
    options = {
        'ffmpeg_location': str(BASE_DIR / 'bin'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'ignoreerrors': True, # Keep going on errors (crucial for mass downloads)
        'no_warnings': True,
        'retries': 5,
        'extractor_retries': 3,
        'concurrent_fragment_downloads': 5, # speed up fragment DLs
        'writethumbnail': True,
        'writeinfojson': True, # metadata
        'download_archive': str(ARCHIVE_FILE), # Prevent duplicates automatically
        # Removemos a criação de subpastas por uploader pois links do Instagram podem ter caracteres inválidos (?)
        # que quebram o os.makedirs no Windows (Errno 22). Agora, os nomes dos criadores vão no prefixo do aquivo.
        'outtmpl': str(DOWNLOADS_DIR) + '/%(uploader|Unknown)s_%(upload_date>%Y%m%d|Unknown)s_%(title|Unknown).50s.%(ext)s',
        'restrictfilenames': True,  # Fix Errno 22 Invalid argument on Windows 
        # 'ratelimit': 5 * 1024 * 1024, # 5MB/s limit if needed, un-comment or set via API later
        'quiet': False
    }
    
    # We could restrict resolution if we want faster downloads, but requirement is "best quality"
    
    return options
