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
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

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

def init_db():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS selections (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        target_attributes TEXT,
        operational_purposes TEXT,
        platforms TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS uploaded_files (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        file_type TEXT,
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
        is_selected BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        script_text TEXT NOT NULL,
        is_selected BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
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
    
    conn.commit()
    conn.close()

os.makedirs("uploads", exist_ok=True)

init_db()

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None
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

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/options")
async def get_options():
    return {
        "target_attributes": ["10代", "20代", "30代", "40代", "50代以上", "男性", "女性", "その他"],
        "operational_purposes": ["ブランディング", "集客", "販売促進", "顧客サポート", "コミュニティ構築", "教育・情報提供"],
        "platforms": ["YouTube", "Instagram", "TikTok"]
    }

def extract_video_id(youtube_url):
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)',
        r'(?:youtube\.com\/shorts\/)([\w-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def get_video_transcript(video_id):
    """Get transcript for a YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ja', 'en'])
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)
        return transcript_text
    except Exception as e:
        print(f"Error getting transcript for video {video_id}: {str(e)}")
        return None

@app.post("/clients/")
async def create_client(client: ClientCreate):
    client_id = str(uuid.uuid4())
    
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO clients (id, name, email) VALUES (?, ?, ?)",
        (client_id, client.name, client.email)
    )
    
    if client.youtube_urls:
        for url in client.youtube_urls:
            video_id = extract_video_id(url)
            if video_id:
                transcript_text = get_video_transcript(video_id)
                if transcript_text:
                    transcript_id = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO client_video_transcripts (id, client_id, video_url, transcript_text) VALUES (?, ?, ?, ?)",
                        (transcript_id, client_id, url, transcript_text)
                    )
    
    conn.commit()
    conn.close()
    
    return {"id": client_id, "name": client.name, "email": client.email}

@app.post("/selections/")
async def create_selection(
    client_id: str = Form(...),
    selection_target_attributes: List[str] = Form([], alias="selection.target_attributes"),
    selection_operational_purposes: List[str] = Form([], alias="selection.operational_purposes"),
    selection_platforms: List[str] = Form([], alias="selection.platforms")
):
    selection_id = str(uuid.uuid4())
    
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    
    import json
    target_attributes_json = json.dumps(selection_target_attributes)
    operational_purposes_json = json.dumps(selection_operational_purposes)
    platforms_json = json.dumps(selection_platforms)
    
    cursor.execute(
        "INSERT INTO selections (id, client_id, target_attributes, operational_purposes, platforms) VALUES (?, ?, ?, ?, ?)",
        (selection_id, client_id, target_attributes_json, operational_purposes_json, platforms_json)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "id": selection_id,
        "client_id": client_id,
        "target_attributes": selection_target_attributes,
        "operational_purposes": selection_operational_purposes,
        "platforms": selection_platforms
    }

@app.post("/upload/")
async def upload_file(client_id: str = Form(...), file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    file_path = f"uploads/{file_id}{file_extension}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    
    cursor.execute(
        "INSERT INTO uploaded_files (id, client_id, file_path, original_filename, file_type) VALUES (?, ?, ?, ?, ?)",
        (file_id, client_id, file_path, file.filename, file.content_type)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "id": file_id,
        "client_id": client_id,
        "file_path": file_path,
        "original_filename": file.filename,
        "file_type": file.content_type
    }

@app.post("/generate-profile/")
async def generate_profile(client_id: str = Form(...)):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    
    cursor.execute("SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1", (client_id,))
    selection = cursor.fetchone()
    
    if not selection:
        conn.close()
        raise HTTPException(status_code=404, detail="Selection not found")
    
    import json
    target_attributes = json.loads(selection[0])
    operational_purposes = json.loads(selection[1])
    platforms = json.loads(selection[2])
    
    cursor.execute("SELECT transcript_text FROM client_video_transcripts WHERE client_id = ?", (client_id,))
    transcripts = cursor.fetchall()
    transcript_texts = [t[0] for t in transcripts]
    
    try:
        if openai_api_key == "your_api_key_here":
            account_name = f"旅行好きな{target_attributes[0] if target_attributes else '20代'}のアカウント"
            profile_text = f"""こんにちは！{', '.join(target_attributes) if target_attributes else '20代'}の{', '.join(platforms) if platforms else 'YouTube'}ユーザーです。
            {', '.join(operational_purposes) if operational_purposes else 'ブランディング'}を目的としたコンテンツを発信しています。
            旅行、料理、音楽が大好きで、日常の発見や体験を共有しています。
            フォローしていただけると嬉しいです！"""
        else:
            prompt = f"""
            以下の情報に基づいて、SNSアカウントのプロフィールを生成してください。
            
            ターゲット属性: {', '.join(target_attributes)}
            運用目的: {', '.join(operational_purposes)}
            プラットフォーム: {', '.join(platforms)}
            """
            
            if transcript_texts:
                prompt += f"""
                
                以下は、クライアントのYouTube動画から抽出した字幕テキストです。このコンテンツの特徴を反映したプロフィールを作成してください：
                
                {transcript_texts[0][:1000] if len(transcript_texts[0]) > 1000 else transcript_texts[0]}
                """
                if len(transcript_texts) > 1:
                    prompt += f"""
                    
                    追加の動画字幕（要約）：
                    {'; '.join([t[:200] + '...' for t in transcript_texts[1:]])}
                    """
            
            prompt += """
            
            アカウント名とプロフィール文を日本語で生成してください。
            """
            
            client = openai.OpenAI(api_key=openai_api_key, base_url="https://api.openai.com/v1")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはSNSマーケティングの専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            
            generated_text = response.choices[0].message.content
            
            if "アカウント名:" in generated_text and "プロフィール:" in generated_text:
                account_name = generated_text.split("アカウント名:")[1].split("プロフィール:")[0].strip()
                profile_text = generated_text.split("プロフィール:")[1].strip()
            else:
                account_name = "SNSアカウント"
                profile_text = generated_text
        
        profile_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO profiles (id, client_id, account_name, profile_text) VALUES (?, ?, ?, ?)",
            (profile_id, client_id, account_name, profile_text)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "id": profile_id,
            "client_id": client_id,
            "account_name": account_name,
            "profile_text": profile_text
        }
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to generate profile: {str(e)}")

@app.post("/select-profile/{profile_id}")
async def select_profile(profile_id: str, client_id: str = Form(...)):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM profiles WHERE id = ? AND client_id = ?", (profile_id, client_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")
    
    cursor.execute("UPDATE profiles SET is_selected = 0 WHERE client_id = ?", (client_id,))
    
    cursor.execute("UPDATE profiles SET is_selected = 1 WHERE id = ?", (profile_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Profile selected successfully"}

@app.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, profile: ProfileUpdate):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM profiles WHERE id = ?", (profile_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Profile not found")
    
    cursor.execute(
        "UPDATE profiles SET account_name = ?, profile_text = ? WHERE id = ?",
        (profile.account_name, profile.profile_text, profile_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Profile updated successfully"}

@app.post("/generate-script/")
async def generate_script(client_id: str = Form(...)):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    
    cursor.execute("SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1", (client_id,))
    selection = cursor.fetchone()
    
    if not selection:
        conn.close()
        raise HTTPException(status_code=404, detail="Selection not found")
    
    import json
    target_attributes = json.loads(selection[0])
    operational_purposes = json.loads(selection[1])
    platforms = json.loads(selection[2])
    
    cursor.execute("SELECT account_name, profile_text FROM profiles WHERE client_id = ? AND is_selected = 1", (client_id,))
    profile = cursor.fetchone()
    
    account_name = profile[0] if profile else "アカウント名未設定"
    profile_text = profile[1] if profile else "プロフィール未設定"
    
    cursor.execute("SELECT transcript_text FROM client_video_transcripts WHERE client_id = ?", (client_id,))
    transcripts = cursor.fetchall()
    transcript_texts = [t[0] for t in transcripts]
    
    try:
        if openai_api_key == "your_api_key_here":
            script_text = f"""こんにちは、{account_name}です！

今日は{', '.join(target_attributes) if target_attributes else '20代'}の皆さんに向けて、旅行と料理の魅力についてお話しします。

私は{', '.join(operational_purposes) if operational_purposes else 'ブランディング'}を目的として、{', '.join(platforms) if platforms else 'YouTube'}で活動しています。

旅行先で見つけた絶品料理の作り方を紹介します。今回は京都で食べた抹茶スイーツの簡単レシピです！

皆さんも作ってみたら、ぜひコメント欄で感想を教えてくださいね。
また、次に紹介して欲しい料理があれば教えてください！

最後まで見ていただきありがとうございました。チャンネル登録もよろしくお願いします！"""
        else:
            prompt = f"""
            以下の情報に基づいて、SNS投稿用の台本を生成してください。
            
            アカウント名: {account_name}
            プロフィール: {profile_text}
            ターゲット属性: {', '.join(target_attributes)}
            運用目的: {', '.join(operational_purposes)}
            プラットフォーム: {', '.join(platforms)}
            """
            
            if transcript_texts:
                prompt += f"""
                
                以下は、クライアントのYouTube動画から抽出した字幕テキストです。このコンテンツの特徴やトーン、スタイルを参考にして、同様の魅力を持つ台本を作成してください：
                
                {transcript_texts[0][:1500] if len(transcript_texts[0]) > 1500 else transcript_texts[0]}
                """
                if len(transcript_texts) > 1:
                    prompt += f"""
                    
                    追加の動画字幕（要約）：
                    {'; '.join([t[:300] + '...' for t in transcript_texts[1:]])}
                    """
            
            prompt += """
            
            台本は以下の要素を含めてください：
            1. 挨拶
            2. 自己紹介
            3. コンテンツの主題
            4. 視聴者への質問やコールトゥアクション
            5. 締めの言葉
            
            台本は日本語で、選択されたプラットフォームに適した形式で作成してください。
            """
            
            client = openai.OpenAI(api_key=openai_api_key, base_url="https://api.openai.com/v1")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはSNSコンテンツクリエイターです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            
            script_text = response.choices[0].message.content
        
        script_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO scripts (id, client_id, script_text) VALUES (?, ?, ?)",
            (script_id, client_id, script_text)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "id": script_id,
            "client_id": client_id,
            "script_text": script_text
        }
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to generate script: {str(e)}")

@app.post("/select-script/{script_id}")
async def select_script(script_id: str, client_id: str = Form(...)):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM scripts WHERE id = ? AND client_id = ?", (script_id, client_id))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Script not found")
    
    cursor.execute("UPDATE scripts SET is_selected = 0 WHERE client_id = ?", (client_id,))
    
    cursor.execute("UPDATE scripts SET is_selected = 1 WHERE id = ?", (script_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Script selected successfully"}

@app.put("/scripts/{script_id}")
async def update_script(script_id: str, script: ScriptUpdate):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM scripts WHERE id = ?", (script_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Script not found")
    
    cursor.execute(
        "UPDATE scripts SET script_text = ? WHERE id = ?",
        (script.script_text, script_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Script updated successfully"}

@app.post("/clients/{client_id}/youtube-urls")
async def add_youtube_urls(client_id: str, youtube_urls: List[str] = Form(...)):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Client not found")
    
    added_urls = []
    for url in youtube_urls:
        video_id = extract_video_id(url)
        if video_id:
            transcript_text = get_video_transcript(video_id)
            if transcript_text:
                transcript_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO client_video_transcripts (id, client_id, video_url, transcript_text) VALUES (?, ?, ?, ?)",
                    (transcript_id, client_id, url, transcript_text)
                )
                added_urls.append(url)
    
    conn.commit()
    conn.close()
    
    return {"client_id": client_id, "added_urls": added_urls}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
