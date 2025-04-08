import sqlite3
import os
from openai import OpenAI
from typing import List, Dict

# SQLite DB接続
def get_db_connection():
    return sqlite3.connect('data.db')

# OpenAI APIクライアント設定
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# カテゴリー別リサーチ取得
def get_research_by_category(category: str) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT title, reason, url, platform FROM research_results WHERE category = ?",
        (category,)
    )

    research_results = cursor.fetchall()
    conn.close()

    return [{"title": row[0], "reason": row[1], "url": row[2], "platform": row[3]} for row in research_results]

# GPT-4oでAI提案生成
def generate_suggestions(category: str, research_results: List[Dict]) -> str:
    prompt = (
        f"以下は「{category}」カテゴリーにおけるSNS成功事例のリサーチ結果です。\n"
        "これらを元に、このカテゴリーでのSNS成功戦略について具体的なアクションプランを提案してください。\n\n"
    )

    for i, result in enumerate(research_results, 1):
        prompt += (
            f"{i}. タイトル: {result['title']}\n"
            f"   成功理由: {result['reason']}\n"
            f"   プラットフォーム: {result['platform']}\n"
            f"   URL: {result['url']}\n\n"
        )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600
    )

    return response.choices[0].message.content

# メイン処理
def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT category FROM research_results")
    available_categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    print("\n===== AI SNS Strategy Suggestion Tool =====\n")
    print("Available categories:")

    for i, category in enumerate(available_categories, 1):
        print(f"{i}. {category}")

    choice = input("\nEnter the number of your chosen category (or type the category name): ")

    try:
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(available_categories):
                category = available_categories[choice_num - 1]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(available_categories)}.")
                return
        elif choice in available_categories:
            category = choice
        else:
            print(f"Invalid choice. Please enter a number between 1 and {len(available_categories)} or a valid category name.")
            return
    except ValueError:
        print("Invalid input. Please try again.")
        return

    print(f"\nFetching research data for category: {category}...")

    research_results = get_research_by_category(category)

    if not research_results:
        print(f"No research results found for category: {category}")
        return

    print(f"Found {len(research_results)} research entries.")
    print("\nGenerating suggestions based on research data...")

    try:
        suggestions = generate_suggestions(category, research_results)

        print("\n===== Generated Suggestions =====\n")
        print(suggestions)

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTo set your OpenAI API key, run the following command in your terminal:")
        print("export OPENAI_API_KEY='your-api-key'")

if __name__ == "__main__":
    main()
