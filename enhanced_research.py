import os
import sqlite3
import json
import time
import random
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data.db"

def get_api_key():
    """Get OpenAI API key from environment variables"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found in environment variables. Using mock data.")
    return api_key

def create_enhanced_tables():
    """Create enhanced tables for storing detailed research data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS success_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        industry TEXT,
        brand_name TEXT,
        platform TEXT,
        description TEXT,
        engagement_metrics TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS account_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        success_case_id INTEGER,
        account_name TEXT,
        profile_text TEXT,
        target_age TEXT,
        target_gender TEXT,
        target_interests TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (success_case_id) REFERENCES success_cases (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS high_engagement_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        success_case_id INTEGER,
        post_type TEXT,
        structure TEXT,
        script TEXT,
        intro_char_count INTEGER,
        main_char_count INTEGER,
        conclusion_char_count INTEGER,
        total_duration TEXT,
        key_elements TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (success_case_id) REFERENCES success_cases (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Enhanced tables created successfully")

def research_success_cases(industry, platform, num_cases=5):
    """
    Research success cases for a specific industry and platform
    
    Args:
        industry (str): The industry to research
        platform (str): The platform to research (YouTube, Instagram, TikTok)
        num_cases (int): Number of cases to generate
        
    Returns:
        dict: Success cases data
    """
    api_key = get_api_key()
    
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
            あなたはSNSマーケティングの専門家です。{industry}業界の{platform}での成功事例を{num_cases}件調査してください。
            
            各事例について、以下の情報を含めてください：
            1. ブランド名
            2. 詳細な説明（どのような戦略を使用したか、なぜ成功したか）
            3. エンゲージメント指標（フォロワー数、いいね数、シェア数など）
            
            JSON形式で返してください。
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはSNSマーケティングの専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return generate_mock_success_cases(industry, platform, num_cases)
    else:
        return generate_mock_success_cases(industry, platform, num_cases)

def research_account_profile(brand_name, platform):
    """
    Research account profiles for a specific brand
    
    Args:
        brand_name (str): The brand name to research
        platform (str): The platform to research (YouTube, Instagram, TikTok)
        
    Returns:
        dict: Account profile information
    """
    api_key = get_api_key()
    
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
            あなたはSNSマーケティングの専門家です。{brand_name}の{platform}アカウントについて詳細に調査してください。
            
            以下の情報を含めてください：
            1. アカウント名
            2. プロフィール文（実際の文章）
            3. ターゲット層の属性：
               - 年齢層
               - 性別
               - 関心事/興味
            
            JSON形式で返してください。
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはSNSマーケティングの専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return generate_mock_account_profile(brand_name, platform)
    else:
        return generate_mock_account_profile(brand_name, platform)

def research_high_engagement_post(brand_name, platform):
    """
    Research high engagement posts for a specific brand
    
    Args:
        brand_name (str): The brand name to research
        platform (str): The platform to research (YouTube, Instagram, TikTok)
        
    Returns:
        dict: High engagement post information
    """
    api_key = get_api_key()
    
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
            あなたはSNSマーケティングの専門家です。{brand_name}の{platform}での高エンゲージメントを獲得した投稿（動画）について詳細に調査してください。
            
            以下の情報を含めてください：
            1. 投稿タイプ（通常投稿、リール、ストーリーなど）
            2. 構成（導入、本編、結論などの構成）
            3. 台本（実際の台本または内容の詳細な説明）
            4. セクションごとの文字数：
               - 導入部分の文字数
               - 本編の文字数
               - 結論部分の文字数
            5. 総再生時間
            6. 特徴的な要素（ハッシュタグ、音楽、エフェクトなど）
            
            JSON形式で返してください。
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたはSNSマーケティングの専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return generate_mock_high_engagement_post(brand_name, platform)
    else:
        return generate_mock_high_engagement_post(brand_name, platform)

def generate_mock_success_cases(industry, platform, num_cases=5):
    """Generate mock success cases when API is not available"""
    platforms = {
        "YouTube": {
            "metrics": ["登録者数", "総再生回数", "平均視聴時間", "コメント数"],
            "values": [
                lambda: f"{random.randint(10, 500)}万人",
                lambda: f"{random.randint(1000, 5000)}万回",
                lambda: f"{random.randint(3, 15)}分",
                lambda: f"平均{random.randint(500, 10000)}件"
            ]
        },
        "Instagram": {
            "metrics": ["フォロワー数", "平均いいね数", "保存数", "リーチ数"],
            "values": [
                lambda: f"{random.randint(10, 300)}万人",
                lambda: f"{random.randint(1, 50)}万件",
                lambda: f"投稿あたり{random.randint(5000, 50000)}回",
                lambda: f"投稿あたり{random.randint(50, 500)}万人"
            ]
        },
        "TikTok": {
            "metrics": ["フォロワー数", "総いいね数", "平均視聴完了率", "シェア数"],
            "values": [
                lambda: f"{random.randint(10, 500)}万人",
                lambda: f"{random.randint(100, 2000)}万件",
                lambda: f"{random.randint(40, 80)}%",
                lambda: f"動画あたり{random.randint(5000, 100000)}回"
            ]
        }
    }
    
    industries = {
        "美容": ["SHISEIDO", "SK-II", "FANCL", "Kao", "KOSE", "DHC", "POLA", "ORBIS", "ALBION", "THREE"],
        "ファッション": ["UNIQLO", "GU", "ZARA", "H&M", "BEAMS", "UNITED ARROWS", "SHIPS", "nano universe", "URBAN RESEARCH", "BEAUTY&YOUTH"],
        "食品": ["日清食品", "カルビー", "明治", "森永製菓", "江崎グリコ", "キリン", "サントリー", "アサヒ", "コカ・コーラ", "ネスレ"],
        "テクノロジー": ["Apple", "Samsung", "Sony", "Panasonic", "SHARP", "Microsoft", "Google", "Amazon", "Meta", "LINE"],
        "エンターテイメント": ["Netflix", "Disney", "Universal Studios", "Sony Music", "Avex", "Nintendo", "BANDAI NAMCO", "SQUARE ENIX", "CAPCOM", "SEGA"]
    }
    
    brand_list = industries.get(industry, industries["テクノロジー"])
    selected_brands = random.sample(brand_list, min(num_cases, len(brand_list)))
    
    platform_metrics = platforms.get(platform, platforms["Instagram"])
    
    cases = []
    for brand in selected_brands:
        metrics = {}
        for i, metric in enumerate(platform_metrics["metrics"]):
            metrics[metric] = platform_metrics["values"][i]()
        
        strategy_elements = [
            f"ユーザー参加型キャンペーン「#{brand}チャレンジ」の実施",
            f"インフルエンサーとのコラボレーションコンテンツ",
            f"ユーザー生成コンテンツの積極的な活用",
            f"ブランドストーリーを伝える感情的なコンテンツ",
            f"トレンドに即した定期的な投稿"
        ]
        
        success_factors = [
            "一貫したブランドボイスとビジュアルアイデンティティ",
            "ターゲットオーディエンスの明確な理解と対応",
            "高品質でオリジナリティのあるコンテンツ制作",
            "ユーザーエンゲージメントを促進する双方向のコミュニケーション",
            "データ分析に基づいた投稿最適化"
        ]
        
        case = {
            "brand_name": brand,
            "description": f"{brand}は{platform}での戦略として、{random.choice(strategy_elements)}を中心に展開。{random.choice(success_factors)}が成功の鍵となり、{random.choice(success_factors)}によって他ブランドとの差別化に成功しました。特に{random.choice(strategy_elements)}が高いエンゲージメントを獲得し、ブランド認知度の向上に貢献しています。",
            "engagement_metrics": metrics
        }
        cases.append(case)
    
    result = {
        "success_cases": cases
    }
    
    return result

def generate_mock_account_profile(brand_name, platform):
    """Generate mock account profile when API is not available"""
    name_variations = [
        f"{brand_name}",
        f"{brand_name}_official",
        f"{brand_name}_japan",
        f"official_{brand_name}",
        f"{brand_name}.official"
    ]
    
    profile_templates = [
        f"{brand_name}の公式{platform}アカウントです。最新の製品情報や限定コンテンツをお届けします。 #公式",
        f"【公式】{brand_name} | 新商品情報やキャンペーン情報をいち早くお届け！お問い合わせはDMまで。",
        f"{brand_name}公式アカウント✓ 毎日更新中！最新トレンドやイベント情報を発信しています。",
        f"Welcome to the official {brand_name} account! 公式アカウントからの最新情報をチェックしてください。",
        f"{brand_name} | 公式アカウント | 新商品やキャンペーン情報、限定コンテンツを配信中！"
    ]
    
    age_ranges = [
        "10代後半〜20代前半",
        "20代〜30代",
        "30代〜40代",
        "20代〜40代",
        "全年齢層（特に20代〜30代）"
    ]
    
    genders = [
        "女性中心（約70%）",
        "男性中心（約65%）",
        "男女ほぼ同率",
        "女性がメインターゲット",
        "男性がメインターゲット"
    ]
    
    interest_categories = [
        "ファッション、トレンド、ライフスタイル",
        "テクノロジー、ガジェット、イノベーション",
        "美容、健康、ウェルネス",
        "旅行、アウトドア、アドベンチャー",
        "料理、グルメ、フードカルチャー"
    ]
    
    result = {
        "account_profile": {
            "account_name": random.choice(name_variations),
            "profile_text": random.choice(profile_templates),
            "target_audience": {
                "age": random.choice(age_ranges),
                "gender": random.choice(genders),
                "interests": random.choice(interest_categories)
            }
        }
    }
    
    return result

def generate_mock_high_engagement_post(brand_name, platform):
    """Generate mock high engagement post when API is not available"""
    post_types = {
        "YouTube": ["ブランド紹介動画", "製品レビュー", "ハウツー動画", "ブランドストーリー", "ユーザー体験動画"],
        "Instagram": ["フィード投稿", "リール", "ストーリーズ", "IGTV", "カルーセル投稿"],
        "TikTok": ["チャレンジ動画", "トレンド参加", "製品紹介", "ハウツー動画", "ユーモア動画"]
    }
    
    structure_templates = [
        "注目を集めるフック → 問題提起 → 解決策の提示 → 製品紹介 → 行動喚起",
        "インパクトのある導入 → ストーリーテリング → 製品の利点紹介 → 使用例 → まとめ",
        "質問形式の導入 → 共感ポイント → 製品紹介 → 使用方法 → 結果の提示",
        "驚きの事実 → 背景説明 → 製品の特徴 → 実際の使用シーン → 感想と行動喚起",
        "ユーザーの声 → 問題点の共有 → 解決策としての製品 → 使用後の変化 → 購入方法"
    ]
    
    script_templates = [
        f"「こんにちは！今日は{brand_name}の新商品をご紹介します。多くの方が抱える[問題]。でも、この製品ならその悩みを解決できるんです。実際に使ってみると…（製品デモ）。いかがでしたか？公式サイトからチェックしてみてください！」",
        f"「[驚きの事実]をご存知ですか？実は多くの人が気づいていないんです。{brand_name}では、この問題に着目して[製品名]を開発しました。特徴は[特徴1]、[特徴2]、そして[特徴3]です。ぜひお試しください！」",
        f"「みなさんこんにちは！今回は{brand_name}の人気商品[製品名]の使い方をご紹介します。まず[ステップ1]、次に[ステップ2]、最後に[ステップ3]。これだけで驚くほどの効果が得られます。ぜひコメントで感想を教えてください！」",
        f"「[ユーザーの声]というコメントをよくいただきます。{brand_name}では、そんなお悩みを解決するために[製品名]を開発しました。実際に使うとこんな感じです（デモ）。今なら特別キャンペーン中なので、プロフィールのリンクからチェックしてみてください！」",
        f"「こんにちは、{brand_name}です！今日は裏側をお見せします。実は[意外な事実]なんです。この[製品名]がどのように作られているか、ご覧ください。品質へのこだわりが詰まっています。ぜひ一度お試しください！」"
    ]
    
    intro_chars = random.randint(100, 300)
    main_chars = random.randint(400, 1200)
    conclusion_chars = random.randint(80, 200)
    
    durations = {
        "YouTube": f"{random.randint(3, 15)}分{random.randint(10, 59)}秒",
        "Instagram": f"{random.randint(30, 90)}秒",
        "TikTok": f"{random.randint(15, 60)}秒"
    }
    
    key_elements = {
        "YouTube": [
            "サムネイルの工夫（テキストオーバーレイ、表情のクローズアップ）",
            "冒頭10秒での視聴者の興味を引くフック",
            "テロップやグラフィックの効果的な使用",
            "BGMの適切な選択",
            "エンドカードでの次の動画への誘導"
        ],
        "Instagram": [
            "鮮やかな色彩とコントラスト",
            "ブランドカラーの一貫した使用",
            "効果的なハッシュタグ（#{}Challenge など）",
            "トレンド音楽の活用",
            "インタラクティブな要素（投票、質問ボックスなど）"
        ],
        "TikTok": [
            "トレンド音楽やサウンドの活用",
            "テキストオーバーレイの効果的な使用",
            "冒頭3秒での注目を集める工夫",
            "シンプルで再現しやすいチャレンジ形式",
            "ユーモアや意外性の要素"
        ]
    }
    
    platform_post_types = post_types.get(platform, post_types["Instagram"])
    platform_duration = durations.get(platform, "60秒")
    platform_key_elements = key_elements.get(platform, key_elements["Instagram"])
    
    result = {
        "high_engagement_post": {
            "post_type": random.choice(platform_post_types),
            "structure": random.choice(structure_templates),
            "script": random.choice(script_templates),
            "character_counts": {
                "intro": intro_chars,
                "main": main_chars,
                "conclusion": conclusion_chars,
                "total": intro_chars + main_chars + conclusion_chars
            },
            "duration": platform_duration,
            "key_elements": random.sample(platform_key_elements, 3)
        }
    }
    
    return result

def store_success_case(industry, brand_name, platform, description, engagement_metrics):
    """
    Store success case in the database
    
    Args:
        industry (str): The industry of the success case
        brand_name (str): The brand name
        platform (str): The platform (YouTube, Instagram, TikTok)
        description (str): Description of the success case
        engagement_metrics (dict): Engagement metrics as a dictionary
        
    Returns:
        int: ID of the inserted success case
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    engagement_metrics_json = json.dumps(engagement_metrics, ensure_ascii=False)
    
    cursor.execute(
        "INSERT INTO success_cases (industry, brand_name, platform, description, engagement_metrics) VALUES (?, ?, ?, ?, ?)",
        (industry, brand_name, platform, description, engagement_metrics_json)
    )
    
    success_case_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return success_case_id

def store_account_profile(success_case_id, account_name, profile_text, target_age, target_gender, target_interests):
    """
    Store account profile in the database
    
    Args:
        success_case_id (int): ID of the success case
        account_name (str): Account name
        profile_text (str): Profile text
        target_age (str): Target age range
        target_gender (str): Target gender
        target_interests (str): Target interests
        
    Returns:
        int: ID of the inserted account profile
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO account_profiles (success_case_id, account_name, profile_text, target_age, target_gender, target_interests) VALUES (?, ?, ?, ?, ?, ?)",
        (success_case_id, account_name, profile_text, target_age, target_gender, target_interests)
    )
    
    account_profile_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return account_profile_id

def store_high_engagement_post(success_case_id, post_type, structure, script, intro_char_count, main_char_count, conclusion_char_count, total_duration, key_elements):
    """
    Store high engagement post in the database
    
    Args:
        success_case_id (int): ID of the success case
        post_type (str): Type of post
        structure (str): Structure of the post
        script (str): Script of the post
        intro_char_count (int): Character count of the introduction
        main_char_count (int): Character count of the main content
        conclusion_char_count (int): Character count of the conclusion
        total_duration (str): Total duration of the post
        key_elements (list): Key elements of the post
        
    Returns:
        int: ID of the inserted high engagement post
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    key_elements_json = json.dumps(key_elements, ensure_ascii=False)
    
    cursor.execute(
        "INSERT INTO high_engagement_posts (success_case_id, post_type, structure, script, intro_char_count, main_char_count, conclusion_char_count, total_duration, key_elements) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (success_case_id, post_type, structure, script, intro_char_count, main_char_count, conclusion_char_count, total_duration, key_elements_json)
    )
    
    high_engagement_post_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return high_engagement_post_id

def process_research_data(industry, platform, num_cases=5):
    """
    Process research data for a specific industry and platform
    
    Args:
        industry (str): The industry to research
        platform (str): The platform to research (YouTube, Instagram, TikTok)
        num_cases (int): Number of cases to generate
        
    Returns:
        list: List of success case IDs
    """
    print(f"Researching {industry} industry on {platform}...")
    
    success_cases_data = research_success_cases(industry, platform, num_cases)
    
    success_case_ids = []
    
    if "success_cases" in success_cases_data:
        for case in success_cases_data["success_cases"]:
            brand_name = case.get("brand_name", "Unknown Brand")
            description = case.get("description", "")
            engagement_metrics = case.get("engagement_metrics", {})
            
            success_case_id = store_success_case(industry, brand_name, platform, description, engagement_metrics)
            success_case_ids.append(success_case_id)
            
            print(f"Stored success case: {brand_name}")
            
            account_profile_data = research_account_profile(brand_name, platform)
            
            if "account_profile" in account_profile_data:
                profile = account_profile_data["account_profile"]
                account_name = profile.get("account_name", brand_name)
                profile_text = profile.get("profile_text", "")
                
                target_audience = profile.get("target_audience", {})
                target_age = target_audience.get("age", "")
                target_gender = target_audience.get("gender", "")
                target_interests = target_audience.get("interests", "")
                
                store_account_profile(success_case_id, account_name, profile_text, target_age, target_gender, target_interests)
                
                print(f"Stored account profile for: {brand_name}")
            
            high_engagement_post_data = research_high_engagement_post(brand_name, platform)
            
            if "high_engagement_post" in high_engagement_post_data:
                post = high_engagement_post_data["high_engagement_post"]
                post_type = post.get("post_type", "")
                structure = post.get("structure", "")
                script = post.get("script", "")
                
                character_counts = post.get("character_counts", {})
                intro_char_count = character_counts.get("intro", 0)
                main_char_count = character_counts.get("main", 0)
                conclusion_char_count = character_counts.get("conclusion", 0)
                
                total_duration = post.get("duration", "")
                key_elements = post.get("key_elements", [])
                
                store_high_engagement_post(success_case_id, post_type, structure, script, intro_char_count, main_char_count, conclusion_char_count, total_duration, key_elements)
                
                print(f"Stored high engagement post for: {brand_name}")
    
    return success_case_ids

def main():
    """Main function to run the enhanced research process"""
    print("Starting enhanced research process...")
    
    create_enhanced_tables()
    
    industries = ["美容", "ファッション", "食品", "テクノロジー", "エンターテイメント"]
    platforms = ["YouTube", "Instagram", "TikTok"]
    
    for industry in industries:
        for platform in platforms:
            process_research_data(industry, platform, num_cases=3)
    
    print("Enhanced research process completed successfully!")

if __name__ == "__main__":
    main()
