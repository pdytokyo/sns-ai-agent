import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data.db"

def get_api_key(key_name, default_value=None):
    """
    Get API key from environment variables
    
    Args:
        key_name (str): Name of the API key in .env file
        default_value (str, optional): Default value if key is not found
        
    Returns:
        str: API key value
    """
    api_key = os.getenv(key_name, default_value)
    if not api_key and default_value is None:
        print(f"Warning: {key_name} not found in environment variables")
    return api_key

OPENAI_API_KEY = get_api_key("OPENAI_API_KEY")
YOUTUBE_API_KEY = get_api_key("YOUTUBE_API_KEY")

def get_env_var(var_name, default_value=None):
    """
    Get any environment variable
    
    Args:
        var_name (str): Name of the environment variable
        default_value (any, optional): Default value if variable is not found
        
    Returns:
        str: Environment variable value
    """
    return os.getenv(var_name, default_value)
