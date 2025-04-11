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
        
        conn.commit()
        conn.close()
        print("Successfully initialized data.db with competitor_scripts table")
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
