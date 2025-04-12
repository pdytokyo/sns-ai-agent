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

cursor.execute('''
CREATE TABLE IF NOT EXISTS weekly_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,  -- "Google", "YouTube", "TikTok"
    keyword TEXT NOT NULL,
    rank INTEGER,
    region TEXT DEFAULT "JP",
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS competitor_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,  -- "YouTube", "Instagram", "TikTok"
    video_url TEXT NOT NULL,
    video_title TEXT,
    view_count INTEGER,
    comment_count INTEGER,
    engagement_rate REAL,
    popular_phrases TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
