import os
import datetime
import gspread
import sqlite3
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data.db"

def output_to_google_sheet(category, suggestion):
    """
    Output the generated SNS strategy suggestion to a Google Sheet
    
    Args:
        category (str): The category of the suggestion (e.g., "ビジネス", "健康", etc.)
        suggestion (str): The generated suggestion content
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        sheet_name = os.getenv("SHEET_NAME")
        
        if not credentials_file or not sheet_name:
            print("Error: Missing environment variables for Google Sheets API")
            print("Please set GOOGLE_CREDENTIALS_FILE and SHEET_NAME in your .env file")
            return False
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(credentials)
        
        sheet = client.open(sheet_name).sheet1
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        row_data = [category, current_time, suggestion]
        
        sheet.append_row(row_data)
        
        print(f"Successfully added suggestion for category '{category}' to Google Sheet '{sheet_name}'")
        return True
    
    except Exception as e:
        print(f"Error outputting to Google Sheet: {e}")
        return False

def get_available_categories():
    """Get available categories from the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM research_results")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_research_by_category(category):
    """Get research results for a specific category"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM research_results WHERE category = ?", 
        (category,)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def generate_suggestion_from_research(category):
    """
    Generate a suggestion based on research data for a specific category
    
    This is a placeholder function. In a real application, this would call
    the OpenAI API or use another method to generate suggestions.
    
    Args:
        category (str): The category to generate suggestions for
        
    Returns:
        str: The generated suggestion
    """
    research_data = get_research_by_category(category)
    
    if not research_data:
        return f"No research data found for category: {category}"
    
    suggestions = {
        "ビジネス": """

1. **ユーザー成功事例の定期的共有**
   - 実際の顧客の声や成功体験を定期的に共有し、信頼性を構築する
   - ビフォーアフター形式で具体的な成果を視覚的に示す

2. **実用的なハウツーコンテンツの提供**
   - 業界知識や専門スキルを短く分かりやすいコンテンツで提供
   - 問題解決型のコンテンツで即時的な価値を提供する

3. **社会トレンドとの関連付け**
   - 現在の社会課題や流行と自社製品・サービスを結びつける
   - タイムリーな話題に対する独自の視点や解決策を提示

4. **コミュニティ参加型キャンペーン**
   - ユーザーが参加できるチャレンジやコンテストを定期的に開催
   - ユーザー生成コンテンツを活用した拡散性の高い企画設計

5. **マルチプラットフォーム戦略の展開**
   - 各SNSプラットフォームの特性に合わせたコンテンツ最適化
   - LinkedIn向け専門的コンテンツ、Instagram向け視覚的コンテンツなど
""",
        "ファッション": """

1. **ユーザー参加型スタイリングチャレンジ**
   - 特定のハッシュタグを使ったスタイリングコンテストの定期開催
   - 優れた投稿の公式アカウントでのリポストによる参加意欲向上

2. **ブランドストーリーと価値観の発信**
   - サステナビリティや社会貢献など、ブランドの価値観を伝えるコンテンツ
   - 製品背景やデザイナーのインスピレーションを共有

3. **シーズナルトレンド予測コンテンツ**
   - 次シーズンのトレンド予測や取り入れ方の提案
   - 季節の変わり目に合わせたワードローブ更新アドバイス

4. **コラボレーション企画の戦略的展開**
   - 異なる文化や業界とのコラボレーションによる話題性創出
   - インフルエンサーとの限定コレクション開発と発表

5. **リアルライフスタイリングのショーケース**
   - 多様なボディタイプやライフスタイルに合わせたスタイリング提案
   - 「1アイテム・複数スタイリング」などの実用的コンテンツ
""",
        "スピリチュアル": """

1. **日常に取り入れやすい実践法の提供**
   - 5分間の朝の瞑想など、忙しい現代人でも実践できるシンプルな方法
   - ステップバイステップで視覚的に説明する初心者向けガイド

2. **コミュニティ体験の創出**
   - オンラインでの集団瞑想やヨガセッションのライブ配信
   - 参加者同士が体験をシェアできる仕組みづくり

3. **科学的根拠と伝統的知恵の融合**
   - 最新の脳科学研究とスピリチュアルプラクティスの関連性の解説
   - 古代の知恵を現代生活に適用する方法の提案

4. **パーソナルストーリーの共有**
   - 実践者の人生変化や成長ストーリーの定期的な紹介
   - 有名人や影響力のある実践者のインタビューシリーズ

5. **季節やライフイベントに合わせたコンテンツ**
   - 新年、季節の変わり目、満月など時期に合わせた特別プラクティス
   - 人生の転機（就職、結婚、育児など）に対応したマインドフルネス実践法
""",
        "健康": """

1. **専門家による信頼性の高い健康情報の提供**
   - 医師や専門家による最新の健康情報を分かりやすく解説
   - 健康神話の検証と科学的根拠に基づいた情報発信

2. **短時間で実践できる健康習慣の提案**
   - 5分間のエクササイズや簡単な健康レシピなど、取り入れやすいコンテンツ
   - 日常生活に組み込める具体的な健康習慣のステップバイステップガイド

3. **ユーザー成功体験の共有プログラム**
   - 実際のユーザーの健康改善ストーリーをビフォーアフター形式で紹介
   - コミュニティメンバーの成功体験を定期的に特集するシリーズ企画

4. **視覚的に分かりやすい健康情報グラフィック**
   - 複雑な健康情報を図解やインフォグラフィックで視覚化
   - 体の仕組みや健康プロセスを分かりやすいアニメーションで説明

5. **季節・時事に合わせた健康アドバイス**
   - 季節の変わり目や特定の健康月間に合わせたタイムリーなコンテンツ
   - 流行している健康問題に対する予防法や対処法の提案
""",
        "美容": """

1. **成分教育と透明性重視のコンテンツ**
   - 化粧品成分の役割と効果を分かりやすく解説するシリーズ
   - 製品開発プロセスの透明性を高める舞台裏コンテンツ

2. **多様性を重視したインクルーシブな美容表現**
   - 様々な肌トーン、年齢、性別を代表するモデルの起用
   - 多様な美の形を称える共感型メッセージの発信

3. **ユーザー参加型の美容チャレンジ企画**
   - 特定のメイクテクニックやスキンケアルーティンのチャレンジ企画
   - ユーザー投稿のリポストによるコミュニティ感の醸成

4. **実用的なビフォーアフターコンテンツ**
   - 製品使用前後の効果を正直に示す比較コンテンツ
   - 実際のユーザーによる製品レビューと使用感の共有

5. **ライフスタイルと美容の融合コンテンツ**
   - 季節やライフイベントに合わせた美容アドバイス
   - 内面の健康と外見の美しさを結びつけるホリスティックアプローチ
""",
        "教育": """

1. **複雑な概念の視覚的解説シリーズ**
   - 難解な学術概念をアニメーションや図解で分かりやすく説明
   - 短時間で理解できる「1分間レッスン」形式のマイクロラーニング

2. **インタラクティブな学習チャレンジ**
   - フォロワーが参加できる知識クイズや問題解決チャレンジ
   - 学習成果を共有できるハッシュタグキャンペーン

3. **実践者の成功ストーリー共有**
   - 学習者の実際の成功体験や成長過程を定期的に紹介
   - 「学びが人生をどう変えたか」をテーマにしたインタビューシリーズ

4. **無料教育リソースの戦略的提供**
   - 高品質な学習コンテンツの一部を無料で提供するフリーミアムモデル
   - 特定の学習トピックに関する完全無料のミニコース

5. **学習コミュニティの構築と育成**
   - 学習者同士が知識を共有し合える仕組みづくり
   - メンター・メンティー関係を促進するコミュニティプログラム
"""
    }
    
    return suggestions.get(category, f"No suggestion template found for category: {category}")

def main():
    """
    Main function to demonstrate the usage of the output_to_google_sheet function
    """
    categories = get_available_categories()
    
    if not categories:
        print("No categories found in the database. Please run the research collection script first.")
        return
    
    print("=== SNS戦略提案のGoogle Sheets出力 ===\n")
    print("利用可能なカテゴリ:")
    for i, category in enumerate(categories, 1):
        print(f"{i}. {category}")
    
    try:
        selection = input("\n出力するカテゴリの番号を入力してください: ")
        index = int(selection) - 1
        
        if index < 0 or index >= len(categories):
            print("無効な選択です。プログラムを終了します。")
            return
        
        selected_category = categories[index]
        print(f"\n{selected_category}カテゴリの提案を生成してGoogle Sheetsに出力します...\n")
        
        suggestion = generate_suggestion_from_research(selected_category)
        
        success = output_to_google_sheet(selected_category, suggestion)
        
        if success:
            print("\n処理が完了しました。Google Sheetsを確認してください。")
        else:
            print("\nGoogle Sheetsへの出力に失敗しました。環境変数の設定を確認してください。")
    
    except ValueError:
        print("数値を入力してください。プログラムを終了します。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
