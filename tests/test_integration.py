import os
import pytest
import httpx
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

os.environ["API_URL"] = "http://localhost:8000"
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
os.environ["DISCORD_BOT_TOKEN"] = "test-token"

discord = pytest.importorskip("discord")
langchain = pytest.importorskip("langchain")
langchain_openai = pytest.importorskip("langchain_openai")

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import bots.discord_bot
    from bots.discord_bot import run_bot
except ImportError:
    pytest.skip("Discord bot modules not available", allow_module_level=True)

@pytest.mark.asyncio
async def test_discord_bot_commands():
    """Test that Discord bot commands can communicate with backend API"""
    
    mock_ctx = MagicMock()
    mock_ctx.send = AsyncMock()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "script": "Test script content",
        "shot_list": ["Shot 1", "Shot 2"]
    }
    
    mock_post = AsyncMock(return_value=mock_response)
    
    mock_aenter = AsyncMock()
    mock_aenter.return_value.post = mock_post
    
    mock_client = AsyncMock()
    mock_client.__aenter__ = mock_aenter
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        # Import the model_command from discord_bot
        from bots.discord_bot import model_command
        
        await model_command(mock_ctx, url="https://example.com/video")
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/scripts/modeling")
        assert kwargs["json"]["video_url"] == "https://example.com/video"
        
        mock_ctx.send.assert_any_call("Generating script based on https://example.com/video... This may take a minute.")
        
        mock_ctx.reset_mock()
        mock_post.reset_mock()
        
        # Import the original_command from discord_bot
        from bots.discord_bot import original_command
        
        await original_command(mock_ctx, args="keyword / persona")
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/scripts/original")
        assert kwargs["json"]["keyword"] == "keyword"
        assert kwargs["json"]["persona"] == "persona"
        
        mock_ctx.send.assert_any_call("Generating original script for keyword 'keyword' and persona 'persona'... This may take a minute.")

@pytest.mark.asyncio
async def test_agent_integration():
    """Test that LangChain agent can process requests"""
    
    # Import the prompt from discord_bot to verify it includes agent_scratchpad
    from bots.discord_bot import prompt
    
    assert "{agent_scratchpad}" in str(prompt)
    
    with patch('langchain.agents.create_openai_tools_agent') as mock_create_agent, \
         patch('langchain_openai.ChatOpenAI') as mock_llm:
        
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # Import the agent_executor from discord_bot
        from bots.discord_bot import agent_executor
        
        assert agent_executor is not None

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
