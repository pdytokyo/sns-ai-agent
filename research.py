from openai import OpenAI
from dotenv import load_dotenv
import os
import sqlite3

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def perform_research(prompt, category):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはSNSの成功事例を専門にリサーチするAIアシスタントです。"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )

    result_text = response.choices[0].message.content

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS research_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            result TEXT
        )
    ''')
    c.execute("INSERT INTO research_results (category, result) VALUES (?, ?)", (category, result_text))
    conn.commit()
    conn.close()
    print(f"保存完了: {category}")

# テスト実行用
perform_research("ビジネス系SNSの成功事例を1件教えてください。", "ビジネス")
