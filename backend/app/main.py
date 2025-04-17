from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from sqlmodel import Session

from .database import create_db_and_tables, get_session
from .models import User, Client, Video, Post, Report, JobLog
from .auth import get_current_active_user, get_admin_user
from .routers import auth, script, video, post, report

app = FastAPI(
    title="SNS AI SaaS API",
    description="API for SNS AI SaaS Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(script.router)
app.include_router(video.router)
app.include_router(post.router)
app.include_router(report.router)

@app.on_event("startup")
async def on_startup():
    """Create database tables on startup"""
    create_db_and_tables()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to SNS AI SaaS API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/me", response_model=dict)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin
    }

@app.get("/api/admin/stats", response_model=dict)
async def get_admin_stats(
    admin_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get admin statistics"""
    from sqlalchemy import func, select
    
    user_count = session.exec(select(func.count(User.id))).first()
    
    client_count = session.exec(select(func.count(Client.id))).first()
    
    video_count = session.exec(select(func.count(Video.id))).first()
    processed_video_count = session.exec(select(func.count(Video.id)).where(Video.processed == True)).first()
    
    post_count = session.exec(select(func.count(Post.id))).first()
    posted_count = session.exec(select(func.count(Post.id)).where(Post.posted == True)).first()
    scheduled_count = session.exec(select(func.count(Post.id)).where(Post.posted == False, Post.scheduled_for != None)).first()
    
    failed_job_count = session.exec(select(func.count(JobLog.id)).where(JobLog.status == "failed")).first()
    
    return {
        "users": user_count,
        "clients": client_count,
        "videos": {
            "total": video_count,
            "processed": processed_video_count,
            "processing_rate": processed_video_count / video_count if video_count > 0 else 0
        },
        "posts": {
            "total": post_count,
            "posted": posted_count,
            "scheduled": scheduled_count,
            "success_rate": posted_count / post_count if post_count > 0 else 0
        },
        "failed_jobs": failed_job_count
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
