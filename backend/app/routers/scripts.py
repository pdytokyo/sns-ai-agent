from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any, Optional
import os

from ..database import get_session
from ..models import User
from ..auth import get_current_active_user
from ..services.downloader import download_video
from ..services.transcribe import transcribe_audio
from ..services.rewrite import generate_script_from_transcript, generate_original_script
from ..services.script_generator import ScriptGenerator

router = APIRouter(
    prefix="/scripts",
    tags=["scripts"]
)

@router.post("/modeling", response_model=Dict[str, Any])
async def model_script_from_video(
    video_url: str,
    current_user: Optional[User] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Generate a script and shot list based on a video URL.
    
    Args:
        video_url: URL of the video to model the script after
        
    Returns:
        Dict containing script and shot list
    """
    try:
        video_path = await download_video(video_url)
        
        transcript = await transcribe_audio(video_path)
        
        script_data = await generate_script_from_transcript(transcript, video_url)
        
        
        return script_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )

@router.post("/original", response_model=Dict[str, Any])
async def create_original_script(
    keyword: str,
    persona: str,
    current_user: Optional[User] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Generate an original script and shot list based on a keyword and persona.
    
    Args:
        keyword: Main topic or keyword for the script
        persona: Target persona/audience for the script
        
    Returns:
        Dict containing script and shot list
    """
    try:
        script_data = await generate_original_script(keyword, persona)
        
        
        return script_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )

@router.post("/generate", response_model=Dict[str, Any])
async def generate_script(
    pattern: str,
    client_info: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Generate a script based on a pattern and client info using RAG
    
    Args:
        pattern: Pattern to search for (keywords or description)
        client_info: Client information to incorporate into script
        
    Returns:
        Dict containing generated script and metadata
    """
    try:
        script_generator = ScriptGenerator()
        script_data = await script_generator.generate_script(pattern, client_info)
        
        return script_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )
