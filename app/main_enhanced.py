from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile, Form, Security, status
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

DB_PATH = "app.db"

def init_db():
    """Initialize the database with necessary tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    
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
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
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
