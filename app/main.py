from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_enhancement import research_detailed_success_case, store_success_case, collect_copyright_free_audio, store_audio_tracks, init_db as init_enhanced_db
from competitor_analysis import get_youtube_transcript, analyze_competitor_script, store_competitor_script
from video_processing import process_video

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not found in environment variables")

os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="SNS AI Agent Web Prototype")

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    print("Initializing enhanced database tables...")
    init_enhanced_db()
    print("Enhanced database tables initialized successfully.")

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "user"
    correct_password = "f047be9dc32d4a76824fcbf63823398d"
    
    is_username_correct = secrets.compare_digest(credentials.username, correct_username)
    is_password_correct = secrets.compare_digest(credentials.password, correct_password)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")
        
        if not auth_header.startswith("Basic "):
            return await self.handle_unauthorized(scope, receive, send)
        
        try:
            auth_data = auth_header.replace("Basic ", "")
            decoded = base64.b64decode(auth_data).decode("utf-8")
            username, password = decoded.split(":")
            
            if username != "user" or password != "f047be9dc32d4a76824fcbf63823398d":
                return await self.handle_unauthorized(scope, receive, send)
                
        except Exception:
            return await self.handle_unauthorized(scope, receive, send)
        
        return await self.app(scope, receive, send)
    
    async def handle_unauthorized(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"www-authenticate", b"Basic realm=SNS AI Agent"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"Unauthorized",
        })

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "user"
    correct_password = "f047be9dc32d4a76824fcbf63823398d"
    
    is_username_correct = secrets.compare_digest(credentials.username, correct_username)
    is_password_correct = secrets.compare_digest(credentials.password, correct_password)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

def get_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.db"))
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
    
    target_attributes = selection["target_attributes"].split(",")
    operational_purposes = selection["operational_purposes"].split(",")
    platforms = selection["platforms"].split(",")
    
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
        アカウント名: {profile['account_name']}
        プロフィール: {profile['profile_text']}
        """
    
    if competitor_data:
        keywords = json.loads(competitor_data["keywords"]) if isinstance(competitor_data["keywords"], str) else competitor_data["keywords"]
        empathy_points = json.loads(competitor_data["empathy_points"]) if isinstance(competitor_data["empathy_points"], str) else competitor_data["empathy_points"]
        hook = competitor_data["hook"]
        
        prompt += f"""
        【必須事項】:
        - 冒頭フック: 「{hook}」を基にリライト
        - キーワード: 「{', '.join(keywords[:3])}」を含める
        - 共感ポイント: 「{', '.join(empathy_points[:2])}」を活用する
        """
    
    if success_case:
        trend_topics = json.loads(success_case["trend_topics"]) if isinstance(success_case["trend_topics"], str) else success_case["trend_topics"]
        buzz_point = success_case["buzz_point"].split(" - ")[1] if " - " in success_case["buzz_point"] else success_case["buzz_point"]
        
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
async def root(username: str = Depends(verify_credentials)):
    """ルートエンドポイント - 静的ファイルにリダイレクト"""
    return RedirectResponse(url="/static/index.html")

@app.post("/collect_success_cases/", response_model=dict)
async def collect_success_cases(
    platform: str = Form(...),
    industry: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    """指定したプラットフォームと業界の成功動画を収集し、DBに格納するエンドポイント"""
    try:
        success_case = research_detailed_success_case(platform, industry)
        
        case_id = store_success_case(platform, industry, success_case)
        
        return {
            "success": True,
            "id": case_id,
            "platform": platform,
            "industry": industry,
            "video_url": success_case["video_url"],
            "buzz_point": success_case["buzz_point"],
            "top_comments": success_case["top_comments"],
            "trend_topics": success_case["trend_topics"],
            "engagement_reason": success_case["engagement_reason"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"成功事例の収集中にエラーが発生しました: {str(e)}")

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
    conn: sqlite3.Connection = Depends(get_db)
):
    """動画をアップロードし、アスペクト比とマージン設定を保存するエンドポイント"""
    try:
        os.makedirs("uploaded_videos", exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("uploaded_videos", unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO uploads (filename, original_filename, aspect_ratio, margin_seconds, client_id) VALUES (?, ?, ?, ?, ?)",
            (unique_filename, file.filename, aspect_ratio, margin_seconds, client_id)
        )
        conn.commit()
        upload_id = cursor.lastrowid
        
        return {
            "success": True,
            "id": upload_id,
            "filename": unique_filename,
            "original_filename": file.filename,
            "aspect_ratio": aspect_ratio,
            "margin_seconds": margin_seconds,
            "client_id": client_id,
            "file_path": file_path
        }
    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
