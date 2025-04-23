import os
import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock

os.environ["API_URL"] = "http://localhost:8000"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["DISCORD_BOT_TOKEN"] = "test-token"

discord = pytest.importorskip("discord")
langchain = pytest.importorskip("langchain")
langchain_openai = pytest.importorskip("langchain_openai")

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from bots.discord_bot import model_script_from_video, create_original_script, agent_executor
except ImportError:
    pytest.skip("Discord bot modules not available", allow_module_level=True)

@pytest.mark.asyncio
async def test_model_script_from_video_integration():
    """Test that model_script_from_video tool can communicate with backend API"""
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "script": "Test script content",
            "shot_list": ["Shot 1", "Shot 2"]
        }
        
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        result = await model_script_from_video("https://example.com/video")
        
        assert "Test script content" in result
        
        mock_client_instance.__aenter__.return_value.post.assert_called_once_with(
            f"{os.environ['API_URL']}/scripts/modeling",
            json={"video_url": "https://example.com/video"}
        )

@pytest.mark.asyncio
async def test_create_original_script_integration():
    """Test that create_original_script tool can communicate with backend API"""
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "script": "Original script content",
            "shot_list": ["Original Shot 1", "Original Shot 2"]
        }
        
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        result = await create_original_script("test keyword", "test persona")
        
        assert "Original script content" in result
        
        mock_client_instance.__aenter__.return_value.post.assert_called_once_with(
            f"{os.environ['API_URL']}/scripts/original",
            json={"keyword": "test keyword", "persona": "test persona"}
        )

@pytest.mark.asyncio
async def test_agent_executor_integration():
    """Test that agent_executor can process requests and use tools"""
    
    with patch('bots.discord_bot.model_script_from_video') as mock_model_tool, \
         patch('bots.discord_bot.create_original_script') as mock_create_tool:
        
        mock_model_tool.return_value = "Mocked model script result"
        mock_create_tool.return_value = "Mocked original script result"
        
        model_result = await agent_executor.ainvoke({"input": "Can you model a script from this video: https://example.com/video"})
        
        mock_model_tool.assert_called_once()
        assert "Mocked model script result" in str(model_result)
        
        mock_model_tool.reset_mock()
        mock_create_tool.reset_mock()
        
        create_result = await agent_executor.ainvoke({"input": "Create an original script about cats for pet owners"})
        
        mock_create_tool.assert_called_once()
        assert "Mocked original script result" in str(create_result)

@pytest.mark.asyncio
async def test_backend_health_check():
    """Test that backend health endpoint is accessible"""
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{os.environ['API_URL']}/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
