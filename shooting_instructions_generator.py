"""
shooting_instructions_generator.py - 撮影指示書生成モジュール

選択された台本提案に基づいて撮影指示書を自動生成します。
"""

import sqlite3
import os
import sys
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_shooting_instructions(client_id, script_proposal_id):
    """
    選択された台本提案から撮影指示書を生成
    
    Args:
        client_id: クライアントID
        script_proposal_id: 選択された台本提案ID
        
    Returns:
        str: 生成された撮影指示書の内容
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT title, content FROM script_proposals WHERE id = ? AND client_id = ?",
        (script_proposal_id, client_id)
    )
    proposal = cursor.fetchone()
    
    if not proposal:
        conn.close()
        raise ValueError("台本提案が見つかりません")
    
    title = proposal[0]
    script_content = proposal[1]
    
    cursor.execute(
        "SELECT platforms FROM selections WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
        (client_id,)
    )
    selection = cursor.fetchone()
    platform = selection[0].split(",")[0] if selection else "YouTube"
    
    conn.close()
    
    prompt = f"""
    以下の{platform}用台本に基づいて、撮影指示書を作成してください。
    
    【台本タイトル】
    {title}
    
    【台本内容】
    {script_content}
    
    撮影指示書には以下の内容を含めてください：
    1. 必要な撮影機材
    2. 撮影場所の設定と準備
    3. 照明と音声の設定
    4. 各シーンの具体的な撮影方法
    5. 演出のポイント
    6. タイムライン（撮影の時間配分）
    7. 特殊効果や編集上の注意点
    
    実際に撮影できる具体的な指示にしてください。
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは映像ディレクターで、SNS動画の撮影指示書作成の専門家です。"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000,
        temperature=0.7
    )
    
    instructions = response.choices[0].message.content
    
    return instructions

def store_shooting_instructions(client_id, script_proposal_id, instructions):
    """
    生成された撮影指示書をデータベースに保存
    
    Args:
        client_id: クライアントID
        script_proposal_id: 台本提案ID
        instructions: 撮影指示書の内容
        
    Returns:
        int: 保存された撮影指示書のID
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO shooting_instructions (client_id, script_proposal_id, content) VALUES (?, ?, ?)",
        (client_id, script_proposal_id, instructions)
    )
    
    instruction_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return instruction_id
