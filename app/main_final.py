from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
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

@app.get("/")
async def root():
    return FileResponse("static/index_enhanced.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/clients")
async def create_client(client: ClientCreate):
    """Create a new client and store their information."""
    client_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO clients (id, name, email) VALUES (?, ?, ?)",
        (client_id, client.name, client.email)
    )
    
    conn.commit()
    conn.close()
    
    if client.youtube_urls and len(client.youtube_urls) > 0:
        for url in client.youtube_urls:
            video_id = extract_video_id(url)
            if video_id:
                transcript_text = get_video_transcript(video_id)
                
                transcript_id = str(uuid.uuid4())
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO client_video_transcripts (id, client_id, video_url, transcript_text) VALUES (?, ?, ?, ?)",
                    (transcript_id, client_id, url, transcript_text)
                )
                
                conn.commit()
                conn.close()
                
                analyze_client_transcripts(client_id, transcript_text)
    
    return {"client_id": client_id}

@app.post("/api/selections")
async def create_selection(selection: SelectionCreate):
    """Store client's selections for target attributes, operational purposes, and platforms."""
    selection_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO selections (id, client_id, target_attributes, operational_purposes, platforms) VALUES (?, ?, ?, ?, ?)",
        (
            selection_id,
            selection.client_id,
            json.dumps(selection.target_attributes),
            json.dumps(selection.operational_purposes),
            json.dumps(selection.platforms)
        )
    )
    
    conn.commit()
    conn.close()
    
    return {"selection_id": selection_id}

@app.post("/api/uploads/{client_id}")
async def upload_file(client_id: str, file_type: str = Form(...), file: UploadFile = File(...)):
    """Upload and store a file (video, text, PDF)."""
    upload_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    file_path = f"app/uploads/{upload_id}{file_extension}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO uploads (id, client_id, file_type, file_path) VALUES (?, ?, ?, ?)",
        (upload_id, client_id, file_type, file_path)
    )
    
    conn.commit()
    conn.close()
    
    return {"upload_id": upload_id, "file_path": file_path}

@app.get("/api/generate-profiles/{client_id}")
async def generate_profiles(client_id: str):
    """Generate account name and profile text using AI."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    
    selection_row = cursor.fetchone()
    if not selection_row:
        conn.close()
        return {"error": "No selections found for this client"}
    
    target_attributes = json.loads(selection_row[0])
    operational_purposes = json.loads(selection_row[1])
    platforms = json.loads(selection_row[2])
    
    cursor.execute(
        "SELECT file_type, file_path FROM uploads WHERE client_id = ?",
        (client_id,)
    )
    
    uploads = cursor.fetchall()
    upload_info = [{"type": row[0], "path": row[1]} for row in uploads]
    
    cursor.execute(
        "SELECT keywords, engaging_phrases FROM transcript_analysis WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    
    transcript_row = cursor.fetchone()
    transcript_info = {}
    if transcript_row:
        transcript_info = {
            "keywords": json.loads(transcript_row[0]),
            "engaging_phrases": json.loads(transcript_row[1])
        }
    
    conn.close()
    
    success_cases = []
    for platform in platforms:
        cases = research_detailed_success_case(platform, target_attributes)
        success_cases.extend(cases)
    
    prompt = f"""
    Create 3 different SNS account names and profile texts based on the following information:
    
    Target Attributes: {', '.join(target_attributes)}
    Operational Purposes: {', '.join(operational_purposes)}
    Platforms: {', '.join(platforms)}
    
    Success Cases:
    {json.dumps(success_cases, indent=2, ensure_ascii=False)}
    
    Transcript Analysis:
    {json.dumps(transcript_info, indent=2, ensure_ascii=False) if transcript_info else "No transcript analysis available"}
    
    Generate 3 different options with the following format for each:
    1. Account Name: [creative and catchy name]
    2. Profile Text: [compelling profile text, maximum 150 characters]
    
    Make sure each option is unique and tailored to the target attributes and platforms.
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in social media marketing and content creation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        
        profiles = []
        
        options = ai_response.split("Option")
        for option in options[1:]:  # Skip the first split which is empty
            lines = option.strip().split("\n")
            account_name = ""
            profile_text = ""
            
            for line in lines:
                if "Account Name:" in line:
                    account_name = line.split("Account Name:")[1].strip()
                elif "Profile Text:" in line:
                    profile_text = line.split("Profile Text:")[1].strip()
            
            if account_name and profile_text:
                profile_id = str(uuid.uuid4())
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO profiles (id, client_id, account_name, profile_text) VALUES (?, ?, ?, ?)",
                    (profile_id, client_id, account_name, profile_text)
                )
                
                conn.commit()
                conn.close()
                
                profiles.append({
                    "id": profile_id,
                    "account_name": account_name,
                    "profile_text": profile_text
                })
        
        return {"profiles": profiles}
    
    except Exception as e:
        return {"error": str(e)}

@app.put("/api/profiles/{profile_id}")
async def update_profile(profile_id: str, profile_update: ProfileUpdate):
    """Update an AI-generated profile with client's adjustments."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE profiles SET account_name = ?, profile_text = ? WHERE id = ?",
        (profile_update.account_name, profile_update.profile_text, profile_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Profile updated successfully"}

@app.put("/api/profiles/{profile_id}/select")
async def select_profile(profile_id: str):
    """Mark a profile as selected by the client."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT client_id FROM profiles WHERE id = ?", (profile_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return {"error": "Profile not found"}
    
    client_id = result[0]
    
    cursor.execute("UPDATE profiles SET selected = 0 WHERE client_id = ?", (client_id,))
    
    cursor.execute("UPDATE profiles SET selected = 1 WHERE id = ?", (profile_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Profile selected successfully"}

@app.get("/api/generate-scripts/{client_id}")
async def generate_scripts(client_id: str):
    """Generate scripts using AI based on client information and selected profile."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    
    selection_row = cursor.fetchone()
    if not selection_row:
        conn.close()
        return {"error": "No selections found for this client"}
    
    target_attributes = json.loads(selection_row[0])
    operational_purposes = json.loads(selection_row[1])
    platforms = json.loads(selection_row[2])
    
    cursor.execute(
        "SELECT account_name, profile_text FROM profiles WHERE client_id = ? AND selected = 1",
        (client_id,)
    )
    
    profile_row = cursor.fetchone()
    if not profile_row:
        cursor.execute(
            "SELECT account_name, profile_text FROM profiles WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
            (client_id,)
        )
        profile_row = cursor.fetchone()
    
    if not profile_row:
        conn.close()
        return {"error": "No profile found for this client"}
    
    account_name = profile_row[0]
    profile_text = profile_row[1]
    
    cursor.execute(
        "SELECT keywords, engaging_phrases FROM transcript_analysis WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    
    transcript_row = cursor.fetchone()
    transcript_info = {}
    if transcript_row:
        transcript_info = {
            "keywords": json.loads(transcript_row[0]),
            "engaging_phrases": json.loads(transcript_row[1])
        }
    
    conn.close()
    
    success_cases = []
    for platform in platforms:
        cases = research_detailed_success_case(platform, target_attributes)
        success_cases.extend(cases)
    
    trend_topics = collect_trend_topics(platforms)
    
    prompt = f"""
    Create 3 different script options for social media content based on the following information:
    
    Account Name: {account_name}
    Profile: {profile_text}
    Target Attributes: {', '.join(target_attributes)}
    Operational Purposes: {', '.join(operational_purposes)}
    Platforms: {', '.join(platforms)}
    
    Success Cases (use these as inspiration):
    {json.dumps(success_cases, indent=2, ensure_ascii=False)}
    
    Trend Topics (incorporate these into the scripts):
    {json.dumps(trend_topics, indent=2, ensure_ascii=False)}
    
    Transcript Analysis (use these keywords and phrases):
    {json.dumps(transcript_info, indent=2, ensure_ascii=False) if transcript_info else "No transcript analysis available"}
    
    For each script:
    1. Start with a strong hook using buzz points from success cases
    2. Include trend topics in the middle or end of the script
    3. Adapt the style to the platforms: {', '.join(platforms)}
    4. Keep each script between 200-300 words
    5. Include engaging phrases from transcript analysis if available
    
    Generate 3 different script options, each with a unique approach.
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in social media content creation and scriptwriting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        ai_response = response.choices[0].message.content
        
        scripts = []
        
        options = ai_response.split("Script")
        for option in options[1:]:  # Skip the first split which is empty
            script_text = option.strip()
            if ":" in script_text[:10]:  # Remove numbering like "1:" at the beginning
                script_text = script_text.split(":", 1)[1].strip()
            
            if script_text:
                script_id = str(uuid.uuid4())
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO scripts (id, client_id, script_text) VALUES (?, ?, ?)",
                    (script_id, client_id, script_text)
                )
                
                conn.commit()
                conn.close()
                
                scripts.append({
                    "id": script_id,
                    "script_text": script_text
                })
        
        return {"scripts": scripts}
    
    except Exception as e:
        return {"error": str(e)}

@app.put("/api/scripts/{script_id}")
async def update_script(script_id: str, script_update: ScriptUpdate):
    """Update an AI-generated script with client's adjustments."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE scripts SET script_text = ? WHERE id = ?",
        (script_update.script_text, script_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Script updated successfully"}

@app.put("/api/scripts/{script_id}/select")
async def select_script(script_id: str):
    """Mark a script as selected by the client."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT client_id FROM scripts WHERE id = ?", (script_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return {"error": "Script not found"}
    
    client_id = result[0]
    
    cursor.execute("UPDATE scripts SET selected = 0 WHERE client_id = ?", (client_id,))
    
    cursor.execute("UPDATE scripts SET selected = 1 WHERE id = ?", (script_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Script selected successfully"}

@app.get("/api/audio-library")
async def get_audio_library(genre: Optional[str] = None, mood: Optional[str] = None):
    """Get copyright-free audio tracks, optionally filtered by genre and mood."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT id, title, genre, mood, duration, file_path FROM copyright_free_audio"
    params = []
    
    if genre and mood:
        query += " WHERE genre = ? AND mood = ?"
        params = [genre, mood]
    elif genre:
        query += " WHERE genre = ?"
        params = [genre]
    elif mood:
        query += " WHERE mood = ?"
        params = [mood]
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    audio_tracks = []
    for row in rows:
        audio_tracks.append({
            "id": row[0],
            "title": row[1],
            "genre": row[2],
            "mood": row[3],
            "duration": row[4],
            "file_path": row[5]
        })
    
    return {"audio_tracks": audio_tracks}

@app.get("/api/audio/{audio_id}")
async def get_audio_file(audio_id: str):
    """Stream an audio file from the library."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT file_path FROM copyright_free_audio WHERE id = ?", (audio_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if not result:
        return {"error": "Audio track not found"}
    
    file_path = result[0]
    return FileResponse(file_path)

@app.post("/api/video-processing/{client_id}")
async def process_client_video(
    client_id: str, 
    file: UploadFile = File(...),
    aspect_ratio: str = Form(...),
    margin_seconds: float = Form(0.5)
):
    """Process a video using the jetcut algorithm and adjust aspect ratio."""
    upload_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    input_path = f"app/uploads/{upload_id}_input{file_extension}"
    output_path = f"app/uploads/{upload_id}_output{file_extension}"
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        result = process_video(input_path, output_path, aspect_ratio, margin_seconds)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        result_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO video_processing_results 
            (id, client_id, input_path, output_path, aspect_ratio, original_duration, processed_duration, reduction_percentage) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id, 
                client_id, 
                input_path, 
                output_path, 
                aspect_ratio, 
                result["original_duration"], 
                result["processed_duration"], 
                result["reduction_percentage"]
            )
        )
        
        conn.commit()
        conn.close()
        
        return {
            "result_id": result_id,
            "output_path": output_path,
            "original_duration": result["original_duration"],
            "processed_duration": result["processed_duration"],
            "reduction_percentage": result["reduction_percentage"]
        }
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/video/{result_id}")
async def get_processed_video(result_id: str):
    """Stream a processed video file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT output_path FROM video_processing_results WHERE id = ?", (result_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if not result:
        return {"error": "Processed video not found"}
    
    output_path = result[0]
    return FileResponse(output_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
