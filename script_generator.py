"""
script_generator.py - 複数の台本提案を生成するモジュール

クライアント情報と自動リサーチの結果に基づいて、
複数パターンの台本提案を自動生成します。
"""

import sqlite3
import os
import sys
import json
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script_proposals(client_id, num_proposals=3):
    """
    クライアント情報に基づいて複数の台本提案を生成
    
    Args:
        client_id: クライアントID
        num_proposals: 生成する提案数
        
    Returns:
        list: 生成された台本提案のリスト [{title, content}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT target_attributes, operational_purposes, platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    selection = cursor.fetchone()
    
    if not selection:
        conn.close()
        raise ValueError("クライアント選択情報が見つかりません")
    
    target_attributes = selection[0].split(",")
    operational_purposes = selection[1].split(",")
    platforms = selection[2].split(",")
    platform = platforms[0] if platforms else "YouTube"
    
    cursor.execute(
        "SELECT full_script, keywords, empathy_points, hook FROM competitor_scripts WHERE platform = ? ORDER BY created_at DESC LIMIT 3",
        (platform,)
    )
    competitor_data = cursor.fetchall()
    
    cursor.execute(
        "SELECT buzz_point, top_comments, trend_topics FROM detailed_success_cases WHERE platform = ? ORDER BY created_at DESC LIMIT 3",
        (platform,)
    )
    success_cases = cursor.fetchall()
    
    conn.close()
    
    proposals = []
    
    styles = ["エモーショナル", "情報提供型", "ストーリーテリング"]
    
    for i in range(min(num_proposals, len(styles))):
        style = styles[i]
        
        competitor = competitor_data[min(i, len(competitor_data)-1)] if competitor_data else None
        success_case = success_cases[min(i, len(success_cases)-1)] if success_cases else None
        
        prompt = f"""
        以下の情報に基づいて、{platform}用の{style}スタイルの台本を作成してください。
        
        ターゲット属性: {', '.join(target_attributes)}
        運用目的: {', '.join(operational_purposes)}
        """
        
        if competitor:
            keywords = json.loads(competitor[1]) if isinstance(competitor[1], str) else competitor[1]
            empathy_points = json.loads(competitor[2]) if isinstance(competitor[2], str) else competitor[2]
            hook = competitor[3]
            
            prompt += f"""
            【必須事項】:
            - 冒頭フック: 「{hook}」を参考にする
            - キーワード: 「{', '.join(keywords[:3])}」を含める
            - 共感ポイント: 「{', '.join(empathy_points[:2])}」を活用する
            """
        
        if success_case:
            trend_topics = json.loads(success_case[2]) if isinstance(success_case[2], str) else success_case[2]
            buzz_point = success_case[0].split(" - ")[1] if " - " in success_case[0] else success_case[0]
            
            prompt += f"""
            - トレンドトピック: 「{', '.join(trend_topics[:2])}」を含める
            - 注目ポイント: 「{buzz_point}」に関連する内容を含める
            """
        
        prompt += f"""
        台本タイトルと本文を以下の形式で出力してください：
        
        タイトル: [タイトル]
        
        [台本本文]
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"あなたは{style}スタイルの{platform}台本作成の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        
        lines = result.strip().split("\n")
        title = ""
        content = ""
        
        if lines[0].startswith("タイトル:"):
            title = lines[0].replace("タイトル:", "").strip()
            content = "\n".join(lines[2:])  # タイトル行と空行をスキップ
        else:
            title = f"{style}スタイルの{platform}台本 #{i+1}"
            content = result
        
        proposals.append({
            "title": title,
            "content": content
        })
    
    return proposals

def store_script_proposals(client_id, proposals):
    """
    生成された台本提案をデータベースに保存
    
    Args:
        client_id: クライアントID
        proposals: 台本提案のリスト [{title, content}, ...]
        
    Returns:
        list: 保存された提案のID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    proposal_ids = []
    
    for proposal in proposals:
        cursor.execute(
            "INSERT INTO script_proposals (client_id, title, content) VALUES (?, ?, ?)",
            (client_id, proposal["title"], proposal["content"])
        )
        proposal_ids.append(cursor.lastrowid)
    
    conn.commit()
    conn.close()
    
    return proposal_ids
