import os
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data.db"

def get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return api_key

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

def generate_suggestions(category, research_results):
    try:
        client = OpenAI(api_key=get_api_key())

        prompt = f"""
        以下の「{category}」カテゴリで成功したSNS投稿のデータを参考に、
        効果的なSNSコンテンツを作るための戦略的な提案を5つ作成してください。

        【成功事例のデータ】：
        """

        for item in research_results:
            prompt += f"""
            - タイトル: {item['title']}
              成功理由: {item['reason']}
              プラットフォーム: {item['platform']}
            """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたはSNSマーケティングの専門家です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"エラー発生: {e}")
        return get_hardcoded_suggestions(category)

def get_hardcoded_suggestions(category):
    suggestions = {
        "ビジネス": "ビジネスカテゴリのデフォルト提案...",
        "ファッション": "ファッションカテゴリのデフォルト提案...",
        "スピリチュアル": "スピリチュアルカテゴリのデフォルト提案..."
    }
    return suggestions.get(category, "該当カテゴリの提案がありません。")

def main():
    print("=== SNS AI提案ジェネレーター ===\n")

    categories = get_available_categories()
    if not categories:
        print("利用可能なカテゴリがありません。データを確認してください。")
        return

    print("利用可能なカテゴリ:")
    for i, category in enumerate(categories, 1):
        print(f"{i}. {category}")

    selection = input("\n分析するカテゴリの番号を入力してください: ")
    try:
        index = int(selection) - 1
        selected_category = categories[index]
    except:
        print("無効な選択です。")
        return

    print(f"\n{selected_category}カテゴリの分析を開始します...\n")

    research_results = get_research_by_category(selected_category)
    if not research_results:
        print(f"{selected_category}カテゴリの研究データがありません。")
        return

    suggestions = generate_suggestions(selected_category, research_results)

    print("\n=== AI生成提案 ===\n")
    print(suggestions)

if __name__ == "__main__":
    main()
