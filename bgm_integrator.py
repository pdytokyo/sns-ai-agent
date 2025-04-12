"""
bgm_integrator.py - BGM挿入モジュール

処理済み動画に選択されたBGMを挿入します。
"""

import sqlite3
import os
import sys
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

def get_video_and_bgm_paths(processed_video_id, bgm_id):
    """
    動画とBGMのファイルパスを取得
    
    Args:
        processed_video_id: 処理済み動画のID
        bgm_id: BGMのID
        
    Returns:
        tuple: (client_id, video_path, bgm_path)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT client_id, output_path FROM processed_videos WHERE id = ?",
        (processed_video_id,)
    )
    video_result = cursor.fetchone()
    
    if not video_result:
        conn.close()
        raise ValueError("処理済み動画が見つかりません")
    
    client_id, video_path = video_result
    
    cursor.execute(
        "SELECT file_path FROM copyright_free_audio WHERE id = ?",
        (bgm_id,)
    )
    bgm_result = cursor.fetchone()
    
    if not bgm_result:
        conn.close()
        raise ValueError("BGMが見つかりません")
    
    bgm_path = bgm_result[0]
    
    conn.close()
    
    return client_id, video_path, bgm_path

def add_bgm_to_video(video_path, bgm_path, bgm_volume=0.5, output_dir="output/final"):
    """
    動画にBGMを追加
    
    Args:
        video_path: 動画ファイルのパス
        bgm_path: BGMファイルのパス
        bgm_volume: BGMの音量 (0.0 - 1.0)
        output_dir: 出力ディレクトリ
        
    Returns:
        str: 出力ファイルのパス
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")
    
    if not os.path.exists(bgm_path):
        raise FileNotFoundError(f"BGMファイルが見つかりません: {bgm_path}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_filename = f"final_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        video = VideoFileClip(video_path)
        
        original_audio = video.audio
        
        bgm = AudioFileClip(bgm_path)
        
        if bgm.duration < video.duration:
            bgm = bgm.loop(duration=video.duration)
        else:
            bgm = bgm.subclip(0, video.duration)
        
        bgm = bgm.volumex(bgm_volume)
        
        final_audio = CompositeAudioClip([original_audio, bgm])
        
        final_video = video.set_audio(final_audio)
        
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        video.close()
        bgm.close()
        final_video.close()
        
        return output_path
    
    except Exception as e:
        raise Exception(f"BGM挿入中にエラーが発生しました: {str(e)}")

def create_final_video(processed_video_id, bgm_id, bgm_volume=0.5):
    """
    最終動画を作成してデータベースに保存
    
    Args:
        processed_video_id: 処理済み動画のID
        bgm_id: BGMのID
        bgm_volume: BGMの音量 (0.0 - 1.0)
        
    Returns:
        int: 最終動画のID
    """
    try:
        client_id, video_path, bgm_path = get_video_and_bgm_paths(processed_video_id, bgm_id)
        
        output_path = add_bgm_to_video(video_path, bgm_path, bgm_volume)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO final_videos (client_id, processed_video_id, bgm_id, bgm_volume, output_path) VALUES (?, ?, ?, ?, ?)",
            (client_id, processed_video_id, bgm_id, bgm_volume, output_path)
        )
        
        final_video_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return final_video_id
    
    except Exception as e:
        raise Exception(f"最終動画作成中にエラーが発生しました: {str(e)}")
