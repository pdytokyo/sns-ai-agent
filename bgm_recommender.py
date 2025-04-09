"""
bgm_recommender.py - 動画の内容に基づいて最適なBGMを提案するスクリプト

このスクリプトは字幕ファイル（SRT）の内容を分析し、
OpenAIのGPT-3.5-turbo APIを使用して、動画の内容に最適なBGMを提案します。

使用ライブラリ:
- OpenAI GPT-3.5-turbo API: BGM提案の生成
"""

import os
import re
import sys
import json
import openai
from datetime import datetime


def get_api_key():
    """
    環境変数からOpenAI APIキーを取得します。
    
    Returns:
        str or None: APIキー、取得できない場合はNone
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("エラー: OPENAI_API_KEYが設定されていません。")
        print("環境変数にOPENAI_API_KEYを設定してください。")
        return None
    return api_key


def parse_srt_file(srt_file_path):
    """
    SRTファイルを解析し、字幕テキストを抽出します。
    
    Args:
        srt_file_path (str): SRTファイルのパス
        
    Returns:
        str or None: 抽出された字幕テキスト、エラー時はNone
    """
    try:
        print(f"字幕ファイルを解析中: {srt_file_path}")
        
        if not os.path.exists(srt_file_path):
            print(f"エラー: 字幕ファイルが見つかりません: {srt_file_path}")
            return None
        
        with open(srt_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        subtitle_pattern = r'\d+\s+\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}\s+(.*?)(?=\n\s*\n|\Z)'
        subtitles = re.findall(subtitle_pattern, content, re.DOTALL)
        
        full_text = ' '.join([text.strip().replace('\n', ' ') for text in subtitles])
        
        print(f"字幕テキストの抽出が完了しました（{len(full_text)}文字）")
        return full_text
    
    except Exception as e:
        print(f"字幕ファイル解析中にエラーが発生しました: {str(e)}")
        return None


def analyze_content_and_recommend_bgm(subtitle_text, api_key):
    """
    字幕テキストを分析し、最適なBGMを提案します。
    
    Args:
        subtitle_text (str): 分析する字幕テキスト
        api_key (str): OpenAI APIキー
        
    Returns:
        dict or None: BGM提案結果、エラー時はNone
    """
    try:
        print("字幕内容を分析中...")
        
        openai.api_key = api_key
        
        max_text_length = 4000
        if len(subtitle_text) > max_text_length:
            print(f"テキストが長すぎるため、{max_text_length}文字に切り詰めます")
            subtitle_text = subtitle_text[:max_text_length] + "..."
        
        prompt = f"""
以下は動画の字幕テキストです。この内容に最適なBGM（バックグラウンドミュージック）を提案してください。
以下の情報を含めてください：
1. 推奨するBGMのジャンル
2. 推奨する曲調（テンポ、雰囲気など）
3. 具体的な曲の例（アーティスト名と曲名）を3つ
4. なぜこのBGMが内容に合っているのか、その理由

字幕テキスト:
{subtitle_text}

回答は日本語でJSON形式で返してください。以下のフォーマットに従ってください：
{{
  "genre": "推奨するジャンル",
  "mood": "推奨する曲調の詳細",
  "examples": [
    {{"artist": "アーティスト名1", "title": "曲名1"}},
    {{"artist": "アーティスト名2", "title": "曲名2"}},
    {{"artist": "アーティスト名3", "title": "曲名3"}}
  ],
  "reason": "このBGMを推奨する理由"
}}
"""
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは動画内容に基づいて最適なBGMを提案する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        recommendation_text = response.choices[0].message.content.strip()
        
        json_match = re.search(r'({[\s\S]*})', recommendation_text)
        if json_match:
            recommendation_json = json_match.group(1)
            recommendation = json.loads(recommendation_json)
            return recommendation
        else:
            print("エラー: APIレスポンスからJSON形式の提案を抽出できませんでした")
            return None
    
    except Exception as e:
        print(f"BGM提案生成中にエラーが発生しました: {str(e)}")
        return None


def display_bgm_recommendation(recommendation):
    """
    BGM提案結果を表示します。
    
    Args:
        recommendation (dict): BGM提案結果
    """
    print("\n" + "=" * 50)
    print("【BGM提案結果】")
    print("=" * 50)
    
    print(f"■ 推奨ジャンル: {recommendation.get('genre', '不明')}")
    print(f"■ 推奨曲調: {recommendation.get('mood', '不明')}")
    
    print("\n■ おすすめ曲例:")
    examples = recommendation.get('examples', [])
    for i, example in enumerate(examples, 1):
        artist = example.get('artist', '不明')
        title = example.get('title', '不明')
        print(f"  {i}. {artist} - {title}")
    
    print(f"\n■ 推奨理由:\n{recommendation.get('reason', '不明')}")
    print("=" * 50)


def main():
    """
    メイン処理を実行します。
    """
    try:
        subtitle_file_path = "output/subtitles.srt"
        
        print("=== BGM提案処理開始 ===")
        print(f"字幕ファイル: {subtitle_file_path}")
        print("===========================")
        
        api_key = get_api_key()
        if not api_key:
            return False
        
        subtitle_text = parse_srt_file(subtitle_file_path)
        if not subtitle_text:
            return False
        
        recommendation = analyze_content_and_recommend_bgm(subtitle_text, api_key)
        if not recommendation:
            return False
        
        display_bgm_recommendation(recommendation)
        
        print("=== BGM提案処理完了 ===")
        return True
    
    except Exception as e:
        print(f"処理中にエラーが発生しました: {str(e)}")
        print("=== BGM提案処理失敗 ===")
        return False


if __name__ == "__main__":
    main()
