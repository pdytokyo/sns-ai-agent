"""
alter_uploads_table.py - アップロードテーブルのスキーマを変更するスクリプト

SQLiteデータベースのuploadsテーブルに必要なカラムを追加します。
"""

import sqlite3

DB_PATH = "data.db"

def alter_uploads_table():
    """uploads テーブルにカラムを追加する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 現在のスキーマを確認
    cursor.execute("PRAGMA table_info(uploads)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"現在のカラム: {columns}")
    
    # original_path カラムが存在しない場合は追加
    if "original_path" not in columns:
        print("original_path カラムを追加します...")
        cursor.execute("ALTER TABLE uploads ADD COLUMN original_path TEXT")
        print("original_path カラムを追加しました")
    
    # processed_path カラムが存在しない場合は追加
    if "processed_path" not in columns:
        print("processed_path カラムを追加します...")
        cursor.execute("ALTER TABLE uploads ADD COLUMN processed_path TEXT")
        print("processed_path カラムを追加しました")
    
    # duration カラムが存在しない場合は追加
    if "duration" not in columns:
        print("duration カラムを追加します...")
        cursor.execute("ALTER TABLE uploads ADD COLUMN duration REAL")
        print("duration カラムを追加しました")
    
    # resolution カラムが存在しない場合は追加
    if "resolution" not in columns:
        print("resolution カラムを追加します...")
        cursor.execute("ALTER TABLE uploads ADD COLUMN resolution TEXT")
        print("resolution カラムを追加しました")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_uploads_table()
