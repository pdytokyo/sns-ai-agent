import json
import sqlite3
import os
import re
import sys
import time
import subprocess
import tempfile
from datetime import datetime
import instaloader
from openai import OpenAI
from moviepy.editor import VideoFileClip
import yt_dlp
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, get_api_key

OPENAI_API_KEY = get_api_key("OPENAI_API_KEY", default_value="dummy-api-key-for-testing")
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_username_and_shortcode(post_url):
    """InstagramのURLからユーザー名とショートコードを抽出"""
    pattern = r'instagram\.com/(?:p|reel)/([^/?]+)'
    match = re.search(pattern, post_url)
    if match:
        shortcode = match.group(1)
        return shortcode
    return None

def scrape_instagram_post(post_url, use_mock=True):
    """Instagramの投稿データをスクレイピング"""
    try:
        if use_mock:
            shortcode = extract_username_and_shortcode(post_url)
            if not shortcode:
                return {"success": False, "error": "Invalid Instagram URL"}
            
            mock_data = {
                "https://www.instagram.com/p/C5NJJfJSQnP/": {
                    "views": 10000,
                    "likes": 800,
                    "comments": 120,
                    "caption": "新商品のご紹介です！#新商品 #美容 #スキンケア",
                    "hashtags": "#新商品 #美容 #スキンケア",
                    "posted_at": "2024-04-10 12:30:00",
                    "is_video": True
                },
                "https://www.instagram.com/p/C5Ij-ufSdnm/": {
                    "views": 5000,
                    "likes": 150,
                    "comments": 30,
                    "caption": "今日のメイクのポイント #メイク #コスメ",
                    "hashtags": "#メイク #コスメ",
                    "posted_at": "2024-04-09 15:45:00",
                    "is_video": True
                },
                "https://www.instagram.com/p/C5Hg2YJSQ-K/": {
                    "views": 8000,
                    "likes": 200,
                    "comments": 50,
                    "caption": "新しいヘアスタイルの提案 #ヘアスタイル #ヘアカット",
                    "hashtags": "#ヘアスタイル #ヘアカット",
                    "posted_at": "2024-04-08 09:15:00",
                    "is_video": True
                }
            }
            
            post_data = mock_data.get(post_url, {
                "views": 7000,
                "likes": 300,
                "comments": 80,
                "caption": "サンプル投稿 #サンプル",
                "hashtags": "#サンプル",
                "posted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_video": True
            })
            
            views = post_data["views"]
            likes = post_data["likes"]
            comments = post_data["comments"]
            caption = post_data["caption"]
            hashtags = post_data["hashtags"]
            posted_at = post_data["posted_at"]
            is_video = post_data["is_video"]
            
        else:
            L = instaloader.Instaloader()
            
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            
            views = post.video_view_count if post.is_video else 0
            likes = post.likes
            comments = post.comments
            caption = post.caption if post.caption else ""
            hashtags = " ".join(["#" + tag for tag in post.caption_hashtags])
            posted_at = post.date.strftime("%Y-%m-%d %H:%M:%S")
            is_video = post.is_video
        
        engagement_rate = (likes + comments) / views * 100 if views > 0 else 0
        high_engagement = engagement_rate >= 5.0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO instagram_analysis 
        (post_url, views, likes, comments, caption, hashtags, posted_at, high_engagement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_url,
            views,
            likes,
            comments,
            caption,
            hashtags,
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
        print(f"Instagram投稿スクレイピングエラー: {str(e)}")
        return {"success": False, "error": str(e)}

def download_instagram_video(post_url, output_path):
    """yt-dlpを使用してInstagram動画をダウンロード"""
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post_url])
            
        return True
    except Exception as e:
        print(f"動画ダウンロードエラー: {str(e)}")
        return False

def extract_audio(video_path, audio_path):
    """動画から音声を抽出"""
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        return True
    except Exception as e:
        print(f"音声抽出エラー: {str(e)}")
        return False

def transcribe_audio(audio_path):
    """Whisper APIで音声を文字起こし"""
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        return transcript.text
    except Exception as e:
        print(f"文字起こしエラー: {str(e)}")
        return None

def get_client_info(client_id):
    """クライアント情報を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM clients WHERE id = ?", (client_id,))
    client = cursor.fetchone()
    
    if not client:
        conn.close()
        return None
    
    cursor.execute(
        "SELECT target_attributes, operational_purposes FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    selection = cursor.fetchone()
    
    conn.close()
    
    if not selection:
        return {"name": client["name"], "target_attributes": "", "operational_purposes": ""}
    
    return {
        "name": client["name"],
        "target_attributes": selection["target_attributes"],
        "operational_purposes": selection["operational_purposes"]
    }

def rewrite_script(transcript, client_info):
    """クライアント情報に基づいて台本をリライト"""
    if not transcript or not client_info:
        return None
    
    prompt = f"""
    以下の動画台本を、次のクライアント情報に基づいて「台本構成（話の流れ・順序）は維持したまま」リライトしてください。

    【クライアント情報】
    クライアント名: {client_info['name']}
    ターゲット属性: {client_info['target_attributes']}
    運用目的: {client_info['operational_purposes']}

    【動画台本】
    {transcript}
    
    台本の構成（導入、展開、結論など）と全体的な流れは維持したまま、ターゲット属性や運用目的に合わせた表現やトーンに変更してください。
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"スクリプトリライトエラー: {str(e)}")
        return None

def process_instagram_post(post_url, client_id=None, use_mock=True):
    """Instagram投稿の総合処理（スクレイピング、文字起こし、リライト）"""
    result = scrape_instagram_post(post_url, use_mock=use_mock)
    
    if not result["success"]:
        return result
    
    if result.get("need_transcription", False):
        post_id = result["post_id"]
        
        if use_mock:
            mock_transcripts = {
                "https://www.instagram.com/p/C5NJJfJSQnP/": "こんにちは、今日は新商品のご紹介です。この商品は肌に優しい成分だけで作られていて、敏感肌の方にもおすすめです。使い方はとても簡単で、朝と夜の洗顔後に塗るだけ。1週間使い続けると、肌のキメが整ってきて、化粧ノリも良くなります。ぜひ試してみてください。",
                "https://www.instagram.com/p/C5Ij-ufSdnm/": "今日のメイクのポイントは、ナチュラルだけど印象的な目元です。まずはアイシャドウを薄く全体に塗り、二重幅に少し濃いめのカラーを重ねます。そして目尻に少しだけラメを足すと、パッと華やかな印象になりますよ。最後にマスカラをしっかり塗って完成です。",
                "https://www.instagram.com/p/C5Hg2YJSQ-K/": "今回ご紹介するヘアスタイルは、簡単にできるのに凝って見えるアレンジです。まず髪全体を軽く巻いて、トップにボリュームを出します。次に両サイドの髪を後ろで結んで、残りの髪で結び目を隠します。最後にほぐして完成。忙しい朝でも5分でできるので、ぜひ試してみてください。"
            }
            
            default_transcript = "これはサンプルの文字起こしです。実際の動画では、商品やサービスの特徴、使い方、効果などについて詳しく説明しています。視聴者の興味を引くために、冒頭で問いかけをし、中盤で具体的なメリットを紹介し、最後にアクションを促すような構成になっています。"
            
            transcript = mock_transcripts.get(post_url, default_transcript)
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE instagram_analysis SET transcript = ? WHERE id = ?",
                (transcript, post_id)
            )
            conn.commit()
            
            rewritten_script = None
            if client_id:
                mock_client_info = {
                    1: {
                        "name": "美容サロンA",
                        "target_attributes": "20代〜30代女性、美容に関心が高い",
                        "operational_purposes": "新規顧客獲得、サービス認知度向上"
                    },
                    2: {
                        "name": "アパレルショップB",
                        "target_attributes": "10代後半〜20代前半、トレンドに敏感",
                        "operational_purposes": "新商品PR、来店促進"
                    }
                }
                
                client_info = mock_client_info.get(client_id, {
                    "name": "サンプル企業",
                    "target_attributes": "一般消費者",
                    "operational_purposes": "ブランド認知向上"
                })
                
                if client_info:
                    mock_rewrites = {
                        "https://www.instagram.com/p/C5NJJfJSQnP/": {
                            1: "皆さんこんにちは！今日は待望の新商品をご紹介します✨\n\nこの商品は20代〜30代の美肌を目指す女性のために開発された特別なアイテム。敏感肌の方でも安心して使える優しい成分だけで作られています。\n\n使い方はとっても簡単！朝と夜の洗顔後に軽くなじませるだけ。\n\nたった1週間続けるだけで、肌のキメが整って、メイクのノリが格段に良くなるのを実感できますよ。\n\n今なら初回限定20%オフキャンペーン中です。ぜひ当サロンでお試しください！"
                        }
                    }
                    
                    post_client_rewrites = mock_rewrites.get(post_url, {})
                    rewritten_script = post_client_rewrites.get(client_id)
                    
                    if not rewritten_script:
                        rewritten_script = f"【{client_info['name']}向けにリライトした台本】\n\n{transcript}\n\n※このコンテンツは{client_info['target_attributes']}向けに最適化され、{client_info['operational_purposes']}を目的としています。"
                    
                    cursor.execute(
                        "UPDATE instagram_analysis SET rewritten_script = ? WHERE id = ?",
                        (rewritten_script, post_id)
                    )
                    conn.commit()
            
            conn.close()
            
            return {
                **result,
                "transcript": transcript,
                "rewritten_script": rewritten_script
            }
        
        else:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
                video_path = video_file.name
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
                audio_path = audio_file.name
            
            try:
                if not download_instagram_video(post_url, video_path):
                    return {**result, "transcript": None, "rewritten_script": None}
                
                if not extract_audio(video_path, audio_path):
                    return {**result, "transcript": None, "rewritten_script": None}
                
                transcript = transcribe_audio(audio_path)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE instagram_analysis SET transcript = ? WHERE id = ?",
                    (transcript, post_id)
                )
                conn.commit()
                
                rewritten_script = None
                if client_id and transcript:
                    client_info = get_client_info(client_id)
                    
                    if client_info:
                        rewritten_script = rewrite_script(transcript, client_info)
                        
                        cursor.execute(
                            "UPDATE instagram_analysis SET rewritten_script = ? WHERE id = ?",
                            (rewritten_script, post_id)
                        )
                        conn.commit()
                
                conn.close()
                
                return {
                    **result,
                    "transcript": transcript,
                    "rewritten_script": rewritten_script
                }
                
            finally:
                for path in [video_path, audio_path]:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
    
    return result

def get_instagram_analysis(post_id=None):
    """Instagram分析結果を取得"""
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
    if len(sys.argv) > 1:
        post_url = sys.argv[1]
        client_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        
        result = process_instagram_post(post_url, client_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("使用法: python instagram_analyzer.py <instagram_post_url> [client_id]")
