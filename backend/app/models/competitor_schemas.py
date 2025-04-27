from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ScrapeRequest(BaseModel):
    urls: List[str]

class GenerateScriptRequest(BaseModel):
    pattern: str
    client_info: Dict[str, Any]
