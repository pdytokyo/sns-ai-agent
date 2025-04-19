import os
import asyncio
from typing import Dict, Any
import openai
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY", "dummy-api-key-for-testing")
client = OpenAI(api_key=api_key)

async def generate_script_from_transcript(transcript: str, video_url: str) -> Dict[str, Any]:
    """
    Generate a script and shot list based on a transcript.
    
    Args:
        transcript: Transcription of the video
        video_url: URL of the original video
        
    Returns:
        Dict containing script and shot list
    """
    prompt = f"""
    You are an expert social media content creator. Analyze this transcript from a video and create:
    
    1. A rewritten script that maintains the same structure and flow but improves clarity and engagement
    2. A detailed shot list with camera angles, expressions, and visual directions
    
    Original video URL: {video_url}
    
    Transcript:
    {transcript}
    
    Format your response as a JSON object with these keys:
    - script: The full rewritten script
    - shot_list: Array of shot objects, each with:
      - time_code: Approximate time in the script
      - shot_type: (close-up, medium, wide, etc.)
      - description: What to show
      - expression: How the subject should appear
      - camera_movement: Any camera movement
    
    Make the script engaging for social media while preserving the original message and structure.
    """
    
    def _generate():
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert social media content creator specializing in Instagram and TikTok videos."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _generate)
    
    import json
    script_data = json.loads(result)
    
    return script_data

async def generate_original_script(keyword: str, persona: str) -> Dict[str, Any]:
    """
    Generate an original script and shot list based on a keyword and persona.
    
    Args:
        keyword: Main topic or keyword for the script
        persona: Target persona/audience for the script
        
    Returns:
        Dict containing script and shot list
    """
    prompt = f"""
    You are an expert social media content creator. Create an original script and shot list for a short-form video (Instagram Reels or TikTok) based on:
    
    Keyword/Topic: {keyword}
    Target Persona: {persona}
    
    The script should be:
    - 30-60 seconds in length
    - Engaging from the first 3 seconds
    - Following proven social media content structures
    - Optimized for the target persona
    
    Format your response as a JSON object with these keys:
    - script: The full script
    - shot_list: Array of shot objects, each with:
      - time_code: Approximate time in the script
      - shot_type: (close-up, medium, wide, etc.)
      - description: What to show
      - expression: How the subject should appear
      - camera_movement: Any camera movement
    
    Make the script highly engaging for social media with a strong hook and call to action.
    """
    
    def _generate():
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert social media content creator specializing in Instagram and TikTok videos."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _generate)
    
    import json
    script_data = json.loads(result)
    
    return script_data
