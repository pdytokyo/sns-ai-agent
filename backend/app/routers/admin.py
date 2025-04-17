from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import Dict, List, Optional

from ..database import get_session
from ..models import JobLog, Client, User
from ..auth import get_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get admin dashboard statistics"""
    
    total_jobs = session.exec(select(func.count()).select_from(JobLog)).one()
    
    failed_jobs = session.exec(
        select(func.count())
        .select_from(JobLog)
        .where(JobLog.status == "failed")
    ).one()
    
    client_stats = {}
    clients_with_jobs = session.exec(
        select(JobLog.client_id, func.count().label("job_count"))
        .where(JobLog.client_id != None)
        .group_by(JobLog.client_id)
    ).all()
    
    for client_id, job_count in clients_with_jobs:
        client_stats[client_id] = {
            "total": job_count,
            "failed": 0
        }
    
    clients_with_failed_jobs = session.exec(
        select(JobLog.client_id, func.count().label("failed_count"))
        .where(JobLog.client_id != None)
        .where(JobLog.status == "failed")
        .group_by(JobLog.client_id)
    ).all()
    
    for client_id, failed_count in clients_with_failed_jobs:
        if client_id in client_stats:
            client_stats[client_id]["failed"] = failed_count
        else:
            client_stats[client_id] = {
                "total": failed_count,
                "failed": failed_count
            }
    
    client_ids = list(client_stats.keys())
    if client_ids:
        clients = session.exec(
            select(Client.id, Client.name)
            .where(Client.id.in_(client_ids))
        ).all()
        
        for client_id, client_name in clients:
            if client_id in client_stats:
                client_stats[client_id]["name"] = client_name
    
    return {
        "total_jobs": total_jobs,
        "failed_jobs": failed_jobs,
        "per_client": client_stats
    }
