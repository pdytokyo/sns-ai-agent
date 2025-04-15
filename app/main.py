from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Security, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
# from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List, Optional
import sqlite3
import os
import json
from pydantic import BaseModel
import shutil
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import base64
import uuid
import secrets
import sys
import threading
import logging
import traceback
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_enhancement import research_detailed_success_case, store_success_case, collect_copyright_free_audio, store_audio_tracks, init_db as init_enhanced_db
from competitor_analysis import get_youtube_transcript, analyze_competitor_script, store_competitor_script
from video_processing import process_video
from auto_research import start_auto_research_thread, run_auto_research
from script_generator import generate_script_proposals, store_script_proposals
from shooting_instructions_generator import generate_shooting_instructions, store_shooting_instructions
from subtitle_generator import generate_subtitles, store_subtitles
from config import OPENAI_API_KEY
from bgm_integrator import create_final_video

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not found in environment variables")

def setup_logging():
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    logger = logging.getLogger("sns-ai-agent")
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler(os.path.join(logs_dir, "app.log"))
    file_handler.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("static/uploaded_videos", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("uploaded_videos", exist_ok=True)  # 後方互換性のために維持

app = FastAPI(title="SNS AI Agent Web Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploaded_videos", StaticFiles(directory="static/uploaded_videos"), name="uploaded_videos")
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時に実行される処理"""
    try:
        logger.info("アプリケーション起動")
        
        required_dirs = ["static", "static/uploaded_videos", "output", "uploads", "uploaded_videos"]
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"ディレクトリ確認: {directory}")
        
        logger.info("拡張データベーステーブルの初期化...")
        init_enhanced_db()
        logger.info("拡張データベーステーブルの初期化完了")
        
        conn = sqlite3.connect("data.db", check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploads'")
        if not cursor.fetchone():
            logger.warning("uploads テーブルが存在しません。テーブルを作成します。")
            init_db()
        else:
            logger.info("データベーステーブル確認OK")
            
        conn.close()
        
        try:
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scheduler import start_scheduler_thread
            scheduler_thread = start_scheduler_thread()
            logger.info("トレンド収集スケジューラ起動完了")
        except Exception as e:
            logger.warning(f"トレンド収集スケジューラの起動に失敗しました: {str(e)}")
            logger.warning(traceback.format_exc())
        
        logger.info("アプリケーション起動完了")
    except Exception as e:
        logger.error(f"起動中にエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())

# security = HTTPBasic()

# def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
#     
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Basic"},
#         )
#     
#     return credentials.username

# class AuthMiddleware:
#     def __init__(self, app):
#         self.app = app
# 
#     async def __call__(self, scope, receive, send):
#         if scope["type"] != "http":
#             return await self.app(scope, receive, send)
#         
#         path = scope.get("path", "")
#         if path.startswith("/static/"):
#             return await self.app(scope, receive, send)
#         
#         headers = dict(scope.get("headers", []))
#         auth_header = headers.get(b"authorization", b"").decode("utf-8")
#         
#         if not auth_header.startswith("Basic "):
#             return await self.handle_unauthorized(scope, receive, send)
#         
#         try:
#             auth_data = auth_header.replace("Basic ", "")
#             decoded = base64.b64decode(auth_data).decode("utf-8")
#             username, password = decoded.split(":")
#             
#             if username != "user" or password != "f047be9dc32d4a76824fcbf63823398d":
#                 return await self.handle_unauthorized(scope, receive, send)
#                 
#         except Exception:
#             return await self.handle_unauthorized(scope, receive, send)
#         
#         return await self.app(scope, receive, send)
#     
#     async def handle_unauthorized(self, scope, receive, send):
#         await send({
#             "type": "http.response.start",
#             "status": 401,
#             "headers": [
#                 (b"content-type", b"text/plain"),
#                 (b"www-authenticate", b"Basic realm=SNS AI Agent"),
#             ],
#         })
#         await send({
#             "type": "http.response.body",
#             "body": b"Unauthorized",
#         })

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(AuthMiddleware)


def get_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.db"))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
        
def get_data_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data.db"))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.db"))
    conn = sqlite3.connect(db_path)
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
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS client_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        sns_platform TEXT,
        description TEXT,
        youtube_urls TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    
    data_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data.db"))
    if os.path.exists(data_db_path):
        conn = sqlite3.connect(data_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            sns_platform TEXT,
            description TEXT,
            youtube_urls TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        
        cursor.execute("PRAGMA table_info(competitor_analysis)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "analyzed_at" not in column_names:
            print("Adding analyzed_at column to competitor_analysis table")
            cursor.execute('''
            ALTER TABLE competitor_analysis ADD COLUMN analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
class CompetitorVideoAnalyze(BaseModel):
    platform: str
    industry: str
    video_url: str

class ClientInfoCreate(BaseModel):
    name: str
    email: Optional[str] = None
    sns_platform: List[str]
    description: str
    youtube_urls: List[str]
    created_at: Optional[datetime] = None
    
@app.post("/api/save-client-info", response_model=dict)
async def save_client_info(client_info: ClientInfoCreate):
    """クライアント情報を保存するAPI"""
    try:
        data_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data.db"))
        conn = sqlite3.connect(data_db_path)
        cursor = conn.cursor()
        
        sns_platform_str = ",".join(client_info.sns_platform)
        youtube_urls_str = "\n".join(client_info.youtube_urls)
        
        cursor.execute(
            """
            INSERT INTO client_info 
            (name, email, sns_platform, description, youtube_urls)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                client_info.name,
                client_info.email,
                sns_platform_str,
                client_info.description,
                youtube_urls_str
            )
        )
        
        conn.commit()
        client_id = cursor.lastrowid
        conn.close()
        
        return {"success": True, "clientId": client_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"クライアント情報の保存に失敗しました: {str(e)}")

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
    
    target_attributes = selection[0].split(",")
    operational_purposes = selection[1].split(",")
    platforms = selection[2].split(",")
    
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
    """データドリブン型の台本を生成するエンドポイント"""
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
    
    target_attributes = selection[0].split(",")
    operational_purposes = selection[1].split(",")
    platforms = selection[2].split(",")
    
    platform = platforms[0] if platforms else "YouTube"
    cursor.execute(
        "SELECT full_script, keywords, empathy_points, hook FROM competitor_scripts WHERE platform = ? ORDER BY created_at DESC LIMIT 1",
        (platform,)
    )
    competitor_data = cursor.fetchone()
    
    cursor.execute(
        "SELECT buzz_point, top_comments, trend_topics FROM detailed_success_cases WHERE platform = ? ORDER BY created_at DESC LIMIT 1",
        (platform,)
    )
    success_case = cursor.fetchone()
    
    prompt = f"""
    以下の情報に基づいて、SNS投稿用の台本を生成してください。
    
    ターゲット属性: {', '.join(target_attributes)}
    運用目的: {', '.join(operational_purposes)}
    プラットフォーム: {', '.join(platforms)}
    """
    
    if profile:
        prompt += f"""
        アカウント名: {profile[0]}
        プロフィール: {profile[1]}
        """
    
    if competitor_data:
        keywords = json.loads(competitor_data[1]) if isinstance(competitor_data[1], str) else competitor_data[1]
        empathy_points = json.loads(competitor_data[2]) if isinstance(competitor_data[2], str) else competitor_data[2]
        hook = competitor_data[3]
        
        prompt += f"""
        【必須事項】:
        - 冒頭フック: 「{hook}」を基にリライト
        - キーワード: 「{', '.join(keywords[:3])}」を含める
        - 共感ポイント: 「{', '.join(empathy_points[:2])}」を活用する
        """
    
    if success_case:
        trend_topics = json.loads(success_case[2]) if isinstance(success_case[2], str) else success_case[2]
        buzz_point = success_case[0].split(" - ")[1] if " - " in success_case[0] else success_case[0]
        
        prompt += f"""
        - トレンドトピック: 「{', '.join(trend_topics[:2])}」を含める
        - 注目ポイント: 「{buzz_point}」に関連する内容を含める
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
    """ルートエンドポイント - クライアントワークフローにリダイレクト"""
    return RedirectResponse(url="/static/client_workflow.html")

@app.post("/collect_success_cases/", response_model=dict)
async def collect_success_cases(
    platform: str = Form(...),
    industry: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """指定したプラットフォームと業界の成功動画を収集し、DBに格納するエンドポイント"""
    try:
        def background_task():
            try:
                success_case = research_detailed_success_case(platform, industry)
                case_id = store_success_case(platform, industry, success_case)
                print(f"成功事例の収集が完了しました。ID: {case_id}")
            except Exception as e:
                print(f"成功事例の収集中にエラーが発生しました: {str(e)}")
        
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()
        
        return {
            "success": True,
            "message": "成功事例の収集をバックグラウンドで開始しました。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"成功事例の収集の開始中にエラーが発生しました: {str(e)}")

@app.post("/start-auto-research/", response_model=dict)
async def start_auto_research_endpoint(
    client_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアント向けの自動リサーチを開始するエンドポイント"""
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
            (client_id,)
        )
        selection = cursor.fetchone()
        
        if not selection:
            raise HTTPException(status_code=400, detail="クライアント選択情報が見つかりません")
        
        platforms = selection[0].split(",")
        
        start_auto_research_thread(client_id, platforms)
        
        return {
            "success": True,
            "message": "自動リサーチを開始しました。バックグラウンドで処理が続きます。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自動リサーチの開始中にエラーが発生しました: {str(e)}")

@app.get("/research-status/{client_id}", response_model=dict)
async def get_research_status(
    client_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアントの自動リサーチ状況を取得するエンドポイント"""
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT research_status FROM clients WHERE id = ?",
            (client_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="クライアント情報が見つかりません")
        
        return {
            "success": True,
            "status": result[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リサーチ状況の取得中にエラーが発生しました: {str(e)}")

@app.post("/generate-script-proposals/", response_model=dict)
async def generate_script_proposals_endpoint(
    client_id: int = Form(...),
    num_proposals: int = Form(3),
    conn: sqlite3.Connection = Depends(get_db)
):
    """複数の台本提案を生成するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT research_status FROM clients WHERE id = ?",
            (client_id,)
        )
        client = cursor.fetchone()
        
        if not client or client[0] != "completed":
            cursor.execute(
                "SELECT platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
                (client_id,)
            )
            selection = cursor.fetchone()
            
            if not selection:
                raise HTTPException(status_code=400, detail="クライアント選択情報が見つかりません")
            
            platforms = selection[0].split(",")
            
            start_auto_research_thread(client_id, platforms)
            
            return {
                "success": True,
                "status": "research_in_progress",
                "message": "自動リサーチを開始しました。しばらくお待ちください。"
            }
        
        proposals = generate_script_proposals(client_id, num_proposals)
        proposal_ids = store_script_proposals(client_id, proposals)
        
        return {
            "success": True,
            "status": "completed",
            "proposal_ids": proposal_ids,
            "proposals": proposals
        }
    
    except Exception as e: 
        raise HTTPException(status_code=500, detail=f"台本提案の生成中にエラーが発生しました: {str(e)}")

@app.get("/script-proposals/{client_id}", response_model=List[dict])
async def get_script_proposals(
    client_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアントの台本提案一覧を取得するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content, is_selected FROM script_proposals WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,)
        )
        proposals = [dict(row) for row in cursor.fetchall()]
        return proposals
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"台本提案の取得中にエラーが発生しました: {str(e)}")

@app.post("/select-script-proposal/{proposal_id}", response_model=dict)
async def select_script_proposal(
    proposal_id: int,
    client_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """特定の台本提案を選択するエンドポイント"""
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE script_proposals SET is_selected = 0 WHERE client_id = ?",
            (client_id,)
        )
        
        cursor.execute(
            "UPDATE script_proposals SET is_selected = 1 WHERE id = ? AND client_id = ?",
            (proposal_id, client_id)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="台本提案が見つかりません")
        
        return {
            "success": True,
            "proposal_id": proposal_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"台本提案の選択中にエラーが発生しました: {str(e)}")

@app.post("/generate-shooting-instructions/", response_model=dict)
async def generate_shooting_instructions_endpoint(
    client_id: int = Form(...),
    script_proposal_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """撮影指示書を生成するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM script_proposals WHERE id = ? AND client_id = ? AND is_selected = 1",
            (script_proposal_id, client_id)
        )
        proposal = cursor.fetchone()
        
        if not proposal:
            raise HTTPException(status_code=400, detail="選択された台本提案が見つかりません")
        
        instructions = generate_shooting_instructions(client_id, script_proposal_id)
        instruction_id = store_shooting_instructions(client_id, script_proposal_id, instructions)
        
        return {
            "success": True,
            "instruction_id": instruction_id,
            "content": instructions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撮影指示書の生成中にエラーが発生しました: {str(e)}")

@app.get("/shooting-instructions/{client_id}", response_model=dict)
async def get_shooting_instructions(
    client_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアントの最新の撮影指示書を取得するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT si.id, si.content, sp.title as script_title 
            FROM shooting_instructions si
            JOIN script_proposals sp ON si.script_proposal_id = sp.id
            WHERE si.client_id = ?
            ORDER BY si.created_at DESC
            LIMIT 1
            """,
            (client_id,)
        )
        instruction = cursor.fetchone()
        
        if not instruction:
            raise HTTPException(status_code=404, detail="撮影指示書が見つかりません")
        
        return {
            "id": instruction[0],
            "content": instruction[1],
            "script_title": instruction[2]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撮影指示書の取得中にエラーが発生しました: {str(e)}")

@app.post("/generate-subtitles/", response_model=dict)
async def generate_subtitles_endpoint(
    processed_video_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """字幕を生成するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM processed_videos WHERE id = ?",
            (processed_video_id,)
        )
        video = cursor.fetchone()
        
        if not video:
            raise HTTPException(status_code=404, detail="処理済み動画が見つかりません")
        
        subtitles = generate_subtitles(processed_video_id)
        subtitle_ids = store_subtitles(processed_video_id, subtitles)
        
        return {
            "success": True,
            "subtitle_ids": subtitle_ids,
            "subtitles": subtitles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"字幕の生成中にエラーが発生しました: {str(e)}")

@app.get("/subtitles/{processed_video_id}", response_model=List[dict])
async def get_subtitles(
    processed_video_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """処理済み動画の字幕を取得するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, start_time, end_time, text FROM subtitles WHERE processed_video_id = ? ORDER BY start_time",
            (processed_video_id,)
        )
        subtitles = []
        for row in cursor.fetchall():
            subtitles.append({
                "id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "text": row[3]
            })
        return subtitles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"字幕の取得中にエラーが発生しました: {str(e)}")

@app.post("/bgm-integration/", response_model=dict)
async def bgm_integration_endpoint(
    processed_video_id: int = Form(...),
    bgm_id: int = Form(...),
    bgm_volume: float = Form(0.5),
    conn: sqlite3.Connection = Depends(get_db)
):
    """BGMを挿入した最終動画を作成するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM processed_videos WHERE id = ?",
            (processed_video_id,)
        )
        video = cursor.fetchone()
        
        if not video:
            raise HTTPException(status_code=404, detail="処理済み動画が見つかりません")
        
        cursor.execute(
            "SELECT id FROM copyright_free_audio WHERE id = ?",
            (bgm_id,)
        )
        bgm = cursor.fetchone()
        
        if not bgm:
            raise HTTPException(status_code=404, detail="BGMが見つかりません")
        
        final_video_id = create_final_video(processed_video_id, bgm_id, bgm_volume)
        
        cursor.execute(
            "SELECT output_path FROM final_videos WHERE id = ?",
            (final_video_id,)
        )
        final_video = cursor.fetchone()
        
        output_rel_path = final_video[0].replace("app/", "/")
        
        return {
            "success": True,
            "final_video_id": final_video_id,
            "output_path": output_rel_path,
            "preview_url": f"/static/preview.html?video={output_rel_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BGM挿入中にエラーが発生しました: {str(e)}")

@app.get("/final-videos/{client_id}", response_model=List[dict])
async def get_final_videos(
    client_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """クライアントの最終動画一覧を取得するエンドポイント"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fv.id, fv.output_path, fv.bgm_volume, cfa.title as bgm_title
            FROM final_videos fv
            JOIN copyright_free_audio cfa ON fv.bgm_id = cfa.id
            WHERE fv.client_id = ?
            ORDER BY fv.created_at DESC
            """,
            (client_id,)
        )
        videos = []
        for row in cursor.fetchall():
            output_rel_path = row["output_path"].replace("app/", "/")
            videos.append({
                "id": row["id"],
                "output_path": output_rel_path,
                "preview_url": f"/static/preview.html?video={output_rel_path}",
                "bgm_title": row["bgm_title"],
                "bgm_volume": row["bgm_volume"]
            })
        return videos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"最終動画の取得中にエラーが発生しました: {str(e)}")

@app.post("/analyze_competitor_video/", response_model=dict)
async def analyze_competitor_video(
    competitor: CompetitorVideoAnalyze,
    conn: sqlite3.Connection = Depends(get_db)
):
    """競合動画を分析し、台本・キーワード・共感ポイント・フックを抽出するエンドポイント"""
    try:
        transcript_text = get_youtube_transcript(competitor.video_url)
        
        analysis_result = analyze_competitor_script(transcript_text)
        
        script_id = store_competitor_script(
            competitor.platform,
            competitor.industry,
            competitor.video_url,
            transcript_text,
            analysis_result
        )
        
        return {
            "success": True,
            "id": script_id,
            "platform": competitor.platform,
            "industry": competitor.industry,
            "video_url": competitor.video_url,
            "keywords": analysis_result["keywords"],
            "empathy_points": analysis_result["empathy_points"],
            "hook": analysis_result["hook"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"競合動画の分析中にエラーが発生しました: {str(e)}")

@app.post("/fetch_free_bgm/", response_model=dict)
async def fetch_free_bgm(
    genre: Optional[str] = Form(None),
    mood: Optional[str] = Form(None),
    limit: int = Form(10),
    conn: sqlite3.Connection = Depends(get_db)
):
    """著作権フリー音源を取得・DBに格納するエンドポイント"""
    try:
        audio_tracks = collect_copyright_free_audio(genre, mood, limit)
        
        store_audio_tracks(audio_tracks)
        
        return {
            "success": True,
            "tracks": audio_tracks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"著作権フリー音源の取得中にエラーが発生しました: {str(e)}")
        
@app.get("/bgm_library/", response_model=List[dict])
async def get_bgm_library(
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db)
):
    """著作権フリー音源ライブラリを取得するエンドポイント"""
    cursor = conn.cursor()
    
    query = "SELECT id, title, artist, genre, mood, duration, file_path, source FROM copyright_free_audio"
    params = []
    
    if genre or mood:
        query += " WHERE"
        if genre:
            query += " genre = ?"
            params.append(genre)
        if mood:
            if genre:
                query += " AND"
            query += " mood = ?"
            params.append(mood)
    
    cursor.execute(query, params)
    tracks = cursor.fetchall()
    
    result = []
    for track in tracks:
        result.append({
            "id": track[0],
            "title": track[1],
            "artist": track[2],
            "genre": track[3],
            "mood": track[4],
            "duration": track[5],
            "file_path": track[6],
            "source": track[7]
        })
    
    return result

@app.post("/process_video/", response_model=dict)
async def process_video_endpoint(
    client_id: int = Form(...),
    video_id: int = Form(...),
    aspect_ratio: str = Form("16:9"),
    silence_threshold: float = Form(0.02),
    start_margin: float = Form(0.5),
    end_margin: float = Form(0.5),
    conn: sqlite3.Connection = Depends(get_db)
):
    """動画を処理するエンドポイント（アスペクト比変更、ジェットカット）"""
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT file_path FROM uploads WHERE id = ? AND client_id = ?",
            (video_id, client_id)
        )
        upload = cursor.fetchone()
        
        if not upload:
            raise HTTPException(status_code=404, detail="動画が見つかりません")
        
        input_path = upload["file_path"]
        
        result = process_video(
            input_path=input_path,
            aspect_ratio=aspect_ratio,
            silence_threshold=silence_threshold,
            start_margin=start_margin,
            end_margin=end_margin
        )
        
        cursor.execute(
            "INSERT INTO processed_videos (client_id, original_video_id, output_path, aspect_ratio, processing_info) VALUES (?, ?, ?, ?, ?)",
            (
                client_id,
                video_id,
                result["output_path"],
                aspect_ratio,
                json.dumps(result)
            )
        )
        conn.commit()
        processed_id = cursor.lastrowid
        
        output_rel_path = result["output_path"].replace("app/", "/")
        
        return {
            "success": True,
            "id": processed_id,
            "client_id": client_id,
            "original_video_id": video_id,
            "output_path": output_rel_path,
            "preview_url": f"/static/preview.html?video={output_rel_path}",
            "aspect_ratio": aspect_ratio,
            "original_duration": result["original_duration"],
            "processed_duration": result["processed_duration"],
            "reduction_percentage": result["reduction_percentage"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"動画処理中にエラーが発生しました: {str(e)}")

@app.get("/video_info/{video_id}", response_model=dict)
async def get_video_info(
    video_id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    """処理済み動画の情報を取得するエンドポイント"""
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT processing_info, aspect_ratio FROM processed_videos WHERE id = ?",
        (video_id,)
    )
    video = cursor.fetchone()
    
    if not video:
        raise HTTPException(status_code=404, detail="動画情報が見つかりません")
    
    processing_info = json.loads(video["processing_info"])
    
    return {
        "original_duration": processing_info["original_duration"],
        "processed_duration": processing_info["processed_duration"],
        "reduction_percentage": processing_info["reduction_percentage"],
        "aspect_ratio": video["aspect_ratio"],
        "silent_segments": processing_info["silent_segments"]
    }

@app.post("/upload_video/", response_model=dict)
async def upload_video(
    file: UploadFile = File(...),
    client_id: int = Form(...),
    aspect_ratio: str = Form("16:9"),
    margin_seconds: float = Form(0.5),
    conn: sqlite3.Connection = Depends(get_data_db)
):
    """動画をアップロードし、アスペクト比とマージン設定を保存するエンドポイント"""
    try:
        logger.info(f"動画アップロード開始: ファイル名={file.filename}, client_id={client_id}")
        logger.debug(f"パラメータ: aspect_ratio={aspect_ratio}, margin_seconds={margin_seconds}")
        
        os.makedirs("static/uploaded_videos", exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("static/uploaded_videos", unique_filename)
        
        logger.debug(f"ファイル保存先: {file_path}")
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.debug(f"ファイル保存成功: {file_path}")
        except Exception as file_error:
            logger.error(f"ファイル保存エラー: {str(file_error)}")
            logger.error(traceback.format_exc())
            raise Exception(f"ファイル保存中にエラーが発生しました: {str(file_error)}")
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO uploads (filename, original_path, aspect_ratio, margin_seconds, client_id) VALUES (?, ?, ?, ?, ?)",
                (unique_filename, file_path, aspect_ratio, margin_seconds, client_id)
            )
            conn.commit()
            upload_id = cursor.lastrowid
            logger.debug(f"DB登録成功: id={upload_id}")
        except Exception as db_error:
            logger.error(f"DB登録エラー: {str(db_error)}")
            logger.error(traceback.format_exc())
            raise Exception(f"データベース登録中にエラーが発生しました: {str(db_error)}")
        
        logger.info(f"動画アップロード完了: id={upload_id}, ファイル名={unique_filename}")
        
        return {
            "success": True,
            "video_id": upload_id,
            "filename": unique_filename,
            "original_filename": file.filename,
            "aspect_ratio": aspect_ratio,
            "margin_seconds": margin_seconds,
            "client_id": client_id,
            "video_path": file_path,
            "video_url": f"/uploaded_videos/{unique_filename}"
        }
    except Exception as e:
        logger.error(f"動画アップロード中にエラーが発生しました: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"動画アップロード中にエラーが発生しました: {str(e)}")

@app.post("/process_uploaded_video/", response_model=dict)
async def process_uploaded_video(
    upload_id: int = Form(...),
    silence_threshold: float = Form(0.02),
    conn: sqlite3.Connection = Depends(get_db)
):
    """アップロードされた動画を処理するエンドポイント"""
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, filename, aspect_ratio, margin_seconds, client_id FROM uploads WHERE id = ?",
            (upload_id,)
        )
        upload = cursor.fetchone()
        
        if not upload:
            raise HTTPException(status_code=404, detail="アップロードされた動画が見つかりません")
        
        upload_id, filename, aspect_ratio, margin_seconds, client_id = upload
        
        input_path = os.path.join("uploaded_videos", filename)
        
        if not os.path.exists(input_path):
            raise HTTPException(status_code=404, detail="動画ファイルが見つかりません")
        
        result = process_video(
            input_path=input_path,
            aspect_ratio=aspect_ratio,
            silence_threshold=silence_threshold,
            start_margin=margin_seconds,
            end_margin=margin_seconds
        )
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id INTEGER,
            client_id INTEGER,
            output_path TEXT,
            aspect_ratio TEXT,
            processing_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (upload_id) REFERENCES uploads (id),
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute(
            "INSERT INTO processed_videos (upload_id, client_id, output_path, aspect_ratio, processing_info) VALUES (?, ?, ?, ?, ?)",
            (
                upload_id,
                client_id,
                result["output_path"],
                aspect_ratio,
                json.dumps(result)
            )
        )
        conn.commit()
        processed_id = cursor.lastrowid
        
        output_rel_path = result["output_path"].replace("app/", "/")
        
        return {
            "success": True,
            "id": processed_id,
            "upload_id": upload_id,
            "client_id": client_id,
            "output_path": output_rel_path,
            "preview_url": f"/static/preview.html?video={output_rel_path}",
            "aspect_ratio": aspect_ratio,
            "original_duration": result["original_duration"],
            "processed_duration": result["processed_duration"],
            "reduction_percentage": result["reduction_percentage"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"動画処理中にエラーが発生しました: {str(e)}")

@app.get("/api/trends/latest")
async def get_latest_trends():
    """最新のトレンドデータを取得するAPI"""
    try:
        conn = sqlite3.connect("data.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        trends = {}
        platforms = ["Google", "YouTube", "TikTok"]
        
        for platform in platforms:
            cursor.execute("""
                SELECT keyword, rank, collected_at 
                FROM weekly_trends 
                WHERE platform = ? 
                ORDER BY collected_at DESC, rank ASC 
                LIMIT 10
            """, (platform,))
            
            platform_trends = [dict(row) for row in cursor.fetchall()]
            trends[platform.lower()] = platform_trends
        
        conn.close()
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"トレンドデータの取得に失敗しました: {str(e)}")

@app.get("/api/competitor-analysis/latest")
async def get_latest_competitor_analysis():
    """最新の競合分析データを取得するAPI"""
    try:
        conn = sqlite3.connect("data.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        analysis = {}
        platforms = ["YouTube", "Instagram", "TikTok"]
        
        for platform in platforms:
            cursor.execute("""
                SELECT * FROM competitor_analysis 
                WHERE platform = ? 
                ORDER BY analyzed_at DESC 
                LIMIT 5
            """, (platform,))
            
            platform_analysis = [dict(row) for row in cursor.fetchall()]
            analysis[platform.lower()] = platform_analysis
        
        conn.close()
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"競合分析データの取得に失敗しました: {str(e)}")

@app.get("/api/script-usage/stats")
async def get_script_usage_stats():
    """台本の利用統計データを取得するAPI"""
    try:
        conn = sqlite3.connect("app.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as count
            FROM scripts
            GROUP BY month
            ORDER BY month DESC
            LIMIT 6
        """)
        
        monthly_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {
            "monthly_stats": monthly_stats
        }
    except Exception as e:
        sample_data = [
            {"month": "2024-04", "count": 12},
            {"month": "2024-03", "count": 8},
            {"month": "2024-02", "count": 15},
            {"month": "2024-01", "count": 10},
            {"month": "2023-12", "count": 7},
            {"month": "2023-11", "count": 5}
        ]
        return {
            "monthly_stats": sample_data
        }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """分析ダッシュボードページを提供"""
    return FileResponse("app/static/dashboard.html")

@app.get("/instagram-analysis", response_class=HTMLResponse)
async def instagram_analysis_dashboard():
    """Instagram分析ダッシュボードページを提供（統合版ダッシュボードにリダイレクト）"""
    return RedirectResponse(url="/static/dashboard.html#instagram-analysis-tab")

@app.post("/analyze-instagram-post/", response_model=dict)
async def analyze_instagram_post(
    post_url: str = Form(...),
    client_id: Optional[int] = Form(None)
):
    """Instagram投稿を分析するエンドポイント"""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from instagram_analyzer import process_instagram_post
    
    result = process_instagram_post(post_url, client_id)
    return result

@app.get("/get-instagram-analysis/", response_model=dict)
async def get_instagram_analysis(post_id: Optional[int] = None):
    """Instagram分析結果を取得するエンドポイント"""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from instagram_analyzer import get_instagram_analysis
    
    if post_id:
        result = get_instagram_analysis(post_id)
        if not result:
            raise HTTPException(status_code=404, detail="Instagram analysis not found")
        return result
    else:
        return {"results": get_instagram_analysis()}

@app.get("/api/get-script-proposals", response_model=dict)
async def api_get_script_proposals(
    clientId: int,
    conn: sqlite3.Connection = Depends(get_data_db)
):
    """クライアントの台本提案一覧を取得するAPIエンドポイント（クライアントワークフロー用）"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content, is_selected FROM script_proposals WHERE client_id = ? ORDER BY created_at DESC",
            (clientId,)
        )
        proposals = [dict(row) for row in cursor.fetchall()]
        
        if not proposals:
            dummy_proposals = [
                {
                    "id": 9999,
                    "title": "【ダミー】視聴者を惹きつける商品紹介動画",
                    "content": "こんにちは！今日は皆さんにとっておきの商品をご紹介します。\n\n最初に商品の特徴を簡単に説明し、実際の使用シーンを見せていきましょう。\n\n商品の魅力的なポイントを3つに絞って順番に解説します。\n\n最後に、限定特典や購入方法についてご案内します。",
                    "is_selected": 0
                },
                {
                    "id": 9998,
                    "title": "【ダミー】トレンドを取り入れた会社紹介",
                    "content": "皆さんこんにちは！\n\n今日は当社の魅力をお伝えします。\n\n創業からの歴史や、私たちが大切にしている価値観についてお話しします。\n\n実際のお客様の声もいくつかご紹介します。\n\n最後に、今後の展望や取り組みについてお伝えします。ぜひ最後までご覧ください！",
                    "is_selected": 0
                },
                {
                    "id": 9997,
                    "title": "【ダミー】エンゲージメントを高めるハウツー動画",
                    "content": "今回は、誰でも簡単にできる方法をご紹介します！\n\n最初に全体の流れを説明し、必要な準備をお伝えします。\n\nステップ1: まずは基本的なポイントをマスターしましょう。\nステップ2: ここからが本題です。詳しく解説していきます。\nステップ3: 最後の仕上げをして完成させます。\n\n実践してみた結果や、よくある質問についても触れていきます。",
                    "is_selected": 0
                }
            ]
            return {
                "success": True,
                "proposals": dummy_proposals
            }
        
        return {
            "success": True,
            "proposals": proposals
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"台本提案の取得中にエラーが発生しました: {str(e)}"
        }

@app.get("/api/generate-shooting-instructions", response_model=dict)
async def api_generate_shooting_instructions(
    proposalId: int,
    conn: sqlite3.Connection = Depends(get_data_db)
):
    """撮影指示書を生成するAPIエンドポイント（クライアントワークフロー用）"""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT client_id FROM script_proposals WHERE id = ?",
            (proposalId,)
        )
        proposal = cursor.fetchone()
        
        if not proposal:
            return {"success": False, "message": "台本提案が見つかりません"}
        
        client_id = proposal[0]
        instructions = generate_shooting_instructions(client_id, proposalId)
        instruction_id = store_shooting_instructions(client_id, proposalId, instructions)
        
        return {"success": True, "instruction_id": instruction_id, "instructions": instructions}
    except Exception as e:
        return {"success": False, "message": f"撮影指示書の生成中にエラーが発生しました: {str(e)}"}

@app.post("/api/upload-video", response_model=dict)
async def api_upload_video(
    file: UploadFile = File(...),
    client_id: int = Form(...),
    aspect_ratio: str = Form("16:9"),
    margin_seconds: float = Form(0.5),
    conn: sqlite3.Connection = Depends(get_data_db)
):
    """動画をアップロードするAPIエンドポイント（クライアントワークフロー用）"""
    return await upload_video(file, client_id, aspect_ratio, margin_seconds, conn)

@app.post("/upload_video/", response_model=dict)
async def upload_video_endpoint(
    file: UploadFile = File(...),
    client_id: int = Form(...),
    aspect_ratio: str = Form("16:9"),
    margin_seconds: float = Form(0.5),
    conn: sqlite3.Connection = Depends(get_data_db)
):
    """動画をアップロードするAPIエンドポイント（音声編集UI用）"""
    return await upload_video(file, client_id, aspect_ratio, margin_seconds, conn)

class TranscribeRequest(BaseModel):
    audio_base64: str

class EditCommandRequest(BaseModel):
    text: str
    video_metadata: Optional[dict] = None

class ProcessEditRequest(BaseModel):
    client_id: Optional[int] = None
    script_id: Optional[int] = None
    command_json: str
    video_path: str

@app.post("/api/transcribe-audio", response_model=dict)
async def transcribe_audio(
    audio: UploadFile = File(...),
    client_id: str = Form(...)
):
    """音声をWhisper APIで文字起こしするエンドポイント"""
    temp_file_path = None
    try:
        import tempfile
        import uuid
        
        audio_content = await audio.read()
        
        temp_file_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(temp_file_path, "wb") as f:
            f.write(audio_content)
        
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from voice_edit_agent.voice_input import VoiceInput
        
        voice_input = VoiceInput()
        transcript = voice_input.transcribe_from_file(temp_file_path)
        
        logger.info(f"音声文字起こし成功: client_id={client_id}, transcript={transcript[:50]}...")
        
        return {"success": True, "text": transcript, "transcript": transcript}
    except Exception as e:
        logger.error(f"音声の文字起こしに失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"音声の文字起こしに失敗しました: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"一時ファイルの削除に失敗しました: {str(e)}")

@app.post("/api/voice-to-text", response_model=dict)
async def voice_to_text(audio_file: UploadFile = File(...)):
    """音声ファイルをWhisper APIで文字起こしするエンドポイント（WebUI用）"""
    try:
        temp_file_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(temp_file_path, "wb") as f:
            f.write(await audio_file.read())
        
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from voice_edit_agent.voice_input import VoiceInput
        
        voice_input = VoiceInput()
        text = voice_input.transcribe_from_file(temp_file_path)
        
        os.unlink(temp_file_path)
        
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声の文字起こしに失敗しました: {str(e)}")

@app.post("/api/natural-edit", response_model=dict)
async def natural_edit(request: EditCommandRequest):
    """自然言語を編集コマンドに変換するエンドポイント"""
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from voice_edit_agent.natural_edit_agent import NaturalEditAgent
        
        agent = NaturalEditAgent()
        edit_commands = agent.convert_to_edit_commands(request.text, request.video_metadata)
        validated_commands = agent.validate_commands(edit_commands, request.video_metadata.get("duration") if request.video_metadata else None)
        
        return {"success": True, "commands": validated_commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"編集コマンドの生成に失敗しました: {str(e)}")

class TextToEditCommandRequest(BaseModel):
    text: str
    video_id: Optional[str] = None
    video_metadata: Optional[dict] = None

@app.post("/api/text-to-edit-commands", response_model=dict)
async def text_to_edit_commands(request: TextToEditCommandRequest = Body(...)):
    """テキストを編集コマンドに変換するエンドポイント（WebUI用）"""
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from voice_edit_agent.natural_edit_agent import NaturalEditAgent
        import traceback
        
        video_metadata = request.video_metadata if request.video_metadata is not None else {}
        
        if request.video_id and (not video_metadata or video_metadata == {}):
            video_metadata = {"duration": 60.0, "resolution": "1920x1080"}
        
        agent = NaturalEditAgent()
        edit_commands = agent.convert_to_edit_commands(request.text, video_metadata)
        validated_commands = agent.validate_commands(edit_commands, video_metadata.get("duration") if video_metadata else None)
        
        return {"commands": validated_commands}
    except Exception as e:
        logger.error(f"編集コマンド生成エラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"編集コマンドの生成に失敗しました: {str(e)}")

@app.post("/api/process-edit", response_model=dict)
async def process_edit(request: ProcessEditRequest):
    """編集コマンドを適用して動画を処理するエンドポイント"""
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from voice_edit_agent.apply_edit_commands import EditCommandProcessor
        
        processor = EditCommandProcessor()
        result_path = processor.process_commands(
            json.loads(request.command_json), 
            request.video_path,
            client_id=request.client_id,
            script_id=request.script_id
        )
        
        if request.client_id:
            conn = sqlite3.connect('data.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO edit_commands (client_id, script_id, command_json, video_path, result_path) VALUES (?, ?, ?, ?, ?)",
                (request.client_id, request.script_id, request.command_json, request.video_path, result_path)
            )
            conn.commit()
            conn.close()
        
        return {
            "success": True, 
            "result_path": result_path,
            "download_url": f"/static/output/{os.path.basename(result_path)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"動画の編集に失敗しました: {str(e)}")

@app.post("/api/apply-edit-commands", response_model=dict)
async def apply_edit_commands(request: dict = Body(...)):
    """編集コマンドを適用して動画を処理するエンドポイント（WebUI用）"""
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from voice_edit_agent.apply_edit_commands import EditCommandProcessor
        
        processor = EditCommandProcessor()
        result_path = processor.process_commands(
            request["command_json"], 
            request["video_path"],
            client_id=request.get("client_id"),
            script_id=request.get("script_id")
        )
        
        if request.get("client_id"):
            conn = sqlite3.connect('data.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO edit_commands (client_id, script_id, command_json, video_path, result_path) VALUES (?, ?, ?, ?, ?)",
                (request.get("client_id"), request.get("script_id"), json.dumps(request["command_json"]), request["video_path"], result_path)
            )
            conn.commit()
            conn.close()
        
        return {
            "success": True, 
            "result_path": result_path,
            "download_url": f"/static/output/{os.path.basename(result_path)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"動画の編集に失敗しました: {str(e)}")

@app.get("/api/edit-commands", response_model=list)
async def get_edit_commands(client_id: Optional[int] = None):
    """クライアントの編集コマンド履歴を取得するエンドポイント"""
    try:
        conn = sqlite3.connect('data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if client_id:
            cursor.execute("SELECT * FROM edit_commands WHERE client_id = ? ORDER BY created_at DESC", (client_id,))
        else:
            cursor.execute("SELECT * FROM edit_commands ORDER BY created_at DESC")
        
        commands = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return commands
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"編集コマンドの取得に失敗しました: {str(e)}")

@app.get("/edit-ui")
async def edit_ui():
    """音声編集UIページを表示するエンドポイント"""
    return RedirectResponse("/static/edit_ui/index.html")

@app.get("/static/edit_ui/index.html")
async def edit_ui_static():
    """音声編集UIの静的ファイルを表示するエンドポイント"""
    return FileResponse("app/static/edit_ui/index.html")

@app.get("/edit_ui/index.html")
async def edit_ui_redirect():
    """音声編集UIページへのリダイレクト（誤ったパス対応）"""
    return RedirectResponse("/static/edit_ui/index.html")

@app.get("/api/subtitle-templates", response_model=dict)
async def get_subtitle_templates():
    """テロップスタイルテンプレート一覧を取得するエンドポイント"""
    try:
        from subtitle_templates import SUBTITLE_TEMPLATES
        return {"success": True, "templates": SUBTITLE_TEMPLATES}
    except Exception as e:
        logger.error(f"テンプレート取得エラー: {str(e)}")
        return {"success": False, "message": f"テンプレート取得エラー: {str(e)}"}

@app.post("/api/generate-subtitles", response_model=dict)
async def generate_subtitles_endpoint(request: dict = Body(...)):
    """
    テロップを生成して動画に適用するエンドポイント
    """
    try:
        video_id = request.get("video_id")
        template_id = request.get("template_id", "default")
        
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        from subtitle_templates import get_template_by_id
        template = get_template_by_id(template_id)
        
        from voice_edit_agent.voice_input import VoiceInput
        voice_input = VoiceInput()
        transcript = voice_input.transcribe_from_file(original_path)
        
        output_filename = f"subtitle_{uuid.uuid4()}.mp4"
        output_path = os.path.join("static/uploaded_videos", output_filename)
        
        from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
        
        try:
            video = VideoFileClip(original_path)
            
            font = template.get("font", "Arial")
            font_size = template.get("font_size", 24)
            color = template.get("color", "white")
            bg_color = template.get("bg_color", "rgba(0, 0, 0, 0.5)")
            position = template.get("position", "bottom")
            
            txt_clip = TextClip(
                transcript[:100] + "...", 
                fontsize=font_size, 
                font=font,
                color=color,
                bg_color=bg_color,
                method='caption'
            )
            
            if position == "bottom":
                txt_clip = txt_clip.set_position(('center', 'bottom'))
            elif position == "top":
                txt_clip = txt_clip.set_position(('center', 'top'))
            else:
                txt_clip = txt_clip.set_position('center')
            
            txt_clip = txt_clip.set_duration(video.duration)
            
            final_clip = CompositeVideoClip([video, txt_clip])
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            video.close()
            final_clip.close()
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps({"type": "subtitle", "template_id": template_id, "video_id": video_id}),
                    original_path,
                    output_path
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "edit_id": edit_id,
                "processed_video_url": f"/uploaded_videos/{output_filename}",
                "template_id": template_id
            }
        except Exception as e:
            logger.error(f"テロップ生成中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"テロップ生成中にエラーが発生しました: {str(e)}")
    except Exception as e:
        logger.error(f"テロップ生成APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/suggest-bgm", response_model=dict)
async def suggest_bgm(request: dict = Body(...)):
    """
    動画の内容を分析し、適切なBGMジャンルを提案するエンドポイント
    """
    try:
        video_id = request.get("video_id")
        
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        from voice_edit_agent.voice_input import VoiceInput
        voice_input = VoiceInput()
        transcript = voice_input.transcribe_from_file(original_path)
        
        from config import OPENAI_API_KEY
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは動画の内容を分析し、最適なBGMジャンルを提案する専門家です。"},
                    {"role": "user", "content": f"以下の動画の文字起こしを分析して、最適なBGMジャンルを3つ提案してください。それぞれのジャンルについて、なぜそのジャンルが適しているかも説明してください。\n\n文字起こし内容:\n{transcript}"}
                ],
                max_tokens=500
            )
            
            bgm_suggestion = response.choices[0].message.content
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps({"type": "bgm_suggestion", "video_id": video_id, "suggestion": bgm_suggestion}),
                    original_path,
                    ""
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            sample_bgms = [
                {
                    "id": "bgm1",
                    "name": "爽やかなアコースティック",
                    "genre": "アコースティック",
                    "url": "/static/bgm/acoustic_sample.mp3",
                    "duration": 60
                },
                {
                    "id": "bgm2",
                    "name": "エネルギッシュなロック",
                    "genre": "ロック",
                    "url": "/static/bgm/rock_sample.mp3",
                    "duration": 60
                },
                {
                    "id": "bgm3",
                    "name": "感動的なオーケストラ",
                    "genre": "オーケストラ",
                    "url": "/static/bgm/orchestra_sample.mp3",
                    "duration": 60
                },
                {
                    "id": "bgm4",
                    "name": "ポップなエレクトロ",
                    "genre": "エレクトロ",
                    "url": "/static/bgm/electro_sample.mp3",
                    "duration": 60
                },
                {
                    "id": "bgm5",
                    "name": "落ち着いたジャズ",
                    "genre": "ジャズ",
                    "url": "/static/bgm/jazz_sample.mp3",
                    "duration": 60
                }
            ]
            
            return {
                "success": True,
                "edit_id": edit_id,
                "suggestion": bgm_suggestion,
                "bgm_samples": sample_bgms
            }
        except Exception as e:
            logger.error(f"BGM提案生成中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"BGM提案生成中にエラーが発生しました: {str(e)}")
    except Exception as e:
        logger.error(f"BGM提案APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/apply-bgm", response_model=dict)
async def apply_bgm(request: dict = Body(...)):
    """
    選択されたBGMを動画に適用するエンドポイント
    """
    try:
        video_id = request.get("video_id")
        bgm_id = request.get("bgm_id")
        volume = request.get("volume", 0.3)  # デフォルトのボリューム
        
        if not video_id or not bgm_id:
            raise HTTPException(status_code=400, detail="video_id and bgm_id are required")
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        bgm_path = f"static/bgm/{bgm_id}.mp3"
        if not os.path.exists(bgm_path):
            bgm_path = "static/bgm/sample.mp3"
        
        output_filename = f"bgm_{uuid.uuid4()}.mp4"
        output_path = os.path.join("static/uploaded_videos", output_filename)
        
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
        
        try:
            video = VideoFileClip(original_path)
            
            try:
                bgm = AudioFileClip(bgm_path)
                bgm = bgm.volumex(volume)
                
                if bgm.duration < video.duration:
                    bgm = bgm.loop(duration=video.duration)
                else:
                    bgm = bgm.subclip(0, video.duration)
                
                original_audio = video.audio
                new_audio = CompositeAudioClip([original_audio, bgm])
                video = video.set_audio(new_audio)
            except Exception as e:
                logger.warning(f"BGMの適用に失敗しました。元の音声のみで処理を続行します: {str(e)}")
            
            video.write_videofile(output_path, codec="libx264", audio_codec="aac")
            video.close()
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps({"type": "bgm", "video_id": video_id, "bgm_id": bgm_id, "volume": volume}),
                    original_path,
                    output_path
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "edit_id": edit_id,
                "processed_video_url": f"/uploaded_videos/{output_filename}",
                "bgm_id": bgm_id
            }
        except Exception as e:
            logger.error(f"BGM適用中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"BGM適用中にエラーが発生しました: {str(e)}")
    except Exception as e:
        logger.error(f"BGM適用APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/edit-range", response_model=dict)
async def edit_range(request: dict = Body(...)):
    """
    指定された範囲の動画を切り取るエンドポイント
    """
    try:
        video_id = request.get("video_id")
        start_time = request.get("start_time", 0)
        end_time = request.get("end_time", 0)
        
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        output_filename = f"range_edit_{uuid.uuid4()}.mp4"
        output_path = os.path.join("static/uploaded_videos", output_filename)
        
        os.makedirs("static/uploaded_videos", exist_ok=True)
        
        from moviepy.editor import VideoFileClip
        try:
            clip = VideoFileClip(original_path)
            if end_time > clip.duration:
                end_time = clip.duration
            
            edited_clip = clip.subclip(start_time, end_time)
            edited_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            clip.close()
            edited_clip.close()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edit_commands'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE edit_commands (
                        id INTEGER PRIMARY KEY,
                        command_json TEXT,
                        video_path TEXT,
                        result_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps({"type": "range_cut", "start_time": start_time, "end_time": end_time, "video_id": video_id}),
                    original_path,
                    output_path
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "edit_id": edit_id,
                "processed_video_url": f"/uploaded_videos/{output_filename}",
                "start_time": start_time,
                "end_time": end_time
            }
        except Exception as e:
            logger.error(f"動画編集中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"動画編集中にエラーが発生しました: {str(e)}")
    except Exception as e:
        logger.error(f"範囲編集APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}


@app.post("/api/generate-subtitles", response_model=dict)
async def generate_subtitles(request: dict = Body(...)):
    """動画にテロップを生成して適用するエンドポイント"""
    try:
        video_id = request.get("video_id")
        template_id = request.get("template_id", "default")
        
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        from subtitle_templates import get_template_by_id
        template = get_template_by_id(template_id)
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, original_path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        from moviepy.editor import VideoFileClip
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        
        try:
            video_clip = VideoFileClip(original_path)
            video_clip.audio.write_audiofile(temp_audio_path, logger=None)
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            with open(temp_audio_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
            
            transcript_text = transcript_response.text
            
            import re
            sentences = re.split(r'(?<=[。．！？])', transcript_text)
            sentences = [s for s in sentences if s.strip()]
            
            from moviepy.editor import TextClip, CompositeVideoClip
            
            output_filename = f"subtitle_{uuid.uuid4()}.mp4"
            output_path = os.path.join("static/uploaded_videos", output_filename)
            
            duration = video_clip.duration
            char_count = len(transcript_text)
            char_per_second = char_count / duration if duration > 0 else 10
            
            subtitle_clips = []
            
            current_time = 0
            for sentence in sentences:
                if not sentence.strip():
                    continue
                
                display_time = len(sentence) / char_per_second
                display_time = max(2, min(display_time, 5))  # 最小2秒、最大5秒
                
                txt_clip = TextClip(
                    sentence, 
                    fontsize=template["font_size"],
                    font=template["font"],
                    color=template["color"],
                    bg_color=template["bg_color"],
                    method='caption',
                    size=(video_clip.w * 0.9, None)
                )
                
                txt_clip = txt_clip.set_position(('center', 'bottom')).set_start(current_time).set_duration(display_time)
                subtitle_clips.append(txt_clip)
                
                current_time += display_time
            
            final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            video_clip.close()
            final_clip.close()
            
            command_data = {
                "type": "add_subtitles", 
                "template_id": template_id,
                "video_id": video_id
            }
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps(command_data),
                    original_path,
                    output_path
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "edit_id": edit_id,
                "processed_video_url": f"/uploaded_videos/{output_filename}",
                "transcript": transcript_text
            }
            
        except Exception as e:
            logger.error(f"テロップ生成中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            raise HTTPException(status_code=500, detail=f"テロップ生成中にエラーが発生しました: {str(e)}")
        
        finally:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                
    except Exception as e:
        logger.error(f"テロップ生成APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/suggest-bgm", response_model=dict)
async def suggest_bgm(request: dict = Body(...)):
    """動画内容を分析し、適切なBGMを提案するエンドポイント"""
    try:
        video_id = request.get("video_id")
        
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, original_path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
            
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        from moviepy.editor import VideoFileClip
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        
        try:
            video_clip = VideoFileClip(original_path)
            video_clip.audio.write_audiofile(temp_audio_path, logger=None)
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            with open(temp_audio_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
            
            transcript_text = transcript_response.text
            
            prompt = f"""
            以下は動画の文字起こしです。この内容に最適なBGMのジャンルを提案してください。
            
            文字起こし:
            {transcript_text}
            
            以下の形式でJSON形式で回答してください:
            {{
                "genre": "提案するBGMジャンル（例: アンビエント、ポップ、ロック、クラシック、ジャズなど）",
                "reason": "このジャンルを選んだ理由（100文字程度）",
                "mood": "動画の雰囲気（例: 明るい、落ち着いた、エネルギッシュ、感動的など）",
                "bgm_suggestions": [
                    {{
                        "title": "BGMタイトル1",
                        "description": "このBGMの特徴（50文字程度）",
                        "url": "サンプルURL（実際のURLは後で差し替えます）"
                    }},
                    // 3〜5曲の候補
                ]
            }}
            
            注意: 回答はJSON形式のみで、余計な説明は不要です。
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは動画内容を分析し、最適なBGMを提案する専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            bgm_suggestions = json.loads(response.choices[0].message.content)
            
            royalty_free_bgm = [
                {
                    "title": "Upbeat Corporate",
                    "description": "明るく前向きな企業向けBGM",
                    "url": "/static/bgm/upbeat_corporate.mp3",
                    "genre": "ポップ"
                },
                {
                    "title": "Inspiring Technology",
                    "description": "テクノロジーをテーマにした未来的なBGM",
                    "url": "/static/bgm/inspiring_technology.mp3",
                    "genre": "エレクトロニック"
                },
                {
                    "title": "Gentle Acoustic",
                    "description": "優しいアコースティックギターのBGM",
                    "url": "/static/bgm/gentle_acoustic.mp3",
                    "genre": "アコースティック"
                },
                {
                    "title": "Emotional Piano",
                    "description": "感動的なピアノソロのBGM",
                    "url": "/static/bgm/emotional_piano.mp3",
                    "genre": "クラシック"
                },
                {
                    "title": "Energetic Rock",
                    "description": "エネルギッシュなロックBGM",
                    "url": "/static/bgm/energetic_rock.mp3",
                    "genre": "ロック"
                },
                {
                    "title": "Relaxing Ambient",
                    "description": "リラックスできる環境音楽",
                    "url": "/static/bgm/relaxing_ambient.mp3",
                    "genre": "アンビエント"
                },
                {
                    "title": "Happy Ukulele",
                    "description": "明るいウクレレのBGM",
                    "url": "/static/bgm/happy_ukulele.mp3",
                    "genre": "ポップ"
                },
                {
                    "title": "Cinematic Orchestra",
                    "description": "映画音楽風の壮大なオーケストラ",
                    "url": "/static/bgm/cinematic_orchestra.mp3",
                    "genre": "オーケストラ"
                }
            ]
            
            suggested_genre = bgm_suggestions.get("genre", "").lower()
            matching_bgm = [bgm for bgm in royalty_free_bgm if suggested_genre in bgm["genre"].lower()]
            
            if len(matching_bgm) < 3:
                remaining_bgm = [bgm for bgm in royalty_free_bgm if bgm not in matching_bgm]
                matching_bgm.extend(remaining_bgm[:5-len(matching_bgm)])
            
            matching_bgm = matching_bgm[:5]
            
            command_data = {
                "type": "suggest_bgm",
                "video_id": video_id,
                "genre": bgm_suggestions.get("genre"),
                "mood": bgm_suggestions.get("mood")
            }
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps(command_data),
                    original_path,
                    ""  # BGM提案は結果パスなし
                )
            )
            conn.commit()
            suggestion_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "suggestion_id": suggestion_id,
                "genre": bgm_suggestions.get("genre"),
                "reason": bgm_suggestions.get("reason"),
                "mood": bgm_suggestions.get("mood"),
                "bgm_options": matching_bgm
            }
            
        except Exception as e:
            logger.error(f"BGM提案中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            raise HTTPException(status_code=500, detail=f"BGM提案中にエラーが発生しました: {str(e)}")
        
        finally:
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                
    except Exception as e:
        logger.error(f"BGM提案APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/apply-bgm", response_model=dict)
async def apply_bgm(request: dict = Body(...)):
    """選択されたBGMを動画に適用するエンドポイント"""
    try:
        video_id = request.get("video_id")
        bgm_url = request.get("bgm_url")
        volume = request.get("volume", 0.3)  # デフォルトボリューム30%
        
        if not video_id or not bgm_url:
            raise HTTPException(status_code=400, detail="video_id and bgm_url are required")
        
        volume = max(0.1, min(float(volume), 1.0))
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, original_path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
            
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        bgm_file_path = bgm_url.replace("/static/", "static/")
        if not os.path.exists(bgm_file_path):
            conn.close()
            raise HTTPException(status_code=404, detail="BGM file not found")
        
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
        
        output_filename = f"bgm_{uuid.uuid4()}.mp4"
        output_path = os.path.join("static/uploaded_videos", output_filename)
        
        try:
            video_clip = VideoFileClip(original_path)
            bgm_clip = AudioFileClip(bgm_file_path)
            
            if bgm_clip.duration < video_clip.duration:
                repeats = int(video_clip.duration / bgm_clip.duration) + 1
                bgm_extended = CompositeAudioClip([bgm_clip.set_start(i * bgm_clip.duration) for i in range(repeats)])
                bgm_clip = bgm_extended.subclip(0, video_clip.duration)
            else:
                bgm_clip = bgm_clip.subclip(0, video_clip.duration)
            
            bgm_clip = bgm_clip.volumex(volume)
            
            original_audio = video_clip.audio
            new_audio = CompositeAudioClip([original_audio, bgm_clip])
            
            video_with_bgm = video_clip.set_audio(new_audio)
            
            video_with_bgm.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            video_clip.close()
            video_with_bgm.close()
            
            command_data = {
                "type": "apply_bgm",
                "video_id": video_id,
                "bgm_url": bgm_url,
                "volume": volume
            }
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps(command_data),
                    original_path,
                    output_path
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "edit_id": edit_id,
                "processed_video_url": f"/uploaded_videos/{output_filename}"
            }
            
        except Exception as e:
            logger.error(f"BGM適用中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"BGM適用中にエラーが発生しました: {str(e)}")
                
    except Exception as e:
        logger.error(f"BGM適用APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/edit-range", response_model=dict)
async def edit_range(request: dict = Body(...)):
    """指定された範囲の動画を切り取るエンドポイント"""
    try:
        video_id = request.get("video_id")
        start_time = request.get("start_time", 0)
        end_time = request.get("end_time", 0)
        
        if not video_id:
            raise HTTPException(status_code=400, detail="video_id is required")
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filename, original_path FROM uploads WHERE id = ?",
            (video_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Video not found")
        
        filename, original_path = result
        
        if not os.path.exists(original_path):
            conn.close()
            raise HTTPException(status_code=404, detail="Video file not found")
        
        output_filename = f"range_edit_{uuid.uuid4()}.mp4"
        output_path = os.path.join("static/uploaded_videos", output_filename)
        
        from moviepy.editor import VideoFileClip
        try:
            clip = VideoFileClip(original_path)
            if end_time > clip.duration:
                end_time = clip.duration
            
            edited_clip = clip.subclip(start_time, end_time)
            edited_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            clip.close()
            edited_clip.close()
            
            command_data = {
                "type": "range_cut", 
                "start_time": start_time, 
                "end_time": end_time, 
                "video_id": video_id
            }
            
            cursor.execute(
                "INSERT INTO edit_commands (command_json, video_path, result_path) VALUES (?, ?, ?)",
                (
                    json.dumps(command_data),
                    original_path,
                    output_path
                )
            )
            conn.commit()
            edit_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "edit_id": edit_id,
                "processed_video_url": f"/uploaded_videos/{output_filename}",
                "start_time": start_time,
                "end_time": end_time
            }
        except Exception as e:
            logger.error(f"動画編集中にエラーが発生しました: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"動画編集中にエラーが発生しました: {str(e)}")
    except Exception as e:
        logger.error(f"範囲編集APIエラー: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get-processed-videos", response_model=List[dict])
async def get_processed_videos():
    """処理済み動画のリストを取得するエンドポイント（WebUI用）"""
    try:
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        upload_dir = "uploaded_videos"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edit_commands'")
        if not cursor.fetchone():
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS edit_commands (
                id INTEGER PRIMARY KEY,
                client_id TEXT,
                script_id TEXT,
                command_json TEXT,
                video_path TEXT,
                result_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
        
        cursor.execute("SELECT id, video_path, result_path, created_at FROM edit_commands ORDER BY created_at DESC")
        edit_history = cursor.fetchall()
        
        uploaded_videos = []
        for filename in os.listdir(upload_dir):
            if filename.endswith(('.mp4', '.mov', '.avi', '.webm')):
                file_path = os.path.join(upload_dir, filename)
                uploaded_videos.append({
                    "id": f"upload_{filename}",
                    "name": filename,
                    "path": file_path,
                    "type": "uploaded",
                    "created_at": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                })
        
        processed_videos = []
        for filename in os.listdir(output_dir):
            if filename.endswith(('.mp4', '.mov', '.avi', '.webm')):
                file_path = os.path.join(output_dir, filename)
                processed_videos.append({
                    "id": f"output_{filename}",
                    "name": filename,
                    "path": file_path,
                    "type": "processed",
                    "created_at": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                })
        
        history_videos = []
        for record in edit_history:
            id, video_path, result_path, created_at = record
            if os.path.exists(result_path):
                history_videos.append({
                    "id": f"history_{id}",
                    "name": os.path.basename(result_path),
                    "path": result_path,
                    "original_path": video_path,
                    "type": "edited",
                    "created_at": created_at
                })
        
        all_videos = uploaded_videos + processed_videos + history_videos
        
        all_videos.sort(key=lambda x: x["created_at"], reverse=True)
        
        conn.close()
        return all_videos
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"動画リストの取得に失敗しました: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
