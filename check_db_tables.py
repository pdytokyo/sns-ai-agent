"""
check_db_tables.py - データベーステーブルの存在を確認するスクリプト

SQLiteデータベースに必要なテーブルが存在するか確認します。
"""

import sqlite3

DB_PATH = "data.db"

def check_tables():
    """データベースのテーブルを確認する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("データベース内のテーブル一覧:")
    for table in tables:
        print(f"- {table[0]}")
    
    required_tables = ["uploads", "edit_commands"]
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            print(f"{table} テーブルは存在します")
        else:
            print(f"{table} テーブルは存在しません")
    
    conn.close()

if __name__ == "__main__":
    check_tables()
