from fastapi import FastAPI, Request, File, UploadFile, Form, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List, Optional
import os
import sqlite3
import uuid
import shutil
from datetime import datetime
import openai
from dotenv import load_dotenv
from pydantic import BaseModel
import re
import json
import secrets
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_enhancement import research_detailed_success_case, store_success_case, collect_trend_topics
from script_analysis import analyze_client_transcripts, get_transcript_analysis
from video_processing import process_video

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "your_api_key_here")
openai.api_key = openai_api_key

AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "password123")
print(f"Using authentication credentials: {AUTH_USERNAME}/{AUTH_PASSWORD}")

app = FastAPI()
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, AUTH_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, AUTH_PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

DB_PATH = "app.db"

def init_db():
    """Initialize the database with necessary tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS selections (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        target_attributes TEXT NOT NULL,
        operational_purposes TEXT NOT NULL,
        platforms TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS uploads (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        account_name TEXT NOT NULL,
        profile_text TEXT NOT NULL,
        selected INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        script_text TEXT NOT NULL,
        selected INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detailed_success_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        industry TEXT NOT NULL,
        account_name TEXT,
        profile_text TEXT,
        video_url TEXT,
        buzz_point TEXT,
        top_comments TEXT,
        trend_topics TEXT,
        engagement_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS client_video_transcripts (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        video_url TEXT NOT NULL,
        transcript_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transcript_analysis (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        keywords TEXT NOT NULL,
        engaging_phrases TEXT NOT NULL,
        sentiment_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS copyright_free_audio (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        mood TEXT NOT NULL,
        duration INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_processing_results (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        input_path TEXT NOT NULL,
        output_path TEXT NOT NULL,
        aspect_ratio TEXT NOT NULL,
        original_duration REAL NOT NULL,
        processed_duration REAL NOT NULL,
        reduction_percentage REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

os.makedirs("app/uploads", exist_ok=True)

class ClientCreate(BaseModel):
    name: str
    email: str
    youtube_urls: Optional[List[str]] = None

class SelectionCreate(BaseModel):
    client_id: str
    target_attributes: List[str]
    operational_purposes: List[str]
    platforms: List[str]

class ProfileUpdate(BaseModel):
    account_name: str
    profile_text: str

class ScriptUpdate(BaseModel):
    script_text: str

def extract_video_id(url):
    """Extract YouTube video ID from URL."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    match = re.match(youtube_regex, url)
    if match:
        return match.group(6)
    
    if 'youtu.be' in url:
        return url.split('/')[-1]
    
    return None

def get_video_transcript(video_id):
    """Get transcript for a YouTube video."""
    try:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ja'])
        except:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            except Exception as e:
                print(f"Could not get transcript in ja or en for video {video_id}: {str(e)}")
                return f"This is a mock transcript for video {video_id} since the actual transcript could not be retrieved."
        
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)
        
        print(f"Successfully retrieved transcript for video {video_id}, length: {len(transcript_text)} chars")
        return transcript_text
    except Exception as e:
        print(f"Error getting transcript for video {video_id}: {str(e)}")
        return f"This is a mock transcript for video {video_id} since the actual transcript could not be retrieved."

@app.get("/", dependencies=[Depends(verify_credentials)])
async def root():
    return FileResponse("static/index_enhanced.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
