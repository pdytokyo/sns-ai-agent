import os
import asyncio
import json
import discord
from discord.ext import commands
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.tools import tool
import httpx

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://backend:8000")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

llm = ChatOpenAI(model="gpt-4o")

@tool
async def model_script_from_video(video_url: str) -> str:
    """
    Generate a script and shot list based on a video URL.
    
    Args:
        video_url: URL of the video to model the script after
        
    Returns:
        JSON string containing script and shot list
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/scripts/modeling",
            json={"video_url": video_url}
        )
        if response.status_code != 200:
            return f"Error: {response.text}"
        return json.dumps(response.json(), indent=2)

@tool
async def create_original_script(keyword: str, persona: str) -> str:
    """
    Generate an original script and shot list based on a keyword and persona.
    
    Args:
        keyword: Main topic or keyword for the script
        persona: Target persona/audience for the script
        
    Returns:
        JSON string containing script and shot list
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/scripts/original",
            json={"keyword": keyword, "persona": persona}
        )
        if response.status_code != 200:
            return f"Error: {response.text}"
        return json.dumps(response.json(), indent=2)

@tool
async def generate_script_from_pattern(pattern: str, client_info: dict) -> str:
    """
    Generate a script based on a pattern and client info using RAG remix.
    
    Args:
        pattern: Pattern to search for (keywords or description)
        client_info: Client information to incorporate into script
        
    Returns:
        JSON string containing generated script and metadata
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/scripts/generate",
            json={"pattern": pattern, "client_info": client_info}
        )
        if response.status_code != 200:
            return f"Error: {response.text}"
        return json.dumps(response.json(), indent=2)

tools = [model_script_from_video, create_original_script, generate_script_from_pattern]

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant that helps create scripts for social media videos.
    You can generate scripts based on existing videos, create original scripts, or use RAG remix to generate scripts based on patterns.
    
    When a user asks you to model a script from a video, use the model_script_from_video tool.
    When a user asks you to create an original script, use the create_original_script tool.
    When a user asks you to generate a script based on a pattern, use the generate_script_from_pattern tool.
    
    Always respond in a helpful and friendly manner.
    """),
    ("human", "{input}"),
    ("assistant", "{agent_scratchpad}")
])

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user}")

@bot.command(name="model")
async def model_command(ctx, url: str):
    """Generate a script based on a video URL"""
    await ctx.send(f"Generating script based on {url}... This may take a minute.")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/scripts/modeling",
                json={"video_url": url}
            )
            
            if response.status_code != 200:
                await ctx.send(f"Error: {response.text}")
                return
            
            result = response.json()
            
            script = result.get("script", "No script generated")
            
            await ctx.send(f"**Generated Script:**\n```\n{script[:1500]}...\n```")
            
            with open("script_response.json", "w") as f:
                json.dump(result, f, indent=2)
            
            await ctx.send(file=discord.File("script_response.json"))
            
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@bot.command(name="orig")
async def original_command(ctx, *, args: str):
    """Generate an original script based on keyword and persona"""
    try:
        if "/" not in args:
            await ctx.send("Please provide both keyword and persona separated by '/'")
            return
        
        keyword, persona = args.split("/", 1)
        keyword = keyword.strip()
        persona = persona.strip()
        
        await ctx.send(f"Generating original script for keyword '{keyword}' and persona '{persona}'... This may take a minute.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/scripts/original",
                json={"keyword": keyword, "persona": persona}
            )
            
            if response.status_code != 200:
                await ctx.send(f"Error: {response.text}")
                return
            
            result = response.json()
            
            script = result.get("script", "No script generated")
            
            await ctx.send(f"**Generated Script:**\n```\n{script[:1500]}...\n```")
            
            with open("script_response.json", "w") as f:
                json.dump(result, f, indent=2)
            
            await ctx.send(file=discord.File("script_response.json"))
            
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@bot.command(name="script")
async def script_command(ctx, *, args: str):
    """Generate a script based on pattern and client info"""
    try:
        if "/" not in args:
            await ctx.send("Please provide both pattern and client_info separated by '/'")
            return
        
        pattern, client_info_str = args.split("/", 1)
        pattern = pattern.strip()
        client_info_str = client_info_str.strip()
        
        try:
            client_info = json.loads(client_info_str)
        except json.JSONDecodeError:
            client_info = {
                "industry": client_info_str,
                "target_audience": "General audience",
                "key_message": "Informative content"
            }
        
        await ctx.send(f"Generating script for pattern '{pattern}'... This may take a minute.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/scripts/generate",
                json={"pattern": pattern, "client_info": client_info}
            )
            
            if response.status_code != 200:
                await ctx.send(f"Error: {response.text}")
                return
            
            result = response.json()
            
            script = result.get("script", "No script generated")
            
            await ctx.send(f"**Generated Script:**\n```\n{script[:1500]}...\n```")
            
            with open("script_response.json", "w") as f:
                json.dump(result, f, indent=2)
            
            await ctx.send(file=discord.File("script_response.json"))
            
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

def run_bot():
    """Run the Discord bot"""
    bot.run(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    run_bot()
