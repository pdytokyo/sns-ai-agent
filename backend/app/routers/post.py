from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from ..database import get_session
from ..models import Post, PostCreate, PostRead, Client, Video, JobLog
from ..auth import get_current_active_user, User

router = APIRouter(
    prefix="/post",
    tags=["post"]
)

@router.post("/schedule", response_model=PostRead)
async def schedule_post(
    post: PostCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Schedule a post for a client"""
    client = session.exec(
        select(Client).where(
            Client.id == post.client_id,
            Client.user_id == current_user.id
        )
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or you don't have access to this client"
        )
    
    if post.video_id:
        video = session.exec(
            select(Video).where(
                Video.id == post.video_id,
                Video.client_id == client.id
            )
        ).first()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found or doesn't belong to this client"
            )
        
        if not video.processed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video is not processed yet"
            )
    
    try:
        db_post = Post(
            caption=post.caption,
            hashtags=post.hashtags,
            scheduled_for=post.scheduled_for,
            posted=False,
            platform=post.platform,
            client_id=client.id,
            video_id=post.video_id
        )
        
        session.add(db_post)
        session.commit()
        session.refresh(db_post)
        
        job_log = JobLog(
            job_type="post_schedule",
            status="success",
            client_id=client.id,
            user_id=current_user.id
        )
        session.add(job_log)
        session.commit()
        
        return db_post
    
    except Exception as e:
        job_log = JobLog(
            job_type="post_schedule",
            status="failed",
            error_message=str(e),
            client_id=client.id,
            user_id=current_user.id
        )
        session.add(job_log)
        session.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule post: {str(e)}"
        )

@router.get("/list/{client_id}", response_model=List[PostRead])
async def list_posts(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """List all posts for a client"""
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
    
    posts = session.exec(
        select(Post).where(Post.client_id == client_id)
    ).all()
    
    return posts
