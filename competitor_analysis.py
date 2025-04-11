import os
import sqlite3
import json
import openai
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, _errors
import re

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "your_api_key_here")
openai.api_key = openai_api_key

DB_PATH = "data.db"

def extract_video_id(url):
    """Extract YouTube video ID from URL."""
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def get_youtube_transcript(video_url):
    """Get transcript for a YouTube video."""
    video_id = extract_video_id(video_url)
    if not video_id:
        return f"Invalid YouTube URL: {video_url}"
    
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ja', 'en'])
        transcript_text = ' '.join([item['text'] for item in transcript_list])
        return transcript_text
    except _errors.TranscriptsDisabled:
        return f"Transcripts are disabled for video: {video_id}"
    except _errors.NoTranscriptFound:
        return f"No transcript found for video: {video_id}"
    except Exception as e:
        return f"Error getting transcript for video {video_id}: {str(e)}"

def analyze_competitor_script(transcript_text):
    """Analyze competitor script to extract keywords, empathy points, and hook."""
    if not transcript_text or transcript_text.startswith("Invalid YouTube URL") or transcript_text.startswith("Transcripts are disabled") or transcript_text.startswith("No transcript found") or transcript_text.startswith("Error getting transcript"):
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "empathy_points": ["共感ポイント1", "共感ポイント2", "共感ポイント3"],
            "hook": "冒頭フックの例"
        }
        
    try:
        if openai_api_key == "your_api_key_here":
            return {
                "keywords": ["キーワード1", "キーワード2", "キーワード3"],
                "empathy_points": ["共感ポイント1", "共感ポイント2", "共感ポイント3"],
                "hook": "冒頭フックの例"
            }
        
        prompt = f"""
        以下のYouTube動画の台本を分析し、以下の情報を抽出してください：
        
        1. 頻出キーワード（上位5つ）
        2. 視聴者の共感を得られそうなポイント（上位3つ）
        3. 冒頭のフック（最初の30秒程度で視聴者の興味を引く部分）
        
        台本：
        {transcript_text[:2000]}  # Limit to first 2000 chars
        
        JSON形式で出力してください。
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.5,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        
        try:
            json_result = json.loads(result)
            return json_result
        except:
            print("Could not parse OpenAI response as JSON, using mock data instead.")
            return {
                "keywords": ["キーワード1", "キーワード2", "キーワード3"],
                "empathy_points": ["共感ポイント1", "共感ポイント2", "共感ポイント3"],
                "hook": "冒頭フックの例"
            }
            
    except Exception as e:
        print(f"Error analyzing script: {str(e)}")
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "empathy_points": ["共感ポイント1", "共感ポイント2", "共感ポイント3"],
            "hook": "冒頭フックの例"
        }

def store_competitor_script(platform, industry, video_url, transcript_text, analysis_result):
    """Store competitor script in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    keywords = json.dumps(analysis_result["keywords"], ensure_ascii=False) if isinstance(analysis_result["keywords"], list) else analysis_result["keywords"]
    empathy_points = json.dumps(analysis_result["empathy_points"], ensure_ascii=False) if isinstance(analysis_result["empathy_points"], list) else analysis_result["empathy_points"]
    hook = analysis_result["hook"]
    
    cursor.execute('''
    INSERT INTO competitor_scripts 
    (platform, industry, video_url, full_script, keywords, empathy_points, hook)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        platform,
        industry,
        video_url,
        transcript_text,
        keywords,
        empathy_points,
        hook
    ))
    
    script_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return script_id
