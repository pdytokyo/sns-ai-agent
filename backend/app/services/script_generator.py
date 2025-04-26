import os
import json
from typing import Dict, Any, List
import openai
from openai import OpenAI
from .embedding import EmbeddingService

api_key = os.getenv("OPENAI_API_KEY", "dummy-api-key-for-testing")
client = OpenAI(api_key=api_key)

class ScriptGenerator:
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def generate_script(self, pattern: str, client_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a script based on a pattern and client info using RAG
        
        Args:
            pattern: Pattern to search for (keywords or description)
            client_info: Client information to incorporate into script
            
        Returns:
            Dict containing generated script and metadata
        """
        templates = self.embedding_service.search(pattern)
        
        if not templates:
            return {"error": "No matching templates found"}
        
        template = templates[0]
        
        prompt = self._create_prompt(template, client_info)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional script writer for social media videos."},
                {"role": "user", "content": prompt}
            ]
        )
        
        script = response.choices[0].message.content
        
        return {
            "script": script,
            "template_path": template["path"],
            "template_distance": template["distance"],
            "char_counts": template["char_counts"],
            "time_codes": template["time_codes"]
        }
    
    def _create_prompt(self, template: Dict[str, Any], client_info: Dict[str, Any]) -> str:
        """Create prompt for script generation"""
        prompt = f"""
        I need you to create a script for a social media video based on a successful template.
        
        CLIENT INFORMATION:
        Industry: {client_info.get('industry', 'Not specified')}
        Target Audience: {client_info.get('target_audience', 'Not specified')}
        Key Message: {client_info.get('key_message', 'Not specified')}
        
        TEMPLATE TRANSCRIPT:
        {template['transcript']}
        
        CHARACTER COUNTS PER SECTION:
        {json.dumps(template['char_counts'], indent=2)}
        
        INSTRUCTIONS:
        1. Create a new script that follows the EXACT SAME STRUCTURE as the template
        2. Maintain similar character counts for each section (within 10%)
        3. Adapt the content to match the client's industry and target audience
        4. Keep the same pacing, tone, and style as the original
        5. Maintain the same hook structure and call-to-action style
        
        Your script should be ready to use for filming without any further editing.
        """
        
        return prompt
