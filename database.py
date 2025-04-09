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

conn.commit()
conn.close()
