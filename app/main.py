import streamlit as st
import os
import sqlite3
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import yt_dlp
from moviepy.editor import VideoFileClip
import logging

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data.db"

def check_and_migrate_table(conn, table_name, columns):
    """
    Check if a table exists and has all required columns.
    If not, add missing columns.
    
    Args:
        conn: SQLite connection
        table_name: Name of the table to check
        columns: Dictionary of column names and their types
    """
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    if not existing_columns:
        logging.info(f"Table {table_name} does not exist. It will be created.")
        return False
    
    missing_columns = {col: col_type for col, col_type in columns.items() 
                      if col not in existing_columns}
    
    for col, col_type in missing_columns.items():
        logging.info(f"Adding missing column {col} to table {table_name}")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}")
    
    conn.commit()
    return True

def init_db():
    """Initialize the SQLite database with required tables and migrate if needed"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    clients_schema = {
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'name': 'TEXT NOT NULL',
        'email': 'TEXT',
        'industry': 'TEXT',
        'target_audience': 'TEXT',
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    }
    
    table_exists = check_and_migrate_table(conn, 'clients', clients_schema)
    
    if not table_exists:
        columns_str = ', '.join([f"{col} {col_type}" for col, col_type in clients_schema.items()])
        cursor.execute(f'''
        CREATE TABLE clients (
            {columns_str}
        )
        ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detailed_success_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        industry TEXT NOT NULL,
        video_url TEXT NOT NULL,
        buzz_point TEXT,
        top_comments TEXT,
        trend_topics TEXT,
        engagement_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS competitor_scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        industry TEXT NOT NULL,
        video_url TEXT NOT NULL,
        full_script TEXT,
        keywords TEXT,
        empathy_points TEXT,
        hook TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bgm_library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT,
        mood TEXT,
        url TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        posted_at TEXT,
        high_engagement BOOLEAN,
        transcript TEXT,
        rewritten_script TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()
