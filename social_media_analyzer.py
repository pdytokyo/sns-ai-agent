import os
import json
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv
import re
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from competitor_analysis import get_youtube_transcript, analyze_competitor_script

load_dotenv()
DB_PATH = "data.db"

def extract_video_id(url, platform):
    """Extract video ID from URL based on platform"""
    if platform.lower() == "youtube":
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if video_id_match:
            return video_id_match.group(1)
    elif platform.lower() == "instagram":
        video_id_match = re.search(r'\/p\/([^\/]+)|\/reel\/([^\/]+)', url)
        if video_id_match:
            return video_id_match.group(1) or video_id_match.group(2)
    elif platform.lower() == "tiktok":
        video_id_match = re.search(r'\/video\/(\d+)', url)
        if video_id_match:
            return video_id_match.group(1)
    
    return None

def analyze_youtube_video(video_url):
    """Analyze YouTube video and store in competitor_analysis table"""
    try:
        video_id = extract_video_id(video_url, "youtube")
        if not video_id:
            return {"success": False, "error": "Invalid YouTube URL"}
        
        api_key = os.getenv("YOUTUBE_API_KEY", "")
        if not api_key:
            return {"success": False, "error": "YouTube API Key not set"}
        
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            return {"success": False, "error": f"YouTube API Error: {response.status_code}"}
        
        data = response.json()
        if not data.get('items'):
            return {"success": False, "error": "Video not found"}
        
        video_data = data['items'][0]
        title = video_data['snippet']['title']
        view_count = int(video_data['statistics'].get('viewCount', 0))
        comment_count = int(video_data['statistics'].get('commentCount', 0))
        
        engagement_rate = (comment_count / view_count) * 100 if view_count > 0 else 0
        
        transcript = get_youtube_transcript(video_url)
        analysis_result = analyze_competitor_script(transcript)
        
        popular_phrases = json.dumps(analysis_result.get("empathy_points", []), ensure_ascii=False)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO competitor_analysis 
        (platform, video_url, video_title, view_count, comment_count, engagement_rate, popular_phrases)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            "YouTube",
            video_url,
            title,
            view_count,
            comment_count,
            engagement_rate,
            popular_phrases
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        script_id = store_competitor_script_data(
            "YouTube", 
            "", # industry
            video_url, 
            transcript, 
            analysis_result
        )
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "script_id": script_id,
            "title": title,
            "view_count": view_count,
            "comment_count": comment_count,
            "engagement_rate": engagement_rate,
            "popular_phrases": json.loads(popular_phrases) if popular_phrases else []
        }
        
    except Exception as e:
        print(f"YouTube分析エラー: {str(e)}")
        return {"success": False, "error": str(e)}

def analyze_instagram_post(post_url):
    """Analyze Instagram post and store in competitor_analysis table"""
    try:
        
        
        mock_title = "インスタグラム投稿サンプル"
        mock_view_count = 15000
        mock_comment_count = 450
        mock_engagement_rate = 3.0
        mock_popular_phrases = json.dumps([
            "素敵な写真ですね！",
            "参考になります",
            "次回も楽しみにしています"
        ], ensure_ascii=False)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO competitor_analysis 
        (platform, video_url, video_title, view_count, comment_count, engagement_rate, popular_phrases)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Instagram",
            post_url,
            mock_title,
            mock_view_count,
            mock_comment_count,
            mock_engagement_rate,
            mock_popular_phrases
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "title": mock_title,
            "view_count": mock_view_count,
            "comment_count": mock_comment_count,
            "engagement_rate": mock_engagement_rate,
            "popular_phrases": json.loads(mock_popular_phrases)
        }
        
    except Exception as e:
        print(f"Instagram分析エラー: {str(e)}")
        return {"success": False, "error": str(e)}

def analyze_tiktok_video(video_url):
    """Analyze TikTok video and store in competitor_analysis table"""
    try:
        
        
        mock_title = "TikTokトレンド動画サンプル"
        mock_view_count = 50000
        mock_comment_count = 1200
        mock_engagement_rate = 2.4
        mock_popular_phrases = json.dumps([
            "すごい技術！",
            "真似してみます",
            "BGMは何ですか？"
        ], ensure_ascii=False)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO competitor_analysis 
        (platform, video_url, video_title, view_count, comment_count, engagement_rate, popular_phrases)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            "TikTok",
            video_url,
            mock_title,
            mock_view_count,
            mock_comment_count,
            mock_engagement_rate,
            mock_popular_phrases
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "title": mock_title,
            "view_count": mock_view_count,
            "comment_count": mock_comment_count,
            "engagement_rate": mock_engagement_rate,
            "popular_phrases": json.loads(mock_popular_phrases)
        }
        
    except Exception as e:
        print(f"TikTok分析エラー: {str(e)}")
        return {"success": False, "error": str(e)}

def store_competitor_script_data(platform, industry, video_url, transcript, analysis_result):
    """Store data in competitor_scripts table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        keywords = json.dumps(analysis_result.get("keywords", []), ensure_ascii=False)
        empathy_points = json.dumps(analysis_result.get("empathy_points", []), ensure_ascii=False)
        hook = analysis_result.get("hook", "")
        
        cursor.execute('''
        INSERT INTO competitor_scripts 
        (platform, industry, video_url, full_script, keywords, empathy_points, hook)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            platform,
            industry,
            video_url,
            transcript,
            keywords,
            empathy_points,
            hook
        ))
        
        script_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return script_id
    except Exception as e:
        print(f"競合スクリプト保存エラー: {str(e)}")
        return None

def analyze_social_media_content(url, platform):
    """Analyze social media content based on platform"""
    if platform.lower() == "youtube":
        return analyze_youtube_video(url)
    elif platform.lower() == "instagram":
        return analyze_instagram_post(url)
    elif platform.lower() == "tiktok":
        return analyze_tiktok_video(url)
    else:
        return {"success": False, "error": f"Unsupported platform: {platform}"}

if __name__ == "__main__":
    if len(sys.argv) > 2:
        url = sys.argv[1]
        platform = sys.argv[2]
        result = analyze_social_media_content(url, platform)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python social_media_analyzer.py <url> <platform>")
