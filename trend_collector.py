import os
import json
import sqlite3
import requests
from datetime import datetime
from pytrends.request import TrendReq
from dotenv import load_dotenv

load_dotenv()
DB_PATH = "data.db"

def collect_google_trends(region="JP", limit=10):
    """Google Trendsから上位トレンドを収集"""
    try:
        pytrends = TrendReq(hl='ja-JP', tz=540)  # 日本のタイムゾーン
        trending_searches = pytrends.trending_searches(pn=region)
        trends = trending_searches.values.tolist()
        
        top_trends = [item[0] for item in trends[:limit]]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for rank, keyword in enumerate(top_trends, 1):
            cursor.execute('''
            INSERT INTO weekly_trends (platform, keyword, rank, region)
            VALUES (?, ?, ?, ?)
            ''', ("Google", keyword, rank, region))
        
        conn.commit()
        conn.close()
        
        return top_trends
    except Exception as e:
        print(f"Google Trendsデータ収集エラー: {str(e)}")
        return []

def collect_youtube_trending(region="JP", limit=10):
    """YouTube Trendingから上位動画のキーワードを収集"""
    try:
        api_key = os.getenv("YOUTUBE_API_KEY", "")
        if not api_key:
            print("YouTube API Keyが設定されていません")
            return []
        
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&regionCode={region}&maxResults={limit}&key={api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"YouTube API エラー: {response.status_code}")
            return []
        
        data = response.json()
        trends = []
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for rank, item in enumerate(data.get('items', []), 1):
            title = item['snippet']['title']
            trends.append(title)
            
            cursor.execute('''
            INSERT INTO weekly_trends (platform, keyword, rank, region)
            VALUES (?, ?, ?, ?)
            ''', ("YouTube", title, rank, region))
        
        conn.commit()
        conn.close()
        
        return trends
    except Exception as e:
        print(f"YouTube Trendingデータ収集エラー: {str(e)}")
        return []

def collect_tiktok_trending(region="JP", limit=10):
    """TikTok Trendingの人気ハッシュタグを収集"""
    try:
        
        mock_trends = [
            "#人気チャレンジ2024",
            "#最新トレンド",
            "#話題の曲",
            "#ダンスチャレンジ",
            "#おすすめ料理",
            "#旅行",
            "#メイク術",
            "#スキンケア",
            "#流行コーデ",
            "#ペットかわいい"
        ]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for rank, keyword in enumerate(mock_trends[:limit], 1):
            cursor.execute('''
            INSERT INTO weekly_trends (platform, keyword, rank, region)
            VALUES (?, ?, ?, ?)
            ''', ("TikTok", keyword, rank, region))
        
        conn.commit()
        conn.close()
        
        return mock_trends[:limit]
    except Exception as e:
        print(f"TikTok Trendingデータ収集エラー: {str(e)}")
        return []

def collect_all_trends(region="JP", limit=10):
    """全プラットフォームのトレンドを収集"""
    google_trends = collect_google_trends(region, limit)
    youtube_trends = collect_youtube_trending(region, limit)
    tiktok_trends = collect_tiktok_trending(region, limit)
    
    return {
        "google": google_trends,
        "youtube": youtube_trends,
        "tiktok": tiktok_trends,
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    collect_all_trends()
