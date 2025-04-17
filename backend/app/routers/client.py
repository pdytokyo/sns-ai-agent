from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional

from ..database import get_session
from ..models import Client, ClientCreate, ClientRead, User
from ..auth import get_current_active_user, get_admin_user

router = APIRouter(
    prefix="/client",
    tags=["client"]
)

@router.post("/", response_model=ClientRead)
async def create_client(
    client: ClientCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Create a new client"""
    db_client = Client.from_orm(client)
    db_client.user_id = current_user.id
    
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    
    return db_client

@router.get("/", response_model=List[ClientRead])
async def read_clients(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get all clients for the current user or all clients for admin"""
    if current_user.is_admin:
        clients = session.exec(
            select(Client).offset(skip).limit(limit)
        ).all()
    else:
        clients = session.exec(
            select(Client)
            .where(Client.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
        ).all()
    
    return clients

@router.get("/{client_id}", response_model=ClientRead)
async def read_client(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get a specific client by ID"""
    client = session.get(Client, client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    if not current_user.is_admin and client.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this client"
        )
    
    return client

@router.put("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int,
    client_update: ClientCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Update a client"""
    db_client = session.get(Client, client_id)
    
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    if not current_user.is_admin and db_client.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this client"
        )
    
    client_data = client_update.dict(exclude_unset=True)
    for key, value in client_data.items():
        setattr(db_client, key, value)
    
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    
    return db_client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_admin_user),  # Only admin can delete clients
    session: Session = Depends(get_session)
):
    """Delete a client (admin only)"""
    db_client = session.get(Client, client_id)
    
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    session.delete(db_client)
    session.commit()
    
    return None
