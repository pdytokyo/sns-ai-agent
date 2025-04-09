import os
import datetime
import gspread
import sqlite3
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data.db"

def output_to_google_sheet(category, suggestion):
    try:
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        sheet_name = os.getenv("SHEET_NAME")

        if not credentials_file or not sheet_name:
            print("Error: 環境変数が設定されていません。")
            return False

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(credentials)

        sheet = client.open(sheet_name).sheet1
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        row_data = [category, current_time, suggestion]

        sheet.append_row(row_data, value_input_option='USER_ENTERED')

        print(f"カテゴリ '{category}' の提案をGoogle Sheet '{sheet_name}'に正常に追加しました。")
        return True

    except Exception as e:
        print(f"Google Sheetへの出力中にエラーが発生しました: {e}")
        return False

def get_available_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM research_results")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_research_by_category(category):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM research_results WHERE category = ?", (category,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def generate_suggestion_from_research(category):
    research_data = get_research_by_category(category)
    if not research_data:
        return f"No research data found for category: {category}"
    suggestions = {
        "ビジネス": """
## ビジネスカテゴリのSNS戦略提案
1. ユーザー成功事例の定期的共有
2. 実用的なハウツーコンテンツの提供
3. 社会トレンドとの関連付け
4. コミュニティ参加型キャンペーン
5. マルチプラットフォーム戦略の展開
""",
        "ファッション": """
## ファッションカテゴリのSNS戦略提案
1. ユーザー参加型スタイリングチャレンジ
2. ブランドストーリーと価値観の発信
3. シーズナルトレンド予測コンテンツ
4. コラボレーション企画の戦略的展開
5. リアルライフスタイリングのショーケース
""",
        "スピリチュアル": """
## スピリチュアルカテゴリのSNS戦略提案
1. 日常に取り入れやすい実践法の提供
2. コミュニティ体験の創出
3. 科学的根拠と伝統的知恵の融合
4. パーソナルストーリーの共有
5. 季節やライフイベントに合わせたコンテンツ
"""
    }
    return suggestions.get(category, f"No suggestion template found for category: {category}")

def main():
    categories = get_available_categories()
    if not categories:
        print("データベースにカテゴリがありません。")
        return

    print("=== SNS戦略提案のGoogle Sheets出力 ===\n")
    print("利用可能なカテゴリ:")
    for i, category in enumerate(categories, 1):
        print(f"{i}. {category}")

    try:
        selection = input("\n出力するカテゴリの番号を入力してください: ")
        index = int(selection) - 1
        if index < 0 or index >= len(categories):
            print("無効な選択です。終了します。")
            return

        selected_category = categories[index]
        print(f"\n{selected_category}カテゴリの提案を生成してGoogle Sheetsに出力します...\n")
        suggestion = generate_suggestion_from_research(selected_category)
        success = output_to_google_sheet(selected_category, suggestion)

        if success:
            print("\n✅ 処理が完了しました。Google Sheetsを確認してください。")
        else:
            print("\n❌ Google Sheetsへの出力に失敗しました。")

    except ValueError:
        print("数値を入力してください。終了します。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
