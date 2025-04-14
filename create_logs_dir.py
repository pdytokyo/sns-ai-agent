"""
create_logs_dir.py - ログディレクトリを作成するスクリプト

logsディレクトリを作成し、ログファイルの書き込み権限を確認します。
"""

import os
import sys

def create_logs_directory():
    """logsディレクトリを作成し、権限を確認する"""
    logs_dir = "logs"
    
    if not os.path.exists(logs_dir):
        print(f"{logs_dir} ディレクトリは存在しません。作成します。")
        try:
            os.makedirs(logs_dir, exist_ok=True)
            print(f"{logs_dir} ディレクトリを作成しました。")
        except Exception as e:
            print(f"{logs_dir} ディレクトリの作成に失敗しました: {e}")
            return False
    
    try:
        test_filename = os.path.join(logs_dir, "test_log.txt")
        with open(test_filename, "w") as f:
            f.write("テストログ")
        print(f"ログファイル書き込みテスト成功: {test_filename}")
        
        with open(test_filename, "r") as f:
            content = f.read()
        print(f"ログファイル読み込みテスト成功: {content}")
        
        os.remove(test_filename)
        print(f"ログファイル削除テスト成功: {test_filename}")
        
        return True
    except Exception as e:
        print(f"ログファイルアクセステストに失敗しました: {e}")
        return False

if __name__ == "__main__":
    if create_logs_directory():
        print("ログディレクトリの権限チェック: OK")
        sys.exit(0)
    else:
        print("ログディレクトリの権限チェック: 失敗")
        sys.exit(1)
