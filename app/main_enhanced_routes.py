
from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile, Form, Security, status
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
import os
import sqlite3
import uuid
import json
from typing import List, Optional
import openai
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_enhancement import research_detailed_success_case, store_success_case, collect_trend_topics
from script_analysis import analyze_client_transcripts, get_transcript_analysis
from video_processing import process_video

DB_PATH = "app.db"

def generate_data_driven_script(client_id):
    """Generate a script based on database success cases and transcript analysis."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT c.id, c.name, c.email, s.target_attributes, s.operational_purposes, s.platforms
    FROM clients c
    LEFT JOIN selections s ON c.id = s.client_id
    WHERE c.id = ?
    ''', (client_id,))
    
    client_data = cursor.fetchone()
    if not client_data:
        conn.close()
        return {"error": "Client not found"}
    
    client_id, client_name, client_email, target_attributes, operational_purposes, platforms = client_data
    
    target_attributes = json.loads(target_attributes) if target_attributes else []
    operational_purposes = json.loads(operational_purposes) if operational_purposes else []
    platforms = json.loads(platforms) if platforms else []
    
    platform = platforms[0] if platforms else "YouTube"
    cursor.execute('''
    SELECT buzz_point, top_comments, trend_topics, engagement_reason
    FROM detailed_success_cases
    WHERE platform = ?
    ORDER BY RANDOM()
    LIMIT 1
    ''', (platform,))
    
    success_case = cursor.fetchone()
    
    if not success_case:
        mock_case = research_detailed_success_case(platform, "一般")
        buzz_point = mock_case["buzz_point"]
        top_comments = json.dumps(mock_case["top_comments"])
        trend_topics = json.dumps(mock_case["trend_topics"])
        engagement_reason = mock_case["engagement_reason"]
    else:
        buzz_point, top_comments, trend_topics, engagement_reason = success_case
    
    try:
        top_comments = json.loads(top_comments)
        if isinstance(top_comments, list) and top_comments:
            top_comment = top_comments[0]
        else:
            top_comment = "素晴らしい内容でした！"
    except:
        top_comment = "素晴らしい内容でした！"
    
    try:
        trend_topics = json.loads(trend_topics)
        if isinstance(trend_topics, list) and trend_topics:
            trend_topic = trend_topics[0]
        else:
            trend_topic = "最新トレンド"
    except:
        trend_topic = "最新トレンド"
    
    buzz_content = buzz_point.split(" - ")[1] if " - " in buzz_point else buzz_point
    
    transcript_analysis = get_transcript_analysis(client_id)
    
    transcript_keywords = transcript_analysis.get("keywords", [])
    engaging_phrases = transcript_analysis.get("engaging_phrases", [])
    
    try:
        if openai.api_key == "your_api_key_here":
            script = f"""

こんにちは、皆さん！今日は{buzz_content}についてお話しします。これから紹介する内容は、あなたの{', '.join(operational_purposes) if operational_purposes else '情報収集'}に役立つ情報満載です。{', '.join(target_attributes) if target_attributes else '一般視聴者'}の皆さんに特におすすめの内容となっています。

多くの方が「{top_comment}」と感じていると思います。実は、この課題は{', '.join(transcript_keywords[:3]) if transcript_keywords else 'さまざまな要素'}と深く関係しています。今日はその解決策を詳しく解説します。

まず最初に試していただきたいのは、〇〇です。これを実践することで、△△の効果が期待できます。具体的な手順は次の通りです...

ところで、最近の{trend_topic}についてご存知ですか？このトレンドを活用することで、さらに効果的に問題を解決できます。

今日お伝えした{buzz_content}の方法とトレンドの{trend_topic}を組み合わせることで、最大の効果が得られます。ぜひ試してみて、結果をコメント欄で教えてください！チャンネル登録もお忘れなく！
"""
            return script
            
        keywords_text = ", ".join(transcript_keywords[:3]) if transcript_keywords else ""
        engaging_text = ", ".join(engaging_phrases[:2]) if engaging_phrases else ""
        
        target_text = ", ".join(target_attributes) if target_attributes else "一般視聴者"
        purpose_text = ", ".join(operational_purposes) if operational_purposes else "情報提供"
        
        prompt = f"""
        あなたは{platform}クリエイターのための台本作成の専門家です。
        以下の要素を必ず含めた台本を作成してください：
        
        1. 冒頭で必ず「{buzz_content}」というフレーズまたは内容を使う
        2. 中盤以降に「{trend_topic}」をテーマとして含める
        3. 視聴者からの「{top_comment}」のようなコメントを引き出せる内容にする
        
        ターゲット層: {target_text}
        目的: {purpose_text}
        プラットフォーム: {platform}
        
        {f'以下のキーワードを台本内に含めてください: {keywords_text}' if keywords_text else ''}
        {f'以下の共感フレーズを参考にしてください: {engaging_text}' if engaging_text else ''}
        
        台本は5つのセクションに分け、各セクションは100-150文字程度にしてください。
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        script = response.choices[0].message.content
        
        return script
        
    except Exception as e:
        print(f"Error generating script: {str(e)}")
        script = f"""

こんにちは、皆さん！今日は{buzz_content}についてお話しします。これから紹介する内容は、あなたの{', '.join(operational_purposes) if operational_purposes else '情報収集'}に役立つ情報満載です。{', '.join(target_attributes) if target_attributes else '一般視聴者'}の皆さんに特におすすめの内容となっています。

多くの方が「{top_comment}」と感じていると思います。実は、この課題は{', '.join(transcript_keywords[:3]) if transcript_keywords else 'さまざまな要素'}と深く関係しています。今日はその解決策を詳しく解説します。

まず最初に試していただきたいのは、〇〇です。これを実践することで、△△の効果が期待できます。具体的な手順は次の通りです...

ところで、最近の{trend_topic}についてご存知ですか？このトレンドを活用することで、さらに効果的に問題を解決できます。

今日お伝えした{buzz_content}の方法とトレンドの{trend_topic}を組み合わせることで、最大の効果が得られます。ぜひ試してみて、結果をコメント欄で教えてください！チャンネル登録もお忘れなく！
"""
        return script

def setup_routes(app):
    """Set up API routes for the application."""
    
    @app.post("/generate-profile/")
    async def generate_profile(client_id: str = Form(...)):
        """Generate a profile for a client."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT c.name, c.email, s.target_attributes, s.operational_purposes, s.platforms
        FROM clients c
        LEFT JOIN selections s ON c.id = s.client_id
        WHERE c.id = ?
        ''', (client_id,))
        
        client_data = cursor.fetchone()
        if not client_data:
            conn.close()
            raise HTTPException(status_code=404, detail="Client not found")
        
        client_name, client_email, target_attributes, operational_purposes, platforms = client_data
        
        target_attributes = json.loads(target_attributes) if target_attributes else []
        operational_purposes = json.loads(operational_purposes) if operational_purposes else []
        platforms = json.loads(platforms) if platforms else []
        
        transcript_analysis = get_transcript_analysis(client_id)
        
        try:
            if openai.api_key == "your_api_key_here":
                account_name = f"{'、'.join(target_attributes[:2]) if len(target_attributes) >= 2 else '一般'}のアカウント"
                profile_text = f"""こんにちは！{'、'.join(target_attributes) if target_attributes else '一般的な'}のYouTubeユーザーです。
                {'、'.join(operational_purposes) if operational_purposes else 'コンテンツ発信'}を目的としたコンテンツを発信しています。
                旅行、料理、音楽が大好きで、日常の発見や体験を共有しています。
                フォローしていただけると嬉しいです！"""
            else:
                platform = platforms[0] if platforms else "YouTube"
                cursor.execute('''
                SELECT account_name, profile_text
                FROM detailed_success_cases
                WHERE platform = ?
                ORDER BY RANDOM()
                LIMIT 1
                ''', (platform,))
                
                success_case = cursor.fetchone()
                
                target_text = ", ".join(target_attributes) if target_attributes else "一般視聴者"
                purpose_text = ", ".join(operational_purposes) if operational_purposes else "情報提供"
                platform_text = ", ".join(platforms) if platforms else "YouTube"
                
                keywords = transcript_analysis.get("keywords", [])
                keywords_text = ", ".join(keywords[:5]) if keywords else ""
                
                prompt = f"""
                あなたは{platform_text}のプロフィール作成の専門家です。
                以下の条件に合ったアカウント名とプロフィール文を作成してください：
                
                ターゲット層: {target_text}
                目的: {purpose_text}
                プラットフォーム: {platform_text}
                
                {f'以下のキーワードを含めてください: {keywords_text}' if keywords_text else ''}
                
                アカウント名は20文字以内、プロフィール文は150文字以内で作成してください。
                
                以下のJSON形式で出力してください：
                {{
                    "account_name": "アカウント名",
                    "profile_text": "プロフィール文"
                }}
                """
                
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500
                )
                
                result = response.choices[0].message.content
                
                try:
                    profile_data = json.loads(result)
                    account_name = profile_data["account_name"]
                    profile_text = profile_data["profile_text"]
                except:
                    account_name = f"{'、'.join(target_attributes[:2]) if len(target_attributes) >= 2 else '一般'}のアカウント"
                    profile_text = f"""こんにちは！{'、'.join(target_attributes) if target_attributes else '一般的な'}の{platform_text}ユーザーです。
                    {'、'.join(operational_purposes) if operational_purposes else 'コンテンツ発信'}を目的としたコンテンツを発信しています。
                    旅行、料理、音楽が大好きで、日常の発見や体験を共有しています。
                    フォローしていただけると嬉しいです！"""
        
        except Exception as e:
            print(f"Error generating profile: {str(e)}")
            account_name = f"{'、'.join(target_attributes[:2]) if len(target_attributes) >= 2 else '一般'}のアカウント"
            profile_text = f"""こんにちは！{'、'.join(target_attributes) if target_attributes else '一般的な'}の{platforms[0] if platforms else 'YouTube'}ユーザーです。
            {'、'.join(operational_purposes) if operational_purposes else 'コンテンツ発信'}を目的としたコンテンツを発信しています。
            旅行、料理、音楽が大好きで、日常の発見や体験を共有しています。
            フォローしていただけると嬉しいです！"""
        
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
    
    @app.post("/generate-script/")
    async def generate_script(client_id: str = Form(...)):
        """Generate a script for a client."""
        script_text = generate_data_driven_script(client_id)
        
        script_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
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
    
    @app.get("/profiles/{client_id}")
    async def get_profiles(client_id: str):
        """Get all profiles for a client."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, account_name, profile_text, selected FROM profiles WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,)
        )
        
        profiles = cursor.fetchall()
        conn.close()
        
        result = []
        for profile in profiles:
            profile_id, account_name, profile_text, selected = profile
            result.append({
                "id": profile_id,
                "account_name": account_name,
                "profile_text": profile_text,
                "selected": selected == 1
            })
        
        return result
    
    @app.get("/scripts/{client_id}")
    async def get_scripts(client_id: str):
        """Get all scripts for a client."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, script_text, selected FROM scripts WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,)
        )
        
        scripts = cursor.fetchall()
        conn.close()
        
        result = []
        for script in scripts:
            script_id, script_text, selected = script
            result.append({
                "id": script_id,
                "script_text": script_text,
                "selected": selected == 1
            })
        
        return result
    
    @app.post("/profiles/{profile_id}/select")
    async def select_profile(profile_id: str):
        """Select a profile."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT client_id FROM profiles WHERE id = ?", (profile_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Profile not found")
        
        client_id = result[0]
        
        cursor.execute("UPDATE profiles SET selected = 0 WHERE client_id = ?", (client_id,))
        
        cursor.execute("UPDATE profiles SET selected = 1 WHERE id = ?", (profile_id,))
        
        conn.commit()
        conn.close()
        
        return {"message": "Profile selected successfully"}
    
    @app.post("/scripts/{script_id}/select")
    async def select_script(script_id: str):
        """Select a script."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT client_id FROM scripts WHERE id = ?", (script_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Script not found")
        
        client_id = result[0]
        
        cursor.execute("UPDATE scripts SET selected = 0 WHERE client_id = ?", (client_id,))
        
        cursor.execute("UPDATE scripts SET selected = 1 WHERE id = ?", (script_id,))
        
        conn.commit()
        conn.close()
        
        return {"message": "Script selected successfully"}
    
    @app.put("/profiles/{profile_id}")
    async def update_profile(profile_id: str, profile: dict):
        """Update a profile."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE profiles SET account_name = ?, profile_text = ? WHERE id = ?",
            (profile["account_name"], profile["profile_text"], profile_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Profile not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Profile updated successfully"}
    
    @app.put("/scripts/{script_id}")
    async def update_script(script_id: str, script: dict):
        """Update a script."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE scripts SET script_text = ? WHERE id = ?",
            (script["script_text"], script_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Script not found")
        
        conn.commit()
        conn.close()
        
        return {"message": "Script updated successfully"}
    
    @app.get("/success-cases/{platform}")
    async def get_success_cases(platform: str):
        """Get success cases for a platform."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, platform, industry, video_url, buzz_point, top_comments, trend_topics, engagement_reason FROM detailed_success_cases WHERE platform = ?",
            (platform,)
        )
        
        cases = cursor.fetchall()
        conn.close()
        
        result = []
        for case in cases:
            case_id, platform, industry, video_url, buzz_point, top_comments, trend_topics, engagement_reason = case
            
            try:
                top_comments = json.loads(top_comments)
            except:
                top_comments = []
            
            try:
                trend_topics = json.loads(trend_topics)
            except:
                trend_topics = []
            
            result.append({
                "id": case_id,
                "platform": platform,
                "industry": industry,
                "video_url": video_url,
                "buzz_point": buzz_point,
                "top_comments": top_comments,
                "trend_topics": trend_topics,
                "engagement_reason": engagement_reason
            })
        
        return result
    
    @app.get("/copyright-free-audio/")
    async def get_copyright_free_audio(genre: Optional[str] = None, mood: Optional[str] = None):
        """Get copyright-free audio tracks."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT id, title, artist, genre, mood, duration, file_path, source FROM copyright_free_audio"
        params = []
        
        if genre or mood:
            query += " WHERE"
            
            if genre:
                query += " genre = ?"
                params.append(genre)
                
                if mood:
                    query += " AND mood = ?"
                    params.append(mood)
            elif mood:
                query += " mood = ?"
                params.append(mood)
        
        cursor.execute(query, params)
        
        tracks = cursor.fetchall()
        conn.close()
        
        result = []
        for track in tracks:
            track_id, title, artist, genre, mood, duration, file_path, source = track
            result.append({
                "id": track_id,
                "title": title,
                "artist": artist,
                "genre": genre,
                "mood": mood,
                "duration": duration,
                "file_path": file_path,
                "source": source
            })
        
        return result
    
    @app.get("/audio-genres/")
    async def get_audio_genres():
        """Get available audio genres."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT genre FROM copyright_free_audio")
        
        genres = cursor.fetchall()
        conn.close()
        
        return [genre[0] for genre in genres if genre[0]]
    
    @app.get("/audio-moods/")
    async def get_audio_moods():
        """Get available audio moods."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT mood FROM copyright_free_audio")
        
        moods = cursor.fetchall()
        conn.close()
        
        return [mood[0] for mood in moods if mood[0]]
    
    @app.get("/audio-file/{track_id}")
    async def get_audio_file(track_id: int):
        """Get audio file for a track."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT file_path FROM copyright_free_audio WHERE id = ?", (track_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        file_path = result[0]
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(file_path)
    
    @app.post("/process-video/")
    async def process_video_endpoint(
        client_id: str = Form(...),
        file_id: str = Form(...),
        aspect_ratio: str = Form("16:9"),
        silence_threshold: float = Form(0.02),
        min_clip_duration: float = Form(0.5),
        start_margin: float = Form(0.0),
        end_margin: float = Form(0.0)
    ):
        """Process a video with jet cut and aspect ratio conversion."""
        if aspect_ratio not in ["16:9", "1:1", "9:16"]:
            raise HTTPException(status_code=400, detail="Invalid aspect ratio. Must be one of: 16:9, 1:1, 9:16")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT file_path, file_type FROM uploaded_files WHERE id = ? AND client_id = ?",
            (file_id, client_id)
        )
        
        file_info = cursor.fetchone()
        if not file_info:
            conn.close()
            raise HTTPException(status_code=404, detail="File not found or does not belong to this client")
        
        file_path, file_type = file_info
        
        if file_type != "video":
            conn.close()
            raise HTTPException(status_code=400, detail="File is not a video")
        
        try:
            result = process_video(
                input_path=file_path,
                aspect_ratio=aspect_ratio,
                silence_threshold=silence_threshold,
                min_clip_duration=min_clip_duration,
                start_margin=start_margin,
                end_margin=end_margin
            )
            
            edit_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO video_edits 
            (id, client_id, file_id, aspect_ratio, trim_start, trim_end, start_margin, end_margin, output_quality, output_format)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                edit_id,
                client_id,
                file_id,
                aspect_ratio,
                0.0,  # trim_start (not used in jet cut)
                0.0,  # trim_end (not used in jet cut)
                start_margin,
                end_margin,
                "high",  # output_quality
                "mp4"  # output_format
            ))
            
            conn.commit()
            
            result["edit_id"] = edit_id
            
            if "silent_segments" in result and isinstance(result["silent_segments"], list):
                result["silent_segments"] = [
                    {"start": segment["start"], "end": segment["end"]} 
                    for segment in result["silent_segments"]
                ]
            
            conn.close()
            return result
            
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
