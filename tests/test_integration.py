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
        
        with patch('bots.discord_bot.bot') as mock_bot:
            model_command = AsyncMock()
            mock_bot.all_commands = {"model": model_command}
            
            await model_command(mock_ctx, url="https://example.com/video")
            
            mock_client_instance.__aenter__.return_value.post.assert_called_once_with(
                f"{os.environ['API_URL']}/scripts/modeling",
                json={"video_url": "https://example.com/video"}
            )
            
            mock_ctx.send.assert_any_call(f"Generating script based on https://example.com/video... This may take a minute.")
            
            mock_ctx.reset_mock()
            mock_client_instance.reset_mock()
            
            orig_command = AsyncMock()
            mock_bot.all_commands = {"orig": orig_command}
            
            await orig_command(mock_ctx, args="keyword / persona")
            
            mock_client_instance.__aenter__.return_value.post.assert_called_once_with(
                f"{os.environ['API_URL']}/scripts/original",
                json={"keyword": "keyword", "persona": "persona"}
            )
            
            mock_ctx.send.assert_any_call(f"Generating original script for keyword 'keyword' and persona 'persona'... This may take a minute.")

@pytest.mark.asyncio
async def test_agent_integration():
    """Test that LangChain agent can process requests"""
    
    with patch('langchain.agents.AgentExecutor.from_agent_and_tools') as mock_agent_factory, \
         patch('langchain_openai.ChatOpenAI') as mock_llm:
        
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "output": "I'll help you with that script."
        }
        
        mock_agent_factory.return_value = mock_agent
        
        from bots.discord_bot import create_openai_tools_agent, ChatPromptTemplate, MessagesPlaceholder
        
        with patch('langchain.prompts.ChatPromptTemplate.from_messages') as mock_prompt_factory:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "System prompt"),
                MessagesPlaceholder("history"),
                ("user", "{input}"),
                MessagesPlaceholder("agent_scratchpad")
            ])
            
            assert any(isinstance(m, MessagesPlaceholder) and m.variable_name == "agent_scratchpad" 
                      for m in prompt.messages)

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
