from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.script_generator import generate_script_proposals, store_script_proposals, get_script_proposals, select_script_proposal, update_script_proposal
from app.video_processor import process_video, get_processed_videos, get_video_subtitles, update_video_subtitles
from shooting_instructions_generator import generate_shooting_instructions, store_shooting_instructions

app = FastAPI(title="Instagram AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

DB_PATH = "data.db"

UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path("app/static/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        industry TEXT,
        target_audience TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS selections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        target_attributes TEXT,
        operational_purpose TEXT,
        platforms TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS script_proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        key_points TEXT,
        char_count INTEGER,
        is_selected BOOLEAN DEFAULT 0,
        is_template BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shooting_instructions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        script_proposal_id INTEGER,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id),
        FOREIGN KEY (script_proposal_id) REFERENCES script_proposals (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS processed_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        original_path TEXT,
        processed_path TEXT,
        jet_cut_applied BOOLEAN,
        subtitles_added BOOLEAN,
        original_duration REAL,
        processed_duration REAL,
        cut_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_subtitles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id INTEGER,
        subtitles TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (video_id) REFERENCES processed_videos (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[dict] = None

class SelectionCreate(BaseModel):
    client_id: int
    target_attributes: Optional[List[str]] = None
    operational_purpose: Optional[str] = None
    platforms: Optional[List[str]] = None

class ScriptProposalCreate(BaseModel):
    client_id: int
    num_proposals: int = 3
    additional_instructions: Optional[str] = None

class ScriptProposalUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    key_points: Optional[List[str]] = None
    is_template: Optional[bool] = None

class ScriptProposalSelect(BaseModel):
    proposal_id: int
    client_id: int

class ShootingInstructionsCreate(BaseModel):
    client_id: int
    proposal_id: int

class VideoProcessRequest(BaseModel):
    video_id: int
    jet_cut: bool = True
    add_subtitles: bool = True
    silence_threshold: float = 0.01
    min_silence_duration: float = 0.5
    subtitle_style: str = "default"
    save_as_template: bool = False

class SubtitleUpdate(BaseModel):
    subtitles: List[dict]

@app.get("/")
async def root():
    return {"message": "Instagram AI Agent API"}

@app.post("/api/clients")
async def create_client(client: ClientCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    target_audience_json = json.dumps(client.target_audience) if client.target_audience else None
    
    cursor.execute(
        "INSERT INTO clients (name, email, industry, target_audience) VALUES (?, ?, ?, ?)",
        (client.name, client.email, client.industry, target_audience_json)
    )
    
    client_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return {"success": True, "client_id": client_id}

@app.get("/api/clients")
async def get_clients():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM clients ORDER BY name")
    clients = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {"success": True, "clients": clients}

@app.post("/api/selections")
async def create_selection(selection: SelectionCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    target_attributes_json = json.dumps(selection.target_attributes) if selection.target_attributes else None
    platforms_json = json.dumps(selection.platforms) if selection.platforms else None
    
    cursor.execute(
        "INSERT INTO selections (client_id, target_attributes, operational_purpose, platforms) VALUES (?, ?, ?, ?)",
        (selection.client_id, target_attributes_json, selection.operational_purpose, platforms_json)
    )
    
    selection_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return {"success": True, "selection_id": selection_id}

@app.post("/api/generate-script-proposals")
async def api_generate_script_proposals(request: ScriptProposalCreate):
    result = generate_script_proposals(
        request.client_id,
        request.num_proposals,
        request.additional_instructions or ""
    )
    
    if not result["success"]:
        return {"success": False, "error": result["error"]}
    
    proposal_ids = store_script_proposals(request.client_id, result["proposals"])
    
    return {"success": True, "proposals": result["proposals"], "proposal_ids": proposal_ids}

@app.get("/api/script-proposals")
async def api_get_script_proposals(client_id: Optional[int] = None):
    proposals = get_script_proposals(client_id)
    
    return {"success": True, "proposals": proposals}

@app.get("/api/script-proposals/{proposal_id}")
async def api_get_script_proposal(proposal_id: int):
    proposal = get_script_proposals(proposal_id=proposal_id)
    
    if not proposal:
        return {"success": False, "error": "Script proposal not found"}
    
    return {"success": True, "proposal": proposal}

@app.put("/api/script-proposals/{proposal_id}")
async def api_update_script_proposal(proposal_id: int, update: ScriptProposalUpdate):
    success = update_script_proposal(
        proposal_id,
        update.title,
        update.content,
        update.key_points,
        update.is_template
    )
    
    if not success:
        return {"success": False, "error": "Failed to update script proposal"}
    
    return {"success": True}

@app.post("/api/select-script")
async def api_select_script(request: ScriptProposalSelect):
    success = select_script_proposal(request.proposal_id, request.client_id)
    
    if not success:
        return {"success": False, "error": "Failed to select script proposal"}
    
    return {"success": True}

@app.post("/api/generate-shooting-instructions")
async def api_generate_shooting_instructions(request: ShootingInstructionsCreate):
    try:
        instructions = generate_shooting_instructions(request.client_id, request.proposal_id)
        
        instruction_id = store_shooting_instructions(
            request.client_id,
            request.proposal_id,
            instructions
        )
        
        return {"success": True, "instructions": instructions, "instruction_id": instruction_id}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/shooting-instructions")
async def api_get_shooting_instructions(client_id: Optional[int] = None, proposal_id: Optional[int] = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM shooting_instructions"
    params = []
    
    if client_id and proposal_id:
        query += " WHERE client_id = ? AND script_proposal_id = ?"
        params.extend([client_id, proposal_id])
    elif client_id:
        query += " WHERE client_id = ?"
        params.append(client_id)
    elif proposal_id:
        query += " WHERE script_proposal_id = ?"
        params.append(proposal_id)
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    instructions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {"success": True, "instructions": instructions}

@app.post("/api/upload-video")
async def api_upload_video(
    file: UploadFile = File(...),
    client_id: int = Form(...),
    aspect_ratio: str = Form("9:16"),
    margin_seconds: float = Form(0.5)
):
    try:
        upload_dir = UPLOAD_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"upload_{timestamp}{file_extension}"
        file_path = upload_dir / new_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            aspect_ratio TEXT,
            margin_seconds REAL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute(
            "INSERT INTO uploads (client_id, filename, original_filename, aspect_ratio, margin_seconds) VALUES (?, ?, ?, ?, ?)",
            (client_id, new_filename, file.filename, aspect_ratio, margin_seconds)
        )
        
        upload_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return {"success": True, "upload_id": upload_id, "filename": new_filename}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/process-video")
async def api_process_video(request: VideoProcessRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM processed_videos WHERE id = ?", (request.video_id,))
        video = cursor.fetchone()
        
        if not video:
            cursor.execute("SELECT * FROM uploads WHERE id = ?", (request.video_id,))
            upload = cursor.fetchone()
            
            if not upload:
                conn.close()
                return {"success": False, "error": "Video not found"}
            
            video_path = str(UPLOAD_DIR / upload["filename"])
            client_id = upload["client_id"]
        else:
            video_path = video["processed_path"]
            client_id = video["client_id"]
        
        conn.close()
        
        result = process_video(
            video_path,
            str(OUTPUT_DIR),
            client_id,
            request.jet_cut,
            request.add_subtitles,
            request.silence_threshold,
            request.min_silence_duration,
            request.subtitle_style,
            request.save_as_template
        )
        
        if not result["success"]:
            return {"success": False, "error": result["error"]}
        
        return {"success": True, "result": result}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/processed-videos")
async def api_get_processed_videos(client_id: Optional[int] = None):
    try:
        videos = get_processed_videos(client_id)
        
        return {"success": True, "videos": videos}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/processed-videos/{video_id}")
async def api_get_processed_video(video_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM processed_videos WHERE id = ?", (video_id,))
        video = cursor.fetchone()
        
        if not video:
            conn.close()
            return {"success": False, "error": "Video not found"}
        
        video_dict = dict(video)
        
        subtitles = get_video_subtitles(video_id)
        
        cursor.execute("SELECT silence_periods FROM processed_videos WHERE id = ?", (video_id,))
        silence_result = cursor.fetchone()
        
        silence_periods = []
        if silence_result and silence_result["silence_periods"]:
            try:
                silence_periods = json.loads(silence_result["silence_periods"])
            except:
                pass
        
        conn.close()
        
        return {
            "success": True,
            "video": video_dict,
            "subtitles": subtitles,
            "silence_periods": silence_periods
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/api/video-subtitles/{video_id}")
async def api_update_video_subtitles(video_id: int, update: SubtitleUpdate):
    try:
        success = update_video_subtitles(video_id, update.subtitles)
        
        if not success:
            return {"success": False, "error": "Failed to update subtitles"}
        
        return {"success": True}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/templates")
async def api_get_templates(type: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if type:
        cursor.execute("SELECT * FROM templates WHERE type = ? ORDER BY created_at DESC", (type,))
    else:
        cursor.execute("SELECT * FROM templates ORDER BY type, created_at DESC")
    
    templates = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {"success": True, "templates": templates}

@app.post("/api/templates")
async def api_create_template(
    type: str = Form(...),
    name: str = Form(...),
    content: str = Form(...)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO templates (type, name, content) VALUES (?, ?, ?)",
        (type, name, content)
    )
    
    template_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return {"success": True, "template_id": template_id}

@app.get("/script-editor")
async def script_editor_page(request: Request):
    return templates.TemplateResponse("script_editor.html", {"request": request})

@app.get("/video-editor")
async def video_editor_page(request: Request):
    return templates.TemplateResponse("video_editor.html", {"request": request})

init_db()
