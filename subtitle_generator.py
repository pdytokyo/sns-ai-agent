"""
subtitle_generator.py - 字幕自動生成モジュール

編集済み動画から自動で字幕を生成します。
"""

import sqlite3
import os
import sys
import tempfile
from moviepy.editor import VideoFileClip
import whisper
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

model = whisper.load_model("base")

def extract_audio(video_path, output_path):
    """
    動画から音声を抽出
    
    Args:
        video_path: 動画ファイルのパス
        output_path: 出力する音声ファイルのパス
    """
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(output_path, verbose=False, logger=None)
    return True

def generate_subtitles(processed_video_id):
    """
    処理済み動画から字幕を生成
    
    Args:
        processed_video_id: 処理済み動画のID
        
    Returns:
        list: 生成された字幕のリスト [{start_time, end_time, text}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT output_path FROM processed_videos WHERE id = ?",
        (processed_video_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise ValueError("処理済み動画が見つかりません")
    
    video_path = result[0]
    conn.close()
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        temp_audio_path = temp_audio_file.name
    
    try:
        extract_audio(video_path, temp_audio_path)
        
        result = model.transcribe(
            temp_audio_path,
            language="ja",
            task="transcribe",
            verbose=False
        )
        
        subtitles = []
        for segment in result["segments"]:
            subtitles.append({
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"].strip()
            })
        
        return subtitles
    
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

def store_subtitles(processed_video_id, subtitles):
    """
    生成された字幕をデータベースに保存
    
    Args:
        processed_video_id: 処理済み動画のID
        subtitles: 字幕のリスト [{start_time, end_time, text}, ...]
        
    Returns:
        list: 保存された字幕のID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    subtitle_ids = []
    
    for subtitle in subtitles:
        cursor.execute(
            "INSERT INTO subtitles (processed_video_id, start_time, end_time, text) VALUES (?, ?, ?, ?)",
            (processed_video_id, subtitle["start_time"], subtitle["end_time"], subtitle["text"])
        )
        subtitle_ids.append(cursor.lastrowid)
    
    conn.commit()
    conn.close()
    
    return subtitle_ids
