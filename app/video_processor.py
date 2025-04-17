"""
video_processor.py - 動画処理モジュール

アップロードされた動画の自動処理（ジェットカット、字幕生成）を行います。
"""

import os
import json
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
import numpy as np
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data.db"

def detect_silence(audio_array, sample_rate, min_silence_duration=0.5, silence_threshold=0.01):
    """
    音声データから無音部分を検出
    
    Args:
        audio_array: 音声データの配列
        sample_rate: サンプルレート
        min_silence_duration: 最小無音期間（秒）
        silence_threshold: 無音と判定する閾値
        
    Returns:
        list: 無音部分の開始・終了時間のリスト [(start1, end1), (start2, end2), ...]
    """
    volume = np.abs(audio_array)
    
    is_silence = volume < silence_threshold
    
    silence_periods = []
    silence_start = None
    
    for i, silent in enumerate(is_silence):
        time = i / sample_rate
        
        if silent and silence_start is None:
            silence_start = time
        elif not silent and silence_start is not None:
            silence_duration = time - silence_start
            if silence_duration >= min_silence_duration:
                silence_periods.append((silence_start, time))
            silence_start = None
    
    if silence_start is not None:
        time = len(is_silence) / sample_rate
        silence_duration = time - silence_start
        if silence_duration >= min_silence_duration:
            silence_periods.append((silence_start, time))
    
    return silence_periods

def jet_cut_video(input_path, output_path, min_silence_duration=0.5, silence_threshold=0.01):
    """
    動画のジェットカット処理（無音部分の削除）
    
    Args:
        input_path: 入力動画のパス
        output_path: 出力動画のパス
        min_silence_duration: 最小無音期間（秒）
        silence_threshold: 無音と判定する閾値
        
    Returns:
        dict: 処理結果の情報
    """
    try:
        video = VideoFileClip(input_path)
        
        audio = video.audio
        if audio is None:
            return {"success": False, "error": "音声データがありません"}
        
        audio_array = audio.to_soundarray()
        if len(audio_array.shape) > 1:
            audio_array = audio_array.mean(axis=1)  # ステレオの場合はモノラルに変換
        
        silence_periods = detect_silence(
            audio_array, 
            audio.fps, 
            min_silence_duration, 
            silence_threshold
        )
        
        if not silence_periods:
            video.write_videofile(output_path, codec="libx264", audio_codec="aac")
            return {
                "success": True, 
                "original_duration": video.duration,
                "processed_duration": video.duration,
                "cut_count": 0,
                "silence_periods": []
            }
        
        keep_periods = []
        video_start = 0
        
        for silence_start, silence_end in silence_periods:
            if silence_start > video_start:
                keep_periods.append((video_start, silence_start))
            video_start = silence_end
        
        if video_start < video.duration:
            keep_periods.append((video_start, video.duration))
        
        clips = [video.subclip(start, end) for start, end in keep_periods]
        final_clip = clips[0]
        
        for clip in clips[1:]:
            final_clip = final_clip.append_clip(clip)
        
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        processed_duration = sum(end - start for start, end in keep_periods)
        
        result = {
            "success": True,
            "original_duration": video.duration,
            "processed_duration": processed_duration,
            "cut_count": len(silence_periods),
            "silence_periods": silence_periods
        }
        
        video.close()
        final_clip.close()
        
        return result
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def transcribe_video(video_path):
    """
    動画の文字起こし
    
    Args:
        video_path: 動画のパス
        
    Returns:
        dict: 文字起こし結果
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            audio_path = temp_audio.name
        
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        
        os.remove(audio_path)
        
        return {
            "success": True,
            "text": transcript.text,
            "segments": transcript.segments
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_subtitles(transcript, style="default"):
    """
    文字起こしからテロップを生成
    
    Args:
        transcript: 文字起こし結果
        style: テロップのスタイル
        
    Returns:
        list: テロップのリスト
    """
    try:
        segments = transcript.get("segments", [])
        
        if not segments:
            return {"success": False, "error": "文字起こしセグメントがありません"}
        
        prompt = f"""
        以下の文字起こしセグメントを、Instagram動画用のテロップに最適化してください。
        各セグメントに対して、以下の情報を含む最適化されたテロップを提案してください：
        
        1. 元のテキスト
        2. 最適化されたテロップテキスト（簡潔で視覚的に効果的なもの）
        3. 強調すべき単語やフレーズ
        
        セグメント：
        {json.dumps(segments, ensure_ascii=False, indent=2)}
        
        各セグメントに対して、以下の形式でJSON配列として回答してください：
        [
          {{
            "start": 開始時間（秒）,
            "end": 終了時間（秒）,
            "original_text": "元のテキスト",
            "subtitle_text": "最適化されたテロップテキスト",
            "emphasis": ["強調1", "強調2"]
          }},
          ...
        ]
        
        テロップは簡潔で、視聴者の注意を引くものにしてください。
        長いセグメントは複数のテロップに分割してください。
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたはSNS動画のテロップ最適化の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        subtitles_json = response.choices[0].message.content
        subtitles = json.loads(subtitles_json)
        
        styles = {
            "default": {
                "font": "Arial",
                "fontsize": 24,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 1
            },
            "bold": {
                "font": "Arial-Bold",
                "fontsize": 28,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 1.5
            },
            "highlight": {
                "font": "Arial",
                "fontsize": 24,
                "color": "yellow",
                "stroke_color": "black",
                "stroke_width": 1
            }
        }
        
        for subtitle in subtitles:
            subtitle["style"] = styles.get(style, styles["default"])
        
        return {"success": True, "subtitles": subtitles}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_subtitles_to_video(input_path, output_path, subtitles):
    """
    動画にテロップを追加
    
    Args:
        input_path: 入力動画のパス
        output_path: 出力動画のパス
        subtitles: テロップのリスト
        
    Returns:
        dict: 処理結果
    """
    try:
        video = VideoFileClip(input_path)
        
        subtitle_clips = []
        
        for subtitle in subtitles:
            start = subtitle["start"]
            end = subtitle["end"]
            text = subtitle["subtitle_text"]
            style = subtitle["style"]
            
            text_clip = TextClip(
                text,
                font=style["font"],
                fontsize=style["fontsize"],
                color=style["color"],
                stroke_color=style["stroke_color"],
                stroke_width=style["stroke_width"],
                method="caption",
                size=(video.w * 0.8, None),
                align="center"
            )
            
            text_clip = text_clip.set_position(("center", "bottom")).set_start(start).set_end(end)
            subtitle_clips.append(text_clip)
        
        final_clip = CompositeVideoClip([video] + subtitle_clips)
        
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        video.close()
        final_clip.close()
        
        return {"success": True}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def process_video(video_path, output_dir, client_id=None, jet_cut=True, add_subtitles=True):
    """
    動画の一連の処理（ジェットカット、字幕生成）
    
    Args:
        video_path: 入力動画のパス
        output_dir: 出力ディレクトリ
        client_id: クライアントID
        jet_cut: ジェットカットを行うかどうか
        add_subtitles: 字幕を追加するかどうか
        
    Returns:
        dict: 処理結果
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        video_filename = os.path.basename(video_path)
        base_name = os.path.splitext(video_filename)[0]
        
        jet_cut_result = None
        jet_cut_path = None
        
        if jet_cut:
            jet_cut_path = os.path.join(output_dir, f"{base_name}_jetcut.mp4")
            jet_cut_result = jet_cut_video(video_path, jet_cut_path)
            
            if not jet_cut_result["success"]:
                return jet_cut_result
        
        subtitle_result = None
        final_path = None
        
        if add_subtitles:
            source_path = jet_cut_path if jet_cut and jet_cut_path else video_path
            transcript_result = transcribe_video(source_path)
            
            if not transcript_result["success"]:
                return transcript_result
            
            subtitle_result = generate_subtitles(transcript_result)
            
            if not subtitle_result["success"]:
                return subtitle_result
            
            final_path = os.path.join(output_dir, f"{base_name}_final.mp4")
            add_result = add_subtitles_to_video(source_path, final_path, subtitle_result["subtitles"])
            
            if not add_result["success"]:
                return add_result
        else:
            final_path = jet_cut_path if jet_cut and jet_cut_path else video_path
        
        if client_id:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
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
            
            original_duration = jet_cut_result["original_duration"] if jet_cut_result else None
            processed_duration = jet_cut_result["processed_duration"] if jet_cut_result else None
            cut_count = jet_cut_result["cut_count"] if jet_cut_result else 0
            
            cursor.execute(
                """
                INSERT INTO processed_videos 
                (client_id, original_path, processed_path, jet_cut_applied, subtitles_added, 
                original_duration, processed_duration, cut_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id, 
                    video_path, 
                    final_path, 
                    jet_cut, 
                    add_subtitles,
                    original_duration,
                    processed_duration,
                    cut_count
                )
            )
            
            video_id = cursor.lastrowid
            
            if subtitle_result and subtitle_result.get("subtitles"):
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_subtitles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    subtitles TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES processed_videos (id)
                )
                ''')
                
                cursor.execute(
                    "INSERT INTO video_subtitles (video_id, subtitles) VALUES (?, ?)",
                    (video_id, json.dumps(subtitle_result["subtitles"], ensure_ascii=False))
                )
            
            conn.commit()
            conn.close()
        
        return {
            "success": True,
            "original_path": video_path,
            "processed_path": final_path,
            "jet_cut_result": jet_cut_result,
            "subtitle_result": subtitle_result
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_processed_videos(client_id=None):
    """
    処理済み動画の取得
    
    Args:
        client_id: クライアントID（指定しない場合は全ての動画）
        
    Returns:
        list: 処理済み動画のリスト
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if client_id:
        cursor.execute(
            "SELECT * FROM processed_videos WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,)
        )
    else:
        cursor.execute("SELECT * FROM processed_videos ORDER BY created_at DESC")
    
    videos = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return videos

def get_video_subtitles(video_id):
    """
    動画の字幕データの取得
    
    Args:
        video_id: 動画ID
        
    Returns:
        list: 字幕データ
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT subtitles FROM video_subtitles WHERE video_id = ?", (video_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if not result:
        return []
    
    try:
        return json.loads(result["subtitles"])
    except:
        return []

def update_video_subtitles(video_id, subtitles):
    """
    動画の字幕データの更新
    
    Args:
        video_id: 動画ID
        subtitles: 更新する字幕データ
        
    Returns:
        bool: 更新成功かどうか
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE video_subtitles SET subtitles = ? WHERE video_id = ?",
        (json.dumps(subtitles, ensure_ascii=False), video_id)
    )
    
    success = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return success

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        input_path = sys.argv[1]
        output_dir = sys.argv[2]
        
        result = process_video(input_path, output_dir)
        
        if result["success"]:
            print(f"動画処理が完了しました: {result['processed_path']}")
            
            if result.get("jet_cut_result"):
                jc = result["jet_cut_result"]
                print(f"元の長さ: {jc['original_duration']:.1f}秒")
                print(f"処理後の長さ: {jc['processed_duration']:.1f}秒")
                print(f"カット数: {jc['cut_count']}")
        else:
            print(f"エラー: {result['error']}")
    else:
        print("使用方法: python video_processor.py <入力動画パス> <出力ディレクトリ>")
