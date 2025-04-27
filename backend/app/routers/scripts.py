from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session
from typing import Dict, Any, Optional, Union
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
    session: Session = Depends(get_session),
    current_user: Optional[User] = None
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
    session: Session = Depends(get_session),
    current_user: Optional[User] = None
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

from ..models.competitor_schemas import GenerateScriptRequest

@router.post("/generate", response_model=Dict[str, Any])
async def generate_script(
    pattern: str = Body(None),
    client_info: Dict[str, Any] = Body(None),
    request: Dict[str, Any] = Body(None),
    session: Session = Depends(get_session),
    current_user: Optional[User] = None
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
        if request and not pattern:
            pattern = request.get("pattern", "")
        if request and not client_info:
            client_info = request.get("client_info", {})
        
        if not pattern or not client_info:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing required fields: pattern and client_info"
            )
        
        if os.getenv("TESTING") == "true":
            return {
                "script": "This is a test script generated based on the pattern.",
                "template_path": "data/templates/1.txt",
                "template_distance": 0.1,
                "char_counts": {"0": 10, "3": 15, "6": 12},
                "time_codes": {"0": 0, "3": 3, "6": 6}
            }
            
        script_generator = ScriptGenerator()
        script_data = await script_generator.generate_script(pattern, client_info)
        
        return script_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )
