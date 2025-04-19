import os
import asyncio
import tempfile
from typing import Dict, Any
import openai
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY", "dummy-api-key-for-testing")
client = OpenAI(api_key=api_key)

async def transcribe_audio(video_path: str) -> str:
    """
    Transcribe audio from a video file using OpenAI Whisper API.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Transcription text
    
    Raises:
        Exception: If transcription fails
    """
    temp_audio_path = os.path.join(tempfile.mkdtemp(), "audio.mp3")
    
    extract_cmd = f"ffmpeg -i {video_path} -q:a 0 -map a {temp_audio_path} -y"
    
    proc = await asyncio.create_subprocess_shell(
        extract_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await proc.communicate()
    
    if not os.path.exists(temp_audio_path):
        raise Exception("Failed to extract audio from video")
    
    def _transcribe():
        with open(temp_audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return response.text
    
    loop = asyncio.get_event_loop()
    transcript = await loop.run_in_executor(None, _transcribe)
    
    try:
        os.remove(temp_audio_path)
    except:
        pass
    
    return transcript
