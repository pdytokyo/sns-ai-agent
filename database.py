import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS research_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    content TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

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

conn.commit()
conn.close()
