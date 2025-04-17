import os
import re
import json
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
import yt_dlp
from moviepy.editor import VideoFileClip
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data.db"

def extract_shortcode(url):
    """Extract Instagram post shortcode from URL"""
    pattern = r'instagram\.com/(?:p|reel)/([^/?]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def scrape_instagram_post(url, browser_page=None):
    """Scrape Instagram post data using Playwright"""
    try:
        shortcode = extract_shortcode(url)
        if not shortcode:
            return {"success": False, "error": "Invalid Instagram URL"}
        
        close_browser = False
        if browser_page is None:
            close_browser = True
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                browser_page = context.new_page()
                
                browser_page.goto(url, wait_until="networkidle")
                
                result = extract_post_data(browser_page, url)
                
                browser.close()
                
                return result
        else:
            browser_page.goto(url, wait_until="networkidle")
            
            return extract_post_data(browser_page, url)
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_post_data(page, url):
    """Extract data from Instagram post page"""
    try:
        page.wait_for_selector('article', timeout=10000)
        
        is_video = page.query_selector('video') is not None
        
        views = 0
        if is_video:
            views_element = page.query_selector('span:has-text("views")')
            if views_element:
                views_text = views_element.evaluate('node => node.previousSibling.textContent')
                views = parse_count(views_text)
        
        likes = 0
        likes_element = page.query_selector('span:has-text("likes")')
        if likes_element:
            likes_text = likes_element.evaluate('node => node.previousSibling.textContent')
            likes = parse_count(likes_text)
        
        comments = 0
        comments_element = page.query_selector('span:has-text("comments")')
        if comments_element:
            comments_text = comments_element.evaluate('node => node.previousSibling.textContent')
            comments = parse_count(comments_text)
        
        caption = ""
        caption_element = page.query_selector('div[data-testid="post-caption"]')
        if caption_element:
            caption = caption_element.text_content().strip()
        
        hashtags = []
        if caption:
            hashtags = re.findall(r'#\w+', caption)
        
        posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_element = page.query_selector('time')
        if time_element:
            datetime_attr = time_element.get_attribute('datetime')
            if datetime_attr:
                posted_at = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S")
        
        engagement_rate = (likes + comments) / views * 100 if views > 0 else 0
        high_engagement = engagement_rate >= 5.0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO instagram_analysis 
        (post_url, views, likes, comments, caption, hashtags, posted_at, high_engagement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            url,
            views,
            likes,
            comments,
            caption,
            ' '.join(hashtags),
            posted_at,
            high_engagement
        ))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "post_id": post_id,
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate,
            "high_engagement": high_engagement,
            "need_transcription": high_engagement and is_video
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def parse_count(count_text):
    """Parse count text (e.g., '1.2K') to integer"""
    if not count_text:
        return 0
    
    count_text = count_text.strip().lower()
    
    if 'k' in count_text:
        return int(float(count_text.replace('k', '')) * 1000)
    elif 'm' in count_text:
        return int(float(count_text.replace('m', '')) * 1000000)
    else:
        return int(count_text.replace(',', ''))

def download_instagram_video(url, output_path):
    """Download Instagram video using yt-dlp"""
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        return True
    except Exception as e:
        print(f"Video download error: {str(e)}")
        return False

def extract_audio(video_path, audio_path):
    """Extract audio from video"""
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        return True
    except Exception as e:
        print(f"Audio extraction error: {str(e)}")
        return False

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper API"""
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        return transcript.text
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return None

def process_instagram_post(url, client_id=None):
    """Process Instagram post (scrape, download, transcribe)"""
    result = scrape_instagram_post(url)
    
    if not result["success"]:
        return result
    
    if result.get("need_transcription", False):
        post_id = result["post_id"]
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
            video_path = video_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name
        
        try:
            if not download_instagram_video(url, video_path):
                return {**result, "transcript": None}
            
            if not extract_audio(video_path, audio_path):
                return {**result, "transcript": None}
            
            transcript = transcribe_audio(audio_path)
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE instagram_analysis SET transcript = ? WHERE id = ?",
                (transcript, post_id)
            )
            conn.commit()
            conn.close()
            
            return {**result, "transcript": transcript}
            
        finally:
            for path in [video_path, audio_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
    
    return result

def get_instagram_analysis(post_id=None):
    """Get Instagram analysis data from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if post_id:
        cursor.execute("SELECT * FROM instagram_analysis WHERE id = ?", (post_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        return dict(result)
    else:
        cursor.execute("SELECT * FROM instagram_analysis ORDER BY created_at DESC")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = process_instagram_post(url)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python instagram_research.py <instagram_url>")
