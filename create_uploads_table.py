"""
create_uploads_table.py - アップロードテーブルを作成するスクリプト

SQLiteデータベースに動画アップロード用のテーブルを作成します。
"""

import os
import sqlite3

DB_PATH = "data.db"

def create_uploads_table():
    """uploads テーブルを作成する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploads'")
    if cursor.fetchone() is None:
        print("uploads テーブルを作成します...")
        
        cursor.execute('''
        CREATE TABLE uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_path TEXT NOT NULL,
            processed_path TEXT,
            client_id INTEGER,
            aspect_ratio TEXT DEFAULT '16:9',
            margin_seconds REAL DEFAULT 0.5,
            duration REAL,
            resolution TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        print("uploads テーブルを作成しました")
    else:
        print("uploads テーブルは既に存在します")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_uploads_table()
