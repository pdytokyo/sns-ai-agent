import os
import asyncio
import tempfile
from typing import Optional
import yt_dlp

async def download_video(url: str) -> str:
    """
    Download a video from a URL using yt-dlp.
    
    Args:
        url: URL of the video to download
        
    Returns:
        Path to the downloaded video file
    
    Raises:
        Exception: If download fails
    """
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "video.mp4")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
        'noplaylist': True,
        'cookiefile': os.getenv('IG_COOKIE_FILE')  # Use Instagram cookie file if available
    }
    
    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _download)
    
    if not os.path.exists(output_path):
        raise Exception(f"Failed to download video from {url}")
    
    return output_path
