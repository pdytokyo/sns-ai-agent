import os
import sqlite3
import json
import openai
from dotenv import load_dotenv
import re
from collections import Counter

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "your_api_key_here")
openai.api_key = openai_api_key

DB_PATH = "app.db"

def analyze_transcript(transcript_text):
    """
    Analyze YouTube transcript to extract keywords and engaging phrases.
    
    Args:
        transcript_text (str): The transcript text to analyze
        
    Returns:
        dict: Dictionary containing keywords, engaging phrases, and sentiment
    """
    if not transcript_text or transcript_text.startswith("This is a mock transcript"):
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
            "sentiment": "ポジティブ"
        }
    
    try:
        words = re.findall(r'\b\w+\b', transcript_text.lower())
        stop_words = set(['の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ',
                          'the', 'and', 'to', 'of', 'a', 'in', 'that', 'is', 'was', 'for'])
        filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
        
        word_counts = Counter(filtered_words)
        keywords = [word for word, count in word_counts.most_common(5)]
        
        sentences = re.split(r'[。.!?！？]', transcript_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        engaging_candidates = []
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords[:3]) or '?' in sentence or '？' in sentence:
                engaging_candidates.append(sentence)
        
        engaging_phrases = engaging_candidates[:3] if engaging_candidates else sentences[:3]
        
        positive_words = ['良い', '素晴らしい', '好き', '楽しい', '嬉しい', 'good', 'great', 'like', 'love', 'happy']
        negative_words = ['悪い', '嫌い', '残念', '悲しい', '怖い', 'bad', 'hate', 'dislike', 'sad', 'afraid']
        
        positive_count = sum(1 for word in filtered_words if any(pos in word for pos in positive_words))
        negative_count = sum(1 for word in filtered_words if any(neg in word for neg in negative_words))
        
        sentiment = "ポジティブ" if positive_count > negative_count else "ネガティブ" if negative_count > positive_count else "ニュートラル"
        
        return {
            "keywords": keywords,
            "engaging_phrases": engaging_phrases,
            "sentiment": sentiment
        }
    
    except Exception as e:
        print(f"Error in basic transcript analysis: {str(e)}")
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
            "sentiment": "ポジティブ"
        }

def analyze_with_openai(transcript_text):
    """
    Analyze YouTube transcript using OpenAI API.
    
    Args:
        transcript_text (str): The transcript text to analyze
        
    Returns:
        dict: Dictionary containing keywords, engaging phrases, and sentiment
    """
    try:
        if openai_api_key == "your_api_key_here":
            return analyze_transcript(transcript_text)
        
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
            print("Could not parse OpenAI response as JSON, using basic analysis instead.")
            return analyze_transcript(transcript_text)
            
    except Exception as e:
        print(f"Error analyzing transcript with OpenAI: {str(e)}")
        return analyze_transcript(transcript_text)

def get_client_transcripts(client_id):
    """
    Get all transcripts for a client from the database.
    
    Args:
        client_id (str): The client ID
        
    Returns:
        list: List of transcript texts
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT transcript_text FROM client_video_transcripts
        WHERE client_id = ?
        ''', (client_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return []
        
        return [row[0] for row in results]
    
    except Exception as e:
        print(f"Error getting client transcripts: {str(e)}")
        return []

def analyze_client_transcripts(client_id, use_openai=True):
    """
    Analyze all transcripts for a client.
    
    Args:
        client_id (str): The client ID
        use_openai (bool): Whether to use OpenAI for analysis
        
    Returns:
        dict: Combined analysis results
    """
    transcripts = get_client_transcripts(client_id)
    
    if not transcripts:
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
            "sentiment": "ポジティブ"
        }
    
    combined_text = " ".join(transcripts)
    
    if use_openai and openai_api_key != "your_api_key_here":
        return analyze_with_openai(combined_text)
    else:
        return analyze_transcript(combined_text)

def store_transcript_analysis(client_id, analysis_results):
    """
    Store transcript analysis results in the database.
    
    Args:
        client_id (str): The client ID
        analysis_results (dict): The analysis results
        
    Returns:
        int: The ID of the stored analysis
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcript_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            keywords TEXT,
            engaging_phrases TEXT,
            sentiment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        keywords = json.dumps(analysis_results["keywords"], ensure_ascii=False)
        engaging_phrases = json.dumps(analysis_results["engaging_phrases"], ensure_ascii=False)
        sentiment = analysis_results["sentiment"]
        
        cursor.execute('''
        INSERT INTO transcript_analysis 
        (client_id, keywords, engaging_phrases, sentiment)
        VALUES (?, ?, ?, ?)
        ''', (
            client_id,
            keywords,
            engaging_phrases,
            sentiment
        ))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return analysis_id
    
    except Exception as e:
        print(f"Error storing transcript analysis: {str(e)}")
        return None

def get_transcript_analysis(client_id):
    """
    Get transcript analysis for a client from the database.
    
    Args:
        client_id (str): The client ID
        
    Returns:
        dict: The analysis results
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT keywords, engaging_phrases, sentiment
        FROM transcript_analysis
        WHERE client_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        ''', (client_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            analysis = analyze_client_transcripts(client_id)
            store_transcript_analysis(client_id, analysis)
            return analysis
        
        keywords, engaging_phrases, sentiment = result
        
        keywords = json.loads(keywords)
        engaging_phrases = json.loads(engaging_phrases)
        
        return {
            "keywords": keywords,
            "engaging_phrases": engaging_phrases,
            "sentiment": sentiment
        }
    
    except Exception as e:
        print(f"Error getting transcript analysis: {str(e)}")
        return {
            "keywords": ["キーワード1", "キーワード2", "キーワード3"],
            "engaging_phrases": ["共感フレーズ1", "共感フレーズ2", "共感フレーズ3"],
            "sentiment": "ポジティブ"
        }

if __name__ == "__main__":
    sample_transcript = """
    こんにちは、皆さん。今日は新しい商品についてご紹介します。
    この商品は非常に優れた機能を持っています。特に使いやすさが特徴です。
    多くのお客様から「使いやすい」「便利」というコメントをいただいています。
    ぜひ試してみてください。きっと気に入ると思います。
    質問があれば、コメント欄でお待ちしています。
    """
    
    print("Basic analysis:")
    basic_analysis = analyze_transcript(sample_transcript)
    print(json.dumps(basic_analysis, ensure_ascii=False, indent=2))
    
    print("\nOpenAI analysis (if API key is set):")
    openai_analysis = analyze_with_openai(sample_transcript)
    print(json.dumps(openai_analysis, ensure_ascii=False, indent=2))
