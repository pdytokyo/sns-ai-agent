import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def mock_openai_env():
    """Set dummy OpenAI API key for all tests"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "dummy-api-key-for-testing"}):
        yield

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for tests"""
    with patch('instagram_analyzer.client') as mock_client:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked rewritten script"
        mock_client.chat.completions.create.return_value = mock_response
        
        mock_transcription = MagicMock()
        mock_transcription.text = "Mocked transcription text"
        mock_client.audio.transcriptions.create.return_value = mock_transcription
        
        yield mock_client
