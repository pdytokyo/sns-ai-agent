import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def initialize_databases():
    print("Initializing databases...")
    
    try:
        from db_enhancement import init_db
        init_db()
        print("Successfully initialized app.db using db_enhancement.py")
    except Exception as e:
        print(f"Error initializing app.db: {str(e)}")
    
    try:
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            industry TEXT,
            video_url TEXT,
            full_script TEXT,
            keywords TEXT,
            empathy_points TEXT,
            hook TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            platform TEXT,
            rank INTEGER,
            region TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            video_url TEXT,
            title TEXT,
            view_count INTEGER,
            comment_count INTEGER,
            engagement_rate REAL,
            top_phrases TEXT,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aspect_ratio TEXT,
            margin_seconds REAL,
            client_id INTEGER
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id INTEGER,
            client_id INTEGER,
            output_path TEXT,
            aspect_ratio TEXT,
            processing_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (upload_id) REFERENCES uploads (id),
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS instagram_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT NOT NULL,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            caption TEXT,
            hashtags TEXT,
            posted_at TIMESTAMP,
            high_engagement BOOLEAN DEFAULT 0,
            transcript TEXT,
            rewritten_script TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            youtube_urls TEXT,
            research_completed BOOLEAN DEFAULT 0,
            research_completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            target_attributes TEXT NOT NULL,
            operational_purposes TEXT NOT NULL,
            platforms TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            profile_text TEXT NOT NULL,
            is_selected BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            script_text TEXT NOT NULL,
            is_selected BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS script_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_selected BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shooting_instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            script_proposal_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (script_proposal_id) REFERENCES script_proposals (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subtitles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processed_video_id INTEGER NOT NULL,
            start_time FLOAT NOT NULL,
            end_time FLOAT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (processed_video_id) REFERENCES processed_videos (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS copyright_free_audio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT,
            genre TEXT,
            mood TEXT,
            duration FLOAT,
            file_path TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS final_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            processed_video_id INTEGER NOT NULL,
            bgm_id INTEGER,
            bgm_volume FLOAT DEFAULT 0.5,
            output_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (processed_video_id) REFERENCES processed_videos (id),
            FOREIGN KEY (bgm_id) REFERENCES copyright_free_audio (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            account_id TEXT NOT NULL,
            access_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        print("Successfully initialized data.db with required tables")
    except Exception as e:
        print(f"Error initializing data.db: {str(e)}")

def check_databases():
    db_files = ["data.db", "app.db"]
    
    for db_file in db_files:
        if not os.path.exists(db_file):
            print(f"Database file {db_file} does not exist.")
            continue
            
        print(f"\nChecking database: {db_file}")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"Tables in {db_file}: {', '.join(tables)}")
        
        tables_to_check = ["detailed_success_cases", "copyright_free_audio", "competitor_scripts"]
        
        for table in tables_to_check:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"\nTable '{table}' exists in {db_file}")
                cursor.execute(f"PRAGMA table_info({table})")
                schema = cursor.fetchall()
                print(f"Schema for '{table}':")
                for col in schema:
                    print(f"  {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] == 1 else ''}")
            else:
                print(f"\nTable '{table}' does not exist in {db_file}")
        
        conn.close()

if __name__ == "__main__":
    initialize_databases()
    
    check_databases()
