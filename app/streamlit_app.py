import streamlit as st
import os
import sqlite3
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from openai import OpenAI

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.instagram_research import process_instagram_post, get_instagram_analysis

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = "data.db"

from app.main import init_db
init_db()

os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)

st.set_page_config(
    page_title="Instagram AI Agent",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.title("Instagram AI Agent")
    st.markdown("---")
    
    menu = st.radio(
        "Navigation",
        ["Home", "Client Information", "Instagram Research", "Script Generation", "Shooting Instructions", "Video Processing"]
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("AI-powered Instagram content generation system")
    
    if os.getenv("OPENAI_API_KEY"):
        st.success("OpenAI API Key: Connected")
    else:
        st.error("OpenAI API Key: Missing")

if menu == "Home":
    st.title("Instagram AI Content Generator")
    st.markdown("""
    Welcome to the Instagram AI Content Generator! This tool helps you create engaging content for Instagram by:
    
    1. Researching high-engagement Instagram content
    2. Analyzing engagement patterns and content structure
    3. Generating tailored scripts based on successful content
    4. Creating detailed shooting instructions
    5. Processing and optimizing videos for Instagram
    
    Get started by navigating to the "Client Information" section.
    """)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM instagram_analysis")
    instagram_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM detailed_success_cases")
    success_cases_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM competitor_scripts")
    scripts_count = cursor.fetchone()[0]
    
    conn.close()
    
    st.markdown("---")
    st.subheader("Database Statistics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Instagram Posts Analyzed", instagram_count)
    with col2:
        st.metric("Success Cases", success_cases_count)
    with col3:
        st.metric("Competitor Scripts", scripts_count)

elif menu == "Client Information":
    st.title("Client Information")
    
    with st.form("client_form"):
        st.subheader("Enter Client Details")
        client_name = st.text_input("Client Name")
        client_email = st.text_input("Client Email")
        client_industry = st.text_input("Industry")
        
        st.subheader("Target Audience")
        age_range = st.multiselect("Age Range", ["13-17", "18-24", "25-34", "35-44", "45-54", "55+"])
        gender = st.multiselect("Gender", ["Male", "Female", "Non-binary", "All"])
        interests = st.text_area("Interests (comma separated)")
        
        submit_button = st.form_submit_button("Save Client Information")
    
    if submit_button:
        if client_name and client_industry:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            
            target_audience = json.dumps({
                "age_range": age_range,
                "gender": gender,
                "interests": [i.strip() for i in interests.split(",") if i.strip()]
            })
            
            cursor.execute(
                "INSERT INTO clients (name, email, industry, target_audience) VALUES (?, ?, ?, ?)",
                (client_name, client_email, client_industry, target_audience)
            )
            
            conn.commit()
            client_id = cursor.lastrowid
            conn.close()
            
            st.success(f"Client information saved successfully! Client ID: {client_id}")
        else:
            st.error("Please fill in the required fields: Client Name and Industry")
    
    st.markdown("---")
    st.subheader("Existing Clients")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    
    cursor.execute("SELECT * FROM clients ORDER BY created_at DESC")
    clients = cursor.fetchall()
    
    conn.close()
    
    if clients:
        for client in clients:
            with st.expander(f"{client['name']} - {client['industry']}"):
                st.write(f"**Email:** {client['email']}")
                
                try:
                    target_audience = json.loads(client['target_audience'])
                    st.write(f"**Age Range:** {', '.join(target_audience.get('age_range', []))}")
                    st.write(f"**Gender:** {', '.join(target_audience.get('gender', []))}")
                    st.write(f"**Interests:** {', '.join(target_audience.get('interests', []))}")
                except:
                    st.write("**Target Audience:** Data format error")
                
                st.write(f"**Created:** {client['created_at']}")
    else:
        st.info("No clients found. Add a new client using the form above.")

elif menu == "Instagram Research":
    st.title("Instagram Research")
    
    with st.form("instagram_research_form"):
        st.subheader("Analyze Instagram Post")
        instagram_url = st.text_input("Instagram Post URL", placeholder="https://www.instagram.com/p/XXXX/")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        
        cursor.execute("SELECT id, name FROM clients ORDER BY name")
        clients = cursor.fetchall()
        
        conn.close()
        
        client_options = ["None"] + [f"{client[0]}: {client[1]}" for client in clients]
        selected_client = st.selectbox("Select Client for Script Rewriting (Optional)", client_options)
        
        submit_button = st.form_submit_button("Analyze Post")
    
    if submit_button:
        if instagram_url and instagram_url.startswith("https://www.instagram.com/"):
            with st.spinner("Analyzing Instagram post..."):
                client_id = None
                if selected_client != "None":
                    client_id = int(selected_client.split(":")[0])
                
                result = process_instagram_post(instagram_url, client_id)
                
                if result.get("success", False):
                    st.success(f"Instagram post analyzed successfully! Post ID: {result.get('post_id')}")
                    
                    st.subheader("Analysis Results")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Views", f"{result.get('views', 0):,}")
                    with col2:
                        st.metric("Likes", f"{result.get('likes', 0):,}")
                    with col3:
                        st.metric("Comments", f"{result.get('comments', 0):,}")
                    with col4:
                        st.metric("Engagement Rate", f"{result.get('engagement_rate', 0):.1f}%")
                    
                    if result.get("transcript"):
                        st.subheader("Transcript")
                        st.text_area("Original Content", result["transcript"], height=150, disabled=True)
                else:
                    st.error(f"Error analyzing post: {result.get('error', 'Unknown error')}")
        else:
            st.error("Please enter a valid Instagram URL")
    
    st.markdown("---")
    st.subheader("Previous Analyses")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM instagram_analysis ORDER BY created_at DESC LIMIT 10")
    analyses = cursor.fetchall()
    
    conn.close()
    
    if analyses:
        for analysis in analyses:
            with st.expander(f"{analysis['post_url']} - {analysis['created_at']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Views:** {analysis['views']:,}")
                with col2:
                    st.write(f"**Likes:** {analysis['likes']:,}")
                with col3:
                    st.write(f"**Comments:** {analysis['comments']:,}")
                
                if analysis['transcript']:
                    st.write("**Transcript:**")
                    st.text(analysis['transcript'][:200] + "..." if len(analysis['transcript']) > 200 else analysis['transcript'])
                
                if analysis['rewritten_script']:
                    st.write("**Rewritten Script:**")
                    st.text(analysis['rewritten_script'][:200] + "..." if len(analysis['rewritten_script']) > 200 else analysis['rewritten_script'])
    else:
        st.info("No previous analyses found. Analyze an Instagram post using the form above.")

elif menu == "Script Generation":
    st.title("Script Generation")
    
    st.info("Script generation functionality will be implemented in the next phase.")

elif menu == "Shooting Instructions":
    st.title("Shooting Instructions")
    
    st.info("Shooting instructions functionality will be implemented in the next phase.")

elif menu == "Video Processing":
    st.title("Video Processing")
    
    st.info("Video processing functionality will be implemented in the next phase.")
