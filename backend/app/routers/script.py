from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
import os
from openai import OpenAI
from ..database import get_session
from ..models import Script, ScriptCreate, ScriptRead, Client
from ..auth import get_current_active_user, User

router = APIRouter(
    prefix="/script",
    tags=["script"]
)

api_key = os.getenv("OPENAI_API_KEY", "dummy-api-key-for-testing")
openai_client = OpenAI(api_key=api_key)

@router.post("/generate", response_model=ScriptRead)
async def generate_script(
    script_request: ScriptCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Generate a script for a client"""
    client = session.exec(
        select(Client).where(
            Client.id == script_request.client_id,
            Client.user_id == current_user.id
        )
    ).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or you don't have access to this client"
        )
    
    try:
        prompt = f"""
        Create an engaging script for {client.name} in the {client.industry or 'general'} industry.
        Target audience: {client.target_audience or 'general audience'}
        Platform: {script_request.target_platform}
        
        The script should include:
        - A strong hook
        - Key points about the product/service
        - A clear call to action
        
        Format the script for a short-form video (30-60 seconds).
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional social media content creator."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        script_content = response.choices[0].message.content
        
        script = Script(
            content=script_content,
            keywords=script_request.keywords,
            hook=script_request.hook,
            target_platform=script_request.target_platform,
            client_id=client.id
        )
        
        session.add(script)
        session.commit()
        session.refresh(script)
        
        return script
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate script: {str(e)}"
        )

@router.get("/list/{client_id}", response_model=List[ScriptRead])
async def list_scripts(
    client_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """List all scripts for a client"""
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
    
    scripts = session.exec(
        select(Script).where(Script.client_id == client_id)
    ).all()
    
    return scripts
