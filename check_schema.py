import sqlite3
import os

def check_table_exists(cursor, table_name):
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def get_table_schema(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def main():
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
            if check_table_exists(cursor, table):
                print(f"\nTable '{table}' exists in {db_file}")
                schema = get_table_schema(cursor, table)
                print(f"Schema for '{table}':")
                for col in schema:
                    print(f"  {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] == 1 else ''}")
            else:
                print(f"\nTable '{table}' does not exist in {db_file}")
        
        conn.close()

if __name__ == "__main__":
    main()
