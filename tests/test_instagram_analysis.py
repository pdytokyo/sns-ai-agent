import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instagram_analyzer import process_instagram_post, get_instagram_analysis

class TestInstagramAnalysis(unittest.TestCase):
    """Test Instagram analysis functionality"""
    
    @patch('instagram_analyzer.client')
    def test_process_instagram_post(self, mock_client):
        """Test processing an Instagram post with mocked OpenAI client"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Mocked rewritten script"
        mock_client.chat.completions.create.return_value = mock_response
        
        post_url = "https://www.instagram.com/p/C5NJJfJSQnP/"
        client_id = 1
        
        result = process_instagram_post(post_url, client_id, use_mock=True)
        
        self.assertTrue(result["success"])
        self.assertIn("post_id", result)
        self.assertIn("views", result)
        self.assertIn("likes", result)
        self.assertIn("comments", result)
        self.assertIn("engagement_rate", result)
        self.assertIn("high_engagement", result)
        self.assertIn("transcript", result)
        
        result = process_instagram_post(post_url, use_mock=True)
        self.assertTrue(result["success"])
    
    def test_get_instagram_analysis(self):
        """Test retrieving Instagram analysis results"""
        post_url = "https://www.instagram.com/p/C5Ij-ufSdnm/"
        process_result = process_instagram_post(post_url, use_mock=True)
        
        post_id = process_result["post_id"]
        result = get_instagram_analysis(post_id)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["post_url"], post_url)
        
        results = get_instagram_analysis()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

if __name__ == "__main__":
    unittest.main()
