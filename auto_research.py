"""
auto_research.py - 自動リサーチ機能を提供するモジュール

クライアントの情報に基づいて自動的にリサーチを実行し、
結果をデータベースに保存します。フロントエンドには表示せず、
バックグラウンドで処理します。
"""

import sqlite3
import os
import sys
import json
import time
from threading import Thread

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH
from competitor_analysis import get_youtube_transcript, analyze_competitor_script, store_competitor_script
from db_enhancement import research_detailed_success_case, store_success_case

def run_auto_research(client_id, platforms, industry="一般"):
    """
    クライアント情報に基づいて自動リサーチを実行
    
    Args:
        client_id: クライアントID
        platforms: プラットフォームのリスト
        industry: 業界カテゴリ
    """
    print(f"Client {client_id}の自動リサーチを開始")
    
    for platform in platforms:
        try:
            success_case = research_detailed_success_case(platform, industry)
            case_id = store_success_case(platform, industry, success_case)
            print(f"成功事例を保存しました: {platform}, {industry}, ID: {case_id}")
            
            if success_case and "video_url" in success_case:
                video_url = success_case["video_url"]
                try:
                    transcript_text = get_youtube_transcript(video_url)
                    analysis_result = analyze_competitor_script(transcript_text)
                    script_id = store_competitor_script(
                        platform,
                        industry,
                        video_url,
                        transcript_text,
                        analysis_result
                    )
                    print(f"競合分析を保存しました: {platform}, ID: {script_id}")
                except Exception as e:
                    print(f"競合分析中にエラーが発生しました: {str(e)}")
        except Exception as e:
            print(f"プラットフォーム {platform} のリサーチ中にエラーが発生しました: {str(e)}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clients SET research_completed = 1, research_completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (client_id,)
    )
    conn.commit()
    conn.close()
    
    print(f"Client {client_id}の自動リサーチが完了しました")
    return True

def start_auto_research_thread(client_id, platforms, industry="一般"):
    """
    別スレッドで自動リサーチを開始
    """
    thread = Thread(
        target=run_auto_research,
        args=(client_id, platforms, industry),
        daemon=True
    )
    thread.start()
    return True
