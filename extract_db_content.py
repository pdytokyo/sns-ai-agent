import sqlite3
import os

db_path = os.path.expanduser('~/attachments/7f00ff76-337d-41ab-88f1-29849fd9fbd7/data.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('SELECT id, category, result FROM research_results')
results = cursor.fetchall()

with open('research_results_full.txt', 'w', encoding='utf-8') as f:
    for row in results:
        f.write(f"ID: {row[0]}\n")
        f.write(f"Category: {row[1]}\n")
        f.write(f"Result:\n{row[2]}\n")
        f.write("-" * 80 + "\n")

for row in results:
    print(f"ID: {row[0]}")
    print(f"Category: {row[1]}")
    print(f"Result length: {len(row[2])} characters")
    print(f"First 100 chars: {row[2][:100]}...")
    print(f"Last 100 chars: ...{row[2][-100:]}")
    print("-" * 80)

print(f"Full results saved to research_results_full.txt")

conn.close()
