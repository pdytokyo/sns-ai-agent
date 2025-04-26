import os
import asyncio
from typing import List, Dict, Any
import yt_dlp
from .downloader import download_video
from .transcribe import transcribe_audio
from ..models.competitor import CompetitorVideo

class VideoScraper:
    def __init__(self, min_engagement_rate: float = 5.0):
        self.min_engagement_rate = min_engagement_rate
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'cookiefile': os.getenv('IG_COOKIE_FILE')
        }
    
    async def scrape_videos(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape video metadata and filter by engagement rate"""
        results = []
        for url in urls:
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    views = info.get('view_count', 0)
                    likes = info.get('like_count', 0)
                    comments = info.get('comment_count', 0)
                    shares = info.get('repost_count', 0)
                    
                    engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
                    
                    if engagement_rate >= self.min_engagement_rate:
                        results.append({
                            'platform': 'tiktok' if 'tiktok.com' in url else 'instagram',
                            'video_url': url,
                            'engagement_rate': engagement_rate,
                            'view_count': views,
                            'like_count': likes,
                            'comment_count': comments,
                            'share_count': shares
                        })
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                continue
        
        return results
    
    async def process_video(self, video_data: Dict[str, Any]) -> CompetitorVideo:
        """Download video, transcribe, and split into 3-second blocks"""
        video_path = await download_video(video_data['video_url'])
        transcript = await transcribe_audio(video_path)
        
        blocks = []
        time_codes = {}
        char_counts = {}
        
        video_data['transcript'] = transcript
        video_data['time_codes'] = time_codes
        video_data['char_counts'] = char_counts
        
        return CompetitorVideo(**video_data)
