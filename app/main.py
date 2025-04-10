from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import sqlite3
import os
from pydantic import BaseModel
import shutil
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import base64
import uuid

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="SNS AI Agent Web Prototype")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS selections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        target_attributes TEXT,
        operational_purposes TEXT,
        platforms TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS uploaded_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        file_path TEXT,
        file_type TEXT,
        original_filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        account_name TEXT,
        profile_text TEXT,
        is_selected BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        script_text TEXT,
        is_selected BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None

class SelectionCreate(BaseModel):
    target_attributes: List[str]
    operational_purposes: List[str]
    platforms: List[str]

class ProfileUpdate(BaseModel):
    account_name: str
    profile_text: str

class ScriptUpdate(BaseModel):
    script_text: str

@app.post("/clients/", response_model=dict)
async def create_client(client: ClientCreate, conn: sqlite3.Connection = Depends(get_db)):
    """クライアント情報を登録するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clients (name, email) VALUES (?, ?)",
        (client.name, client.email)
    )
    conn.commit()
    client_id = cursor.lastrowid
    return {"id": client_id, "name": client.name, "email": client.email}

@app.post("/selections/", response_model=dict)
async def create_selection(
    client_id: int = Form(...),
    selection: SelectionCreate = Depends(),
    conn: sqlite3.Connection = Depends(get_db)
):
    """ターゲット属性、運用目的、プラットフォームの選択を保存するエンドポイント"""
    cursor = conn.cursor()
    
    target_attributes = ",".join(selection.target_attributes)
    operational_purposes = ",".join(selection.operational_purposes)
    platforms = ",".join(selection.platforms)
    
    cursor.execute(
        "INSERT INTO selections (client_id, target_attributes, operational_purposes, platforms) VALUES (?, ?, ?, ?)",
        (client_id, target_attributes, operational_purposes, platforms)
    )
    conn.commit()
    selection_id = cursor.lastrowid
    
    return {
        "id": selection_id,
        "client_id": client_id,
        "target_attributes": selection.target_attributes,
        "operational_purposes": selection.operational_purposes,
        "platforms": selection.platforms
    }

@app.post("/upload/", response_model=dict)
async def upload_file(
    client_id: int = Form(...),
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """ファイル（動画、テキスト、PDF）をアップロードするエンドポイント"""
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("uploads", unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO uploaded_files (client_id, file_path, file_type, original_filename) VALUES (?, ?, ?, ?)",
        (client_id, file_path, file.content_type, file.filename)
    )
    conn.commit()
    file_id = cursor.lastrowid
    
    return {
        "id": file_id,
        "client_id": client_id,
        "file_path": file_path,
        "original_filename": file.filename
    }

@app.post("/generate-profile/", response_model=dict)
async def generate_profile(
    client_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """アカウント名とプロフィールをAIが自動生成するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    selection = cursor.fetchone()
    
    if not selection:
        raise HTTPException(status_code=404, detail="Client selections not found")
    
    target_attributes = selection["target_attributes"].split(",")
    operational_purposes = selection["operational_purposes"].split(",")
    platforms = selection["platforms"].split(",")
    
    prompt = f"""
    以下の情報に基づいて、SNSアカウントの名前とプロフィール文を生成してください。
    
    ターゲット属性: {', '.join(target_attributes)}
    運用目的: {', '.join(operational_purposes)}
    プラットフォーム: {', '.join(platforms)}
    
    アカウント名とプロフィール文を以下の形式で出力してください：
    
    アカウント名: [アカウント名]
    プロフィール: [プロフィール文]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたはSNSプロフィール作成の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        
        lines = result.strip().split("\n")
        account_name = ""
        profile_text = ""
        
        for line in lines:
            if line.startswith("アカウント名:"):
                account_name = line.replace("アカウント名:", "").strip()
            elif line.startswith("プロフィール:"):
                profile_text = line.replace("プロフィール:", "").strip()
        
        cursor.execute(
            "INSERT INTO profiles (client_id, account_name, profile_text) VALUES (?, ?, ?)",
            (client_id, account_name, profile_text)
        )
        conn.commit()
        profile_id = cursor.lastrowid
        
        return {
            "id": profile_id,
            "client_id": client_id,
            "account_name": account_name,
            "profile_text": profile_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating profile: {str(e)}")

@app.put("/profiles/{profile_id}", response_model=dict)
async def update_profile(
    profile_id: int,
    profile: ProfileUpdate,
    conn: sqlite3.Connection = Depends(get_db)
):
    """生成されたプロフィールを更新するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE profiles SET account_name = ?, profile_text = ? WHERE id = ?",
        (profile.account_name, profile.profile_text, profile_id)
    )
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "id": profile_id,
        "account_name": profile.account_name,
        "profile_text": profile.profile_text
    }

@app.post("/generate-script/", response_model=dict)
async def generate_script(
    client_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """台本を生成するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    selection = cursor.fetchone()
    
    if not selection:
        raise HTTPException(status_code=404, detail="Client selections not found")
    
    cursor.execute(
        "SELECT account_name, profile_text FROM profiles WHERE client_id = ? AND is_selected = 1 ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    profile = cursor.fetchone()
    
    target_attributes = selection["target_attributes"].split(",")
    operational_purposes = selection["operational_purposes"].split(",")
    platforms = selection["platforms"].split(",")
    
    prompt = f"""
    以下の情報に基づいて、SNS投稿用の台本を生成してください。
    
    ターゲット属性: {', '.join(target_attributes)}
    運用目的: {', '.join(operational_purposes)}
    プラットフォーム: {', '.join(platforms)}
    """
    
    if profile:
        prompt += f"""
        アカウント名: {profile['account_name']}
        プロフィール: {profile['profile_text']}
        """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたはSNS台本作成の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        script_text = response.choices[0].message.content
        
        cursor.execute(
            "INSERT INTO scripts (client_id, script_text) VALUES (?, ?)",
            (client_id, script_text)
        )
        conn.commit()
        script_id = cursor.lastrowid
        
        return {
            "id": script_id,
            "client_id": client_id,
            "script_text": script_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating script: {str(e)}")

@app.put("/scripts/{script_id}", response_model=dict)
async def update_script(
    script_id: int,
    script: ScriptUpdate,
    conn: sqlite3.Connection = Depends(get_db)
):
    """生成された台本を更新するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE scripts SET script_text = ? WHERE id = ?",
        (script.script_text, script_id)
    )
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Script not found")
    
    return {
        "id": script_id,
        "script_text": script.script_text
    }

@app.post("/select-profile/{profile_id}", response_model=dict)
async def select_profile(
    profile_id: int,
    client_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """特定のプロフィールを選択するエンドポイント"""
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE profiles SET is_selected = 0 WHERE client_id = ?",
        (client_id,)
    )
    
    cursor.execute(
        "UPDATE profiles SET is_selected = 1 WHERE id = ? AND client_id = ?",
        (profile_id, client_id)
    )
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Profile not found or does not belong to client")
    
    return {"success": True, "profile_id": profile_id}

@app.post("/select-script/{script_id}", response_model=dict)
async def select_script(
    script_id: int,
    client_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """特定の台本を選択するエンドポイント"""
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE scripts SET is_selected = 0 WHERE client_id = ?",
        (client_id,)
    )
    
    cursor.execute(
        "UPDATE scripts SET is_selected = 1 WHERE id = ? AND client_id = ?",
        (script_id, client_id)
    )
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Script not found or does not belong to client")
    
    return {"success": True, "script_id": script_id}

@app.get("/clients/{client_id}/profiles", response_model=List[dict])
async def get_client_profiles(
    client_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアントのプロフィール一覧を取得するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, account_name, profile_text, is_selected FROM profiles WHERE client_id = ? ORDER BY created_at DESC",
        (client_id,)
    )
    profiles = [dict(row) for row in cursor.fetchall()]
    return profiles

@app.get("/clients/{client_id}/scripts", response_model=List[dict])
async def get_client_scripts(
    client_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアントの台本一覧を取得するエンドポイント"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, script_text, is_selected FROM scripts WHERE client_id = ? ORDER BY created_at DESC",
        (client_id,)
    )
    scripts = [dict(row) for row in cursor.fetchall()]
    return scripts

@app.get("/options", response_model=dict)
async def get_options():
    """選択肢の一覧を取得するエンドポイント"""
    return {
        "target_attributes": [
            "10代", "20代前半", "20代後半", "30代前半", "30代後半", "40代", "50代以上",
            "男性", "女性", "その他",
        ],
        "operational_purposes": [
            "ブランド認知", "商品販売", "リード獲得", "コミュニティ形成", "顧客サポート",
            "採用活動", "教育/情報提供", "エンターテイメント", "社会貢献"
        ],
        "platforms": [
            "YouTube", "Instagram", "TikTok"
        ]
    }

@app.get("/", response_class=RedirectResponse)
async def root():
    """ルートエンドポイント - 静的ファイルにリダイレクト"""
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
