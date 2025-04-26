import os
import json
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index_dir = Path('faiss')
        self.index_dir.mkdir(exist_ok=True)
        self.index_path = self.index_dir / 'index.bin'
        self.paths_path = self.index_dir / 'paths.json'
        self.templates_dir = Path('data/templates')
        self.templates_dir.mkdir(exist_ok=True, parents=True)
        
        if self.index_path.exists() and self.paths_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.paths_path, 'r') as f:
                self.paths = json.load(f)
        else:
            self.index = faiss.IndexFlatL2(384)  # 384 is the dimension of all-MiniLM-L6-v2 embeddings
            self.paths = []
    
    def save_template(self, video_id: int, transcript: str, time_codes: Dict[str, Any], char_counts: Dict[str, int]):
        """Save transcript template with time codes and character counts"""
        template_path = self.templates_dir / f"{video_id}.txt"
        
        template_data = {
            'transcript': transcript,
            'time_codes': time_codes,
            'char_counts': char_counts
        }
        
        with open(template_path, 'w') as f:
            json.dump(template_data, f, indent=2)
        
        return str(template_path)
    
    def add_to_index(self, video_id: int, transcript: str):
        """Add transcript to FAISS index"""
        embedding = self.model.encode([transcript])[0]
        
        self.index.add(np.array([embedding], dtype=np.float32))
        
        template_path = str(self.templates_dir / f"{video_id}.txt")
        self.paths.append(template_path)
        
        faiss.write_index(self.index, str(self.index_path))
        with open(self.paths_path, 'w') as f:
            json.dump(self.paths, f, indent=2)
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar templates"""
        query_embedding = self.model.encode([query])[0]
        
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.paths):
                template_path = self.paths[idx]
                with open(template_path, 'r') as f:
                    template_data = json.load(f)
                
                results.append({
                    'path': template_path,
                    'distance': float(distances[0][i]),
                    'transcript': template_data['transcript'],
                    'time_codes': template_data['time_codes'],
                    'char_counts': template_data['char_counts']
                })
        
        return results
