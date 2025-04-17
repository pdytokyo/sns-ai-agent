from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List
import os
import shutil
from pathlib import Path
from ..database import get_session
from ..models import Video, VideoCreate, VideoRead, Client, JobLog, JobLogCreate
from ..auth import get_current_active_user, User

router = APIRouter(
    prefix="/video",
    tags=["video"]
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload", response_model=VideoRead)
async def upload_video(
    file: UploadFile = File(...),
    client_id: int = Form(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Upload a video for a client"""
    client = session.exec(
        select(Client).where(
            Client.id == client_id,
            Client.user_id == current_user.id
        )
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or you don't have access to this client"
        )
    
    try:
        client_dir = UPLOAD_DIR / f"client_{client_id}"
        client_dir.mkdir(exist_ok=True)
        
        file_path = client_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        video = Video(
            title=title,
            file_path=str(file_path),
            client_id=client_id,
            processed=False
        )
        
        session.add(video)
        session.commit()
        session.refresh(video)
        
        job_log = JobLog(
            job_type="video_upload",
            status="success",
            client_id=client_id,
            user_id=current_user.id
        )
        session.add(job_log)
        session.commit()
        
        return video
    
    except Exception as e:
        job_log = JobLog(
            job_type="video_upload",
            status="failed",
            error_message=str(e),
            client_id=client_id,
            user_id=current_user.id
        )
        session.add(job_log)
        session.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )

@router.get("/list/{client_id}", response_model=List[VideoRead])
async def list_videos(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """List all videos for a client"""
    client = session.exec(
        select(Client).where(
            Client.id == client_id,
            Client.user_id == current_user.id
        )
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or you don't have access to this client"
        )
    
    videos = session.exec(
        select(Video).where(Video.client_id == client_id)
    ).all()
    
    return videos
