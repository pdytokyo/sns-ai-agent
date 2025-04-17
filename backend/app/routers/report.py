from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json
from ..database import get_session
from ..models import Report, ReportCreate, ReportRead, Client, Post, Video, JobLog
from ..auth import get_current_active_user, User

router = APIRouter(
    prefix="/report",
    tags=["report"]
)

@router.get("/{client_id}", response_model=Dict[str, Any])
async def get_client_report(
    client_id: int,
    period: str = "month",  # Options: week, month, year, all
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get a report for a client"""
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
        now = datetime.utcnow()
        if period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        elif period == "year":
            start_date = now - timedelta(days=365)
        else:  # all
            start_date = datetime.min
        
        posts = session.exec(
            select(Post).where(
                Post.client_id == client_id,
                Post.created_at >= start_date
            )
        ).all()
        
        videos = session.exec(
            select(Video).where(
                Video.client_id == client_id,
                Video.created_at >= start_date
            )
        ).all()
        
        job_logs = session.exec(
            select(JobLog).where(
                JobLog.client_id == client_id,
                JobLog.created_at >= start_date
            )
        ).all()
        
        report_data = {
            "client_id": client_id,
            "client_name": client.name,
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "summary": {
                "total_posts": len(posts),
                "posted_posts": sum(1 for p in posts if p.posted),
                "scheduled_posts": sum(1 for p in posts if not p.posted and p.scheduled_for),
                "total_videos": len(videos),
                "processed_videos": sum(1 for v in videos if v.processed),
                "failed_jobs": sum(1 for j in job_logs if j.status == "failed")
            },
            "posts": [
                {
                    "id": p.id,
                    "platform": p.platform,
                    "scheduled_for": p.scheduled_for.isoformat() if p.scheduled_for else None,
                    "posted": p.posted,
                    "created_at": p.created_at.isoformat()
                }
                for p in posts
            ],
            "videos": [
                {
                    "id": v.id,
                    "title": v.title,
                    "processed": v.processed,
                    "created_at": v.created_at.isoformat()
                }
                for v in videos
            ],
            "failed_jobs": [
                {
                    "id": j.id,
                    "job_type": j.job_type,
                    "error_message": j.error_message,
                    "created_at": j.created_at.isoformat()
                }
                for j in job_logs if j.status == "failed"
            ]
        }
        
        report = Report(
            report_type=f"{period}_summary",
            data=report_data,
            period_start=start_date,
            period_end=now,
            client_id=client_id
        )
        
        session.add(report)
        session.commit()
        
        return report_data
    
    except Exception as e:
        job_log = JobLog(
            job_type="report_generation",
            status="failed",
            error_message=str(e),
            client_id=client_id,
            user_id=current_user.id
        )
        session.add(job_log)
        session.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )
