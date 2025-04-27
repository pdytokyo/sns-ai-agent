from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional, Union
import os

from ..database import get_session
from ..models import User
from ..auth import get_current_active_user
from ..models.competitor import CompetitorVideo
from ..services.scraper import VideoScraper
from ..services.embedding import EmbeddingService

router = APIRouter(
    prefix="/competitor",
    tags=["competitor"]
)

from ..models.competitor_schemas import ScrapeRequest

@router.post("/scrape", response_model=List[Dict[str, Any]])
async def scrape_competitor_videos(
    request: List[str],
    session: Session = Depends(get_session),
    current_user: Optional[User] = None
):
    """
    Scrape competitor videos from TikTok and Instagram
    
    Args:
        urls: List of video URLs to scrape
        
    Returns:
        List of scraped video data
    """
    try:
        scraper = VideoScraper()
        
        results = await scraper.scrape_videos(request)
        
        for result in results:
            video = CompetitorVideo(**result)
            session.add(video)
        
        session.commit()
        
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape videos: {str(e)}"
        )

@router.post("/process/{video_id}", response_model=Dict[str, Any])
async def process_competitor_video(
    video_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = None
):
    """
    Process a competitor video: download, transcribe, and add to FAISS index
    
    Args:
        video_id: ID of the video to process
        
    Returns:
        Processed video data
    """
    try:
        video = session.exec(select(CompetitorVideo).where(CompetitorVideo.id == video_id)).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video with ID {video_id} not found"
            )
        
        scraper = VideoScraper()
        video_data = {
            'platform': video.platform,
            'video_url': video.video_url,
            'engagement_rate': video.engagement_rate,
            'view_count': video.view_count,
            'like_count': video.like_count,
            'comment_count': video.comment_count,
            'share_count': video.share_count
        }
        processed_video = await scraper.process_video(video_data)
        
        video.transcript = processed_video.transcript
        video.time_codes = processed_video.time_codes
        video.char_counts = processed_video.char_counts
        session.add(video)
        session.commit()
        
        embedding_service = EmbeddingService()
        template_path = embedding_service.save_template(
            video.id, 
            video.transcript, 
            video.time_codes, 
            video.char_counts
        )
        embedding_service.add_to_index(video.id, video.transcript)
        
        return {
            'id': video.id,
            'platform': video.platform,
            'video_url': video.video_url,
            'engagement_rate': video.engagement_rate,
            'transcript': video.transcript,
            'template_path': template_path
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process video: {str(e)}"
        )
