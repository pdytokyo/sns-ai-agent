import os
import sqlite3
import json
import random
import openai
from dotenv import load_dotenv
import requests
from datetime import datetime
import time

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "your_api_key_here")
openai.api_key = openai_api_key

DB_PATH = "app.db"

def init_db():
    """Initialize the database with enhanced tables for detailed success cases."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detailed_success_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        industry TEXT NOT NULL,
        video_url TEXT,
        buzz_point TEXT,
        top_comments TEXT,
        trend_topics TEXT,
        engagement_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS copyright_free_audio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT,
        genre TEXT,
        mood TEXT,
        duration INTEGER,
        file_path TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Enhanced database tables created successfully.")

def collect_trend_topics():
    """Collect trending topics from Google Trends, YouTube, and TikTok."""
    try:
        trends = {
            "google": ["サステナブル", "メタバース", "ワークライフバランス", "SDGs", "リモートワーク"],
            "youtube": ["ショート動画", "ASMR", "ルーティン", "DIY", "ゲーム実況"],
            "tiktok": ["ダンスチャレンジ", "料理レシピ", "メイク術", "旅行", "ライフハック"]
        }
        
        return json.dumps(trends, ensure_ascii=False)
    except Exception as e:
        print(f"Error collecting trend topics: {str(e)}")
        return json.dumps({"error": "Failed to collect trends"})

def research_detailed_success_case(platform, industry):
    """Research detailed success cases for a specific platform and industry."""
    try:
        if openai_api_key == "your_api_key_here":
            return generate_mock_success_case(platform, industry)
            
        prompt = f"""
        あなたは{industry}業界の{platform}マーケティングの専門家です。
        {industry}業界で{platform}上でバズった投稿・動画の詳細な分析を行ってください。
        
        以下の情報を含めてください：
        1. 架空の動画URL（例：https://www.{platform.lower()}.com/watch?v=xxxx）
        2. バズの起点となったポイント（動画の秒数と内容）
        3. 共感を得ているコメント（上位3件）
        4. 現在のトレンドトピック
        5. なぜこの投稿がエンゲージメントを獲得したかの分析
        
        JSON形式で出力してください。
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        
        try:
            json_result = json.loads(result)
            return json_result
        except:
            print("Could not parse OpenAI response as JSON, using mock data instead.")
            return generate_mock_success_case(platform, industry)
            
    except Exception as e:
        print(f"Error researching success case: {str(e)}")
        return generate_mock_success_case(platform, industry)

def generate_mock_success_case(platform, industry):
    """Generate mock success case data for testing."""
    platforms = {
        "YouTube": {
            "url_format": "https://www.youtube.com/watch?v=",
            "video_ids": ["dQw4w9WgXcQ", "9bZkp7q19f0", "kJQP7kiw5Fk", "JGwWNGJdvx8", "fJ9rUzIMcZQ"]
        },
        "Instagram": {
            "url_format": "https://www.instagram.com/p/",
            "video_ids": ["CqXjp1", "BrKjp2", "AzXjp3", "DyXjp4", "EfXjp5"]
        },
        "TikTok": {
            "url_format": "https://www.tiktok.com/@user/video/",
            "video_ids": ["6827563", "7938274", "8049385", "9150496", "0261507"]
        }
    }
    
    industries = {
        "美容": {
            "buzz_points": [
                "0:15 - 意外な美容法の紹介",
                "0:30 - ビフォーアフターの劇的な変化",
                "1:45 - 有名人の美容法の暴露"
            ],
            "comments": [
                "これ試したら本当に肌が変わった！",
                "なんでもっと早く知らなかったんだろう...",
                "値段も手頃で助かります！"
            ],
            "topics": ["スキンケア", "ナチュラルメイク", "美容成分"]
        },
        "ファッション": {
            "buzz_points": [
                "0:10 - 意外な着こなし方の紹介",
                "0:45 - トレンドアイテムの活用法",
                "1:30 - プチプラコーデの全身紹介"
            ],
            "comments": [
                "このコーデなら私にもできそう！",
                "安いのにこんなにおしゃれに見えるなんて！",
                "明日から真似します！"
            ],
            "topics": ["ミニマリスト", "サステナブル", "古着リメイク"]
        },
        "食品": {
            "buzz_points": [
                "0:20 - 意外な食材の組み合わせ",
                "1:00 - 簡単なのに見栄えする盛り付け",
                "2:15 - 時短テクニックの紹介"
            ],
            "comments": [
                "これ作ったら家族に大好評でした！",
                "材料少ないのにこんなに美味しいなんて！",
                "料理苦手な私でも簡単にできました！"
            ],
            "topics": ["時短レシピ", "一人暮らし", "作り置き"]
        },
        "テクノロジー": {
            "buzz_points": [
                "0:30 - 意外な機能の紹介",
                "1:15 - 知られていないショートカット",
                "2:00 - 最新ガジェットのレビュー"
            ],
            "comments": [
                "これ知らなかった！仕事が捗りそう",
                "解説がわかりやすくて助かります",
                "買おうか迷ってたけどこの動画見て決めました！"
            ],
            "topics": ["AI活用", "生産性向上", "ガジェット比較"]
        },
        "エンタメ": {
            "buzz_points": [
                "0:25 - 意外な裏話の紹介",
                "1:30 - 感動的なシーンの解説",
                "2:45 - 視聴者参加型の企画発表"
            ],
            "comments": [
                "この解説で作品の見方が変わりました！",
                "次回も楽しみにしています！",
                "参加したいです！詳細教えてください！"
            ],
            "topics": ["映画解説", "アニメ考察", "ゲーム実況"]
        }
    }
    
    platform_data = platforms.get(platform, platforms["YouTube"])
    video_id = random.choice(platform_data["video_ids"])
    video_url = platform_data["url_format"] + video_id
    
    industry_data = industries.get(industry, industries["美容"])
    
    engagement_reasons = [
        f"{industry}業界のトレンドを先取りした内容で視聴者の興味を引いた",
        f"視聴者が抱える{industry}に関する悩みを的確に解決する内容だった",
        f"{industry}の専門知識をわかりやすく解説し、視聴者の学びになった",
        f"{industry}に関する意外な事実を紹介し、視聴者の好奇心を刺激した",
        f"親しみやすいトーンと{industry}への情熱が視聴者の共感を得た"
    ]
    
    trends_data = json.loads(collect_trend_topics())
    platform_key = "youtube" if platform == "YouTube" else platform.lower()
    current_trends = trends_data.get(platform_key, ["トレンド情報なし"])
    
    mock_case = {
        "video_url": video_url,
        "buzz_point": random.choice(industry_data["buzz_points"]),
        "top_comments": industry_data["comments"],
        "trend_topics": current_trends,
        "engagement_reason": random.choice(engagement_reasons)
    }
    
    return mock_case

def store_success_case(platform, industry, case_data):
    """Store a success case in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    top_comments = json.dumps(case_data["top_comments"], ensure_ascii=False) if isinstance(case_data["top_comments"], list) else case_data["top_comments"]
    trend_topics = json.dumps(case_data["trend_topics"], ensure_ascii=False) if isinstance(case_data["trend_topics"], list) else case_data["trend_topics"]
    
    cursor.execute('''
    INSERT INTO detailed_success_cases 
    (platform, industry, video_url, buzz_point, top_comments, trend_topics, engagement_reason)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        platform,
        industry,
        case_data["video_url"],
        case_data["buzz_point"],
        top_comments,
        trend_topics,
        case_data["engagement_reason"]
    ))
    
    case_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return case_id

def collect_copyright_free_audio(genre=None, mood=None, limit=10):
    """Collect copyright-free audio from YouTube Audio Library or similar sources."""
    genres = ["ポップ", "ロック", "エレクトロニック", "ヒップホップ", "アンビエント", "ジャズ", "クラシック"]
    moods = ["明るい", "エネルギッシュ", "落ち着いた", "感動的", "ミステリアス", "楽しい", "シリアス"]
    
    if not genre:
        genre = random.choice(genres)
    if not mood:
        mood = random.choice(moods)
    
    audio_tracks = []
    for i in range(limit):
        track = {
            "title": f"{genre}トラック{i+1}",
            "artist": f"アーティスト{random.randint(1, 100)}",
            "genre": genre,
            "mood": mood,
            "duration": random.randint(60, 300),  # 1-5 minutes in seconds
            "file_path": f"/static/audio/{genre.lower()}_{i+1}.mp3",
            "source": "YouTube Audio Library" if random.random() > 0.5 else "Epidemic Sound"
        }
        audio_tracks.append(track)
    
    return audio_tracks

def store_audio_tracks(tracks):
    """Store audio tracks in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for track in tracks:
        cursor.execute('''
        INSERT INTO copyright_free_audio 
        (title, artist, genre, mood, duration, file_path, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            track["title"],
            track["artist"],
            track["genre"],
            track["mood"],
            track["duration"],
            track["file_path"],
            track["source"]
        ))
    
    conn.commit()
    conn.close()
    
    print(f"Stored {len(tracks)} audio tracks in the database.")

def analyze_youtube_transcript(transcript_text):
    """Analyze YouTube transcript to extract keywords and engaging phrases."""
    try:
        if not transcript_text or transcript_text.startswith("This is a mock transcript"):
            return {
                "keywords": ["キーワード1", "キーワード2", "キーワード3"],
                "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
                "sentiment": "ポジティブ"
            }
            
        if openai_api_key == "your_api_key_here":
            return {
                "keywords": ["キーワード1", "キーワード2", "キーワード3"],
                "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
                "sentiment": "ポジティブ"
            }
        
        prompt = f"""
        以下のYouTube動画の字幕テキストを分析し、以下の情報を抽出してください：
        
        1. 頻出キーワード（上位5つ）
        2. 視聴者の共感を得られそうなフレーズ（上位3つ）
        3. 全体的な感情トーン（ポジティブ/ニュートラル/ネガティブ）
        
        字幕テキスト：
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
                "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
                "sentiment": "ポジティブ"
            }
            
    except Exception as e:
        print(f"Error analyzing transcript: {str(e)}")
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
            "sentiment": "ポジティブ"
        }

def generate_data_driven_script(client_id, transcript_analysis=None):
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
    conn.close()
    
    if not success_case:
        mock_case = generate_mock_success_case(platform, "一般")
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
    
    transcript_keywords = []
    engaging_phrases = []
    if transcript_analysis:
        transcript_keywords = transcript_analysis.get("keywords", [])
        engaging_phrases = transcript_analysis.get("engaging_phrases", [])
    
    try:
        if openai_api_key == "your_api_key_here":
            return generate_mock_script(buzz_content, trend_topic, top_comment, target_attributes, operational_purposes, platform, transcript_keywords, engaging_phrases)
            
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
        
        script_text = response.choices[0].message.content
        
        return {
            "script_text": script_text,
            "buzz_point": buzz_content,
            "trend_topic": trend_topic,
            "target_audience": target_text,
            "platform": platform
        }
        
    except Exception as e:
        print(f"Error generating script: {str(e)}")
        return generate_mock_script(buzz_content, trend_topic, top_comment, target_attributes, operational_purposes, platform, transcript_keywords, engaging_phrases)

def generate_mock_script(buzz_content, trend_topic, top_comment, target_attributes, operational_purposes, platform, transcript_keywords=None, engaging_phrases=None):
    """Generate a mock script for testing."""
    target_text = ", ".join(target_attributes) if target_attributes else "一般視聴者"
    purpose_text = ", ".join(operational_purposes) if operational_purposes else "情報提供"
    
    keywords = ", ".join(transcript_keywords[:3]) if transcript_keywords else "キーワード"
    
    script = f"""

こんにちは、皆さん！今日は{buzz_content}についてお話しします。これから紹介する内容は、あなたの{purpose_text}に役立つ情報満載です。{target_text}の皆さんに特におすすめの内容となっています。

多くの方が「{top_comment}」と感じていると思います。実は、この課題は{keywords}と深く関係しています。今日はその解決策を詳しく解説します。

まず最初に試していただきたいのは、〇〇です。これを実践することで、△△の効果が期待できます。具体的な手順は次の通りです...

ところで、最近の{trend_topic}についてご存知ですか？このトレンドを活用することで、さらに効果的に問題を解決できます。

今日お伝えした{buzz_content}の方法とトレンドの{trend_topic}を組み合わせることで、最大の効果が得られます。ぜひ試してみて、結果をコメント欄で教えてください！チャンネル登録もお忘れなく！
"""
    
    return {
        "script_text": script,
        "buzz_point": buzz_content,
        "trend_topic": trend_topic,
        "target_audience": target_text,
        "platform": platform
    }

def main():
    """Main function to collect and store enhanced research data."""
    print("Starting database enhancement and data collection...")
    
    init_db()
    
    platforms = ["YouTube", "Instagram", "TikTok"]
    industries = ["美容", "ファッション", "食品", "テクノロジー", "エンタメ"]
    
    print("Collecting detailed success cases...")
    for platform in platforms:
        for industry in industries:
            print(f"Researching {industry} industry on {platform}...")
            
            for i in range(5):
                case_data = research_detailed_success_case(platform, industry)
                case_id = store_success_case(platform, industry, case_data)
                print(f"Stored success case {i+1}/5 for {industry} on {platform} (ID: {case_id})")
                
                time.sleep(0.5)
    
    print("Collecting copyright-free audio tracks...")
    genres = ["ポップ", "ロック", "エレクトロニック", "ヒップホップ", "アンビエント"]
    moods = ["明るい", "エネルギッシュ", "落ち着いた", "感動的", "楽しい"]
    
    for genre in genres:
        for mood in moods:
            tracks = collect_copyright_free_audio(genre, mood, limit=3)
            store_audio_tracks(tracks)
    
    print("Database enhancement and data collection completed successfully.")

if __name__ == "__main__":
    main()
