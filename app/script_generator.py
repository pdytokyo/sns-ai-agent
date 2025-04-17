import os
import json
import sqlite3
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data.db"

def get_client_info(client_id):
    """Get client information from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    client = cursor.fetchone()
    
    conn.close()
    
    if not client:
        return None
    
    return dict(client)

def get_high_engagement_posts(limit=5):
    """Get high engagement Instagram posts for reference"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM instagram_analysis 
        WHERE high_engagement = 1 AND transcript IS NOT NULL
        ORDER BY (likes + comments) / CASE WHEN views = 0 THEN 1 ELSE views END DESC
        LIMIT ?
    """, (limit,))
    
    posts = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return posts

def analyze_post_structure(posts):
    """Analyze the structure of high-engagement posts"""
    structures = []
    
    for post in posts:
        if post.get('transcript'):
            transcript = post.get('transcript')
            
            char_count = len(transcript)
            
            word_count = len(transcript.split())
            
            sentence_count = len([s for s in transcript.replace('!', '.').replace('?', '.').split('.') if s.strip()])
            
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            
            hook = transcript.split('.')[0].strip() if '.' in transcript else transcript
            
            sentences = [s.strip() for s in transcript.replace('!', '.').replace('?', '.').split('.') if s.strip()]
            cta = sentences[-1] if sentences else ""
            
            structures.append({
                'post_id': post.get('id'),
                'char_count': char_count,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'avg_sentence_length': avg_sentence_length,
                'hook': hook,
                'cta': cta,
                'engagement_rate': (post.get('likes', 0) + post.get('comments', 0)) / post.get('views', 1) * 100
            })
    
    return structures

def generate_script_proposals(client_id, num_proposals=3, additional_instructions=""):
    """Generate script proposals based on client information and high-engagement posts"""
    client = get_client_info(client_id)
    if not client:
        return {"success": False, "error": "Client not found"}
    
    posts = get_high_engagement_posts(5)
    if not posts:
        return {"success": False, "error": "No high-engagement posts found for reference"}
    
    structures = analyze_post_structure(posts)
    
    avg_char_count = sum(s['char_count'] for s in structures) / len(structures) if structures else 0
    avg_sentence_count = sum(s['sentence_count'] for s in structures) / len(structures) if structures else 0
    
    reference_texts = []
    for post, structure in zip(posts, structures):
        reference_texts.append(f"""
Reference Post (Engagement Rate: {structure['engagement_rate']:.1f}%):
Character Count: {structure['char_count']}
Sentence Count: {structure['sentence_count']}
Hook: "{structure['hook']}"
Content: "{post['transcript']}"
""")
    
    reference_section = "\n\n".join(reference_texts)
    
    target_audience = json.loads(client['target_audience']) if client['target_audience'] else {}
    
    prompt = f"""
Generate {num_proposals} unique script proposals for Instagram reels for the following client:

Client: {client['name']}
Industry: {client['industry']}
Target Audience: {', '.join(target_audience.get('age_range', []))} | {', '.join(target_audience.get('gender', []))} | {', '.join(target_audience.get('interests', []))}

Additional Instructions: {additional_instructions}

Here are some high-engagement Instagram posts for reference:
{reference_section}

IMPORTANT GUIDELINES:
1. Each script should be approximately {int(avg_char_count)} characters long (±10%)
2. Each script should have approximately {int(avg_sentence_count)} sentences (±2)
3. Start with a strong hook that grabs attention in the first 3 seconds
4. Include a clear call to action at the end
5. Match the structure and pacing of the reference posts
6. Use language that resonates with the target audience
7. Include specific words, phrases, and sentence structures that have proven successful in the reference posts
8. Provide a complete script with every word that should be spoken (not just an outline)

For each proposal, provide:
1. A catchy title
2. A complete script (30-60 seconds when spoken)
3. Key points to emphasize
4. Character count

Format each proposal as:


[COMPLETE SCRIPT]

- [POINT 1]
- [POINT 2]
- [POINT 3]


---

"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert Instagram content creator specializing in creating engaging scripts for short-form videos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        proposals_text = response.choices[0].message.content
        
        proposals = []
        current_proposal = {"title": "", "content": "", "key_points": [], "char_count": 0}
        current_section = None
        
        for line in proposals_text.split("\n"):
            line = line.strip()
            
            if line.startswith("# "):
                if current_proposal["title"]:
                    proposals.append(current_proposal.copy())
                
                current_proposal = {"title": line[2:], "content": "", "key_points": [], "char_count": 0}
                current_section = "content"
            elif line.startswith("## Key Points:"):
                current_section = "key_points"
            elif line.startswith("## Character Count:"):
                try:
                    current_proposal["char_count"] = int(line.replace("## Character Count:", "").strip())
                except:
                    current_proposal["char_count"] = len(current_proposal["content"])
                current_section = None
            elif line.startswith("- ") and current_section == "key_points":
                current_proposal["key_points"].append(line[2:])
            elif line == "---":
                continue
            elif current_section == "content" and current_proposal["title"]:
                current_proposal["content"] += line + "\n"
        
        if current_proposal["title"]:
            proposals.append(current_proposal)
        
        return {"success": True, "proposals": proposals}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def store_script_proposals(client_id, proposals):
    """Store script proposals in the database"""
    if not proposals:
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS script_proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        key_points TEXT,
        char_count INTEGER,
        is_selected BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')
    
    proposal_ids = []
    
    for proposal in proposals:
        content = proposal["content"]
        key_points = json.dumps(proposal["key_points"])
        char_count = proposal["char_count"] or len(content)
        
        cursor.execute(
            "INSERT INTO script_proposals (client_id, title, content, key_points, char_count) VALUES (?, ?, ?, ?, ?)",
            (client_id, proposal["title"], content, key_points, char_count)
        )
        
        proposal_ids.append(cursor.lastrowid)
    
    conn.commit()
    conn.close()
    
    return proposal_ids

def get_script_proposals(client_id=None, proposal_id=None):
    """Get script proposals from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if proposal_id:
        cursor.execute("""
            SELECT sp.*, c.name as client_name, c.industry as client_industry
            FROM script_proposals sp
            JOIN clients c ON sp.client_id = c.id
            WHERE sp.id = ?
        """, (proposal_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        proposal = dict(result)
        try:
            proposal["key_points"] = json.loads(proposal["key_points"])
        except:
            proposal["key_points"] = []
            
        return proposal
    
    elif client_id:
        cursor.execute("""
            SELECT sp.*, c.name as client_name
            FROM script_proposals sp
            JOIN clients c ON sp.client_id = c.id
            WHERE sp.client_id = ?
            ORDER BY sp.created_at DESC
        """, (client_id,))
    else:
        cursor.execute("""
            SELECT sp.*, c.name as client_name
            FROM script_proposals sp
            JOIN clients c ON sp.client_id = c.id
            ORDER BY sp.created_at DESC
        """)
    
    results = []
    for row in cursor.fetchall():
        proposal = dict(row)
        try:
            proposal["key_points"] = json.loads(proposal["key_points"])
        except:
            proposal["key_points"] = []
        
        results.append(proposal)
    
    conn.close()
    return results

def select_script_proposal(proposal_id, client_id):
    """Select a script proposal for a client"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE script_proposals SET is_selected = 0 WHERE client_id = ?",
        (client_id,)
    )
    
    cursor.execute(
        "UPDATE script_proposals SET is_selected = 1 WHERE id = ?",
        (proposal_id,)
    )
    
    conn.commit()
    conn.close()
    
    return True

def update_script_proposal(proposal_id, title=None, content=None, key_points=None):
    """Update a script proposal"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    
    if content is not None:
        updates.append("content = ?")
        params.append(content)
        updates.append("char_count = ?")
        params.append(len(content))
    
    if key_points is not None:
        updates.append("key_points = ?")
        params.append(json.dumps(key_points))
    
    if not updates:
        conn.close()
        return False
    
    query = f"UPDATE script_proposals SET {', '.join(updates)} WHERE id = ?"
    params.append(proposal_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        client_id = int(sys.argv[1])
        num_proposals = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        
        result = generate_script_proposals(client_id, num_proposals)
        
        if result["success"]:
            proposal_ids = store_script_proposals(client_id, result["proposals"])
            print(f"Generated {len(proposal_ids)} script proposals for client {client_id}")
            
            for i, proposal in enumerate(result["proposals"]):
                print(f"\nProposal {i+1}: {proposal['title']}")
                print(f"Character Count: {proposal['char_count']}")
                print(f"Key Points: {', '.join(proposal['key_points'])}")
        else:
            print(f"Error: {result['error']}")
    else:
        print("Usage: python script_generator.py <client_id> [num_proposals]")
