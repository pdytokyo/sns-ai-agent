"""
check_file_permissions.py - ファイル権限を確認するスクリプト

uploaded_videosディレクトリの権限とアクセス状態を確認します。
"""

import os
import sys

def check_directory_permissions():
    """ディレクトリの権限を確認する"""
    directory = "uploaded_videos"
    
    if not os.path.exists(directory):
        print(f"{directory} ディレクトリは存在しません。作成します。")
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"{directory} ディレクトリを作成しました。")
        except Exception as e:
            print(f"{directory} ディレクトリの作成に失敗しました: {e}")
            return False
    
    try:
        test_filename = os.path.join(directory, "test_permissions.txt")
        with open(test_filename, "w") as f:
            f.write("テスト")
        print(f"ファイル書き込みテスト成功: {test_filename}")
        
        with open(test_filename, "r") as f:
            content = f.read()
        print(f"ファイル読み込みテスト成功: {content}")
        
        os.remove(test_filename)
        print(f"ファイル削除テスト成功: {test_filename}")
        
        return True
    except Exception as e:
        print(f"ファイルアクセステストに失敗しました: {e}")
        return False

if __name__ == "__main__":
    if check_directory_permissions():
        print("ディレクトリの権限チェック: OK")
        sys.exit(0)
    else:
        print("ディレクトリの権限チェック: 失敗")
        sys.exit(1)
