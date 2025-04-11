import requests
import json
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
TEST_YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
    "https://www.youtube.com/watch?v=9bZkp7q19f0"   # PSY - GANGNAM STYLE
]

def test_create_client_with_youtube_urls():
    """Test creating a client with YouTube URLs"""
    print("Testing client creation with YouTube URLs...")
    
    response = requests.post(
        f"{BASE_URL}/clients/",
        json={
            "name": "Test Client",
            "email": "test@example.com",
            "youtube_urls": TEST_YOUTUBE_URLS
        }
    )
    
    if response.status_code == 200:
        client_data = response.json()
        print(f"Client created successfully with ID: {client_data['id']}")
        return client_data['id']
    else:
        print(f"Failed to create client: {response.status_code} - {response.text}")
        return None

def test_add_youtube_urls_to_existing_client(client_id):
    """Test adding YouTube URLs to an existing client"""
    print(f"Testing adding YouTube URLs to existing client {client_id}...")
    
    response = requests.post(
        f"{BASE_URL}/clients/{client_id}/youtube-urls",
        data={"youtube_urls": TEST_YOUTUBE_URLS}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Added URLs: {result['added_urls']}")
        return True
    else:
        print(f"Failed to add YouTube URLs: {response.status_code} - {response.text}")
        return False

def test_generate_profile_with_transcripts(client_id):
    """Test generating a profile using YouTube transcripts"""
    print(f"Testing profile generation with transcripts for client {client_id}...")
    
    selection_response = requests.post(
        f"{BASE_URL}/selections/",
        data={
            "client_id": client_id,
            "selection.target_attributes": ["20代", "男性"],
            "selection.operational_purposes": ["ブランディング", "集客"],
            "selection.platforms": ["YouTube"]
        }
    )
    
    if selection_response.status_code != 200:
        print(f"Failed to create selection: {selection_response.status_code} - {selection_response.text}")
        return False
    
    profile_response = requests.post(
        f"{BASE_URL}/generate-profile/",
        data={"client_id": client_id}
    )
    
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        print(f"Profile generated successfully:")
        print(f"Account name: {profile_data['account_name']}")
        print(f"Profile text: {profile_data['profile_text']}")
        return profile_data['id']
    else:
        print(f"Failed to generate profile: {profile_response.status_code} - {profile_response.text}")
        return None

def test_generate_script_with_transcripts(client_id, profile_id):
    """Test generating a script using YouTube transcripts"""
    print(f"Testing script generation with transcripts for client {client_id}...")
    
    select_profile_response = requests.post(
        f"{BASE_URL}/select-profile/{profile_id}",
        data={"client_id": client_id}
    )
    
    if select_profile_response.status_code != 200:
        print(f"Failed to select profile: {select_profile_response.status_code} - {select_profile_response.text}")
        return False
    
    script_response = requests.post(
        f"{BASE_URL}/generate-script/",
        data={"client_id": client_id}
    )
    
    if script_response.status_code == 200:
        script_data = script_response.json()
        print(f"Script generated successfully:")
        print(f"Script text: {script_data['script_text'][:200]}...")  # Show first 200 chars
        return True
    else:
        print(f"Failed to generate script: {script_response.status_code} - {script_response.text}")
        return False

def verify_database_transcripts(client_id):
    """Verify that transcripts were stored in the database"""
    print(f"Verifying database transcripts for client {client_id}...")
    
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT video_url, transcript_text FROM client_video_transcripts WHERE client_id = ?", (client_id,))
    transcripts = cursor.fetchall()
    
    if transcripts:
        print(f"Found {len(transcripts)} transcripts in the database:")
        for i, (url, text) in enumerate(transcripts):
            print(f"Transcript {i+1}:")
            print(f"URL: {url}")
            print(f"Text (first 200 chars): {text[:200]}...")
        return True
    else:
        print("No transcripts found in the database")
        return False
    
    conn.close()

def main():
    """Run all tests"""
    print("Starting YouTube transcript feature tests...")
    
    client_id = test_create_client_with_youtube_urls()
    if not client_id:
        return
    
    if not verify_database_transcripts(client_id):
        print("Warning: No transcripts found in database after client creation")
    
    if not test_add_youtube_urls_to_existing_client(client_id):
        print("Warning: Failed to add YouTube URLs to existing client")
    
    verify_database_transcripts(client_id)
    
    profile_id = test_generate_profile_with_transcripts(client_id)
    if not profile_id:
        return
    
    test_generate_script_with_transcripts(client_id, profile_id)
    
    print("All tests completed!")

if __name__ == "__main__":
    main()
