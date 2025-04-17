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

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data.db"

def init_db():
    """Initialize the SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
