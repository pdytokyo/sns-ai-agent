import pytest
from sqlmodel import Session, select
from fastapi.testclient import TestClient
import json
import os
from unittest.mock import patch, MagicMock

from backend.app.main import app
from backend.app.models.competitor import CompetitorVideo
from backend.app.services.scraper import VideoScraper
from backend.app.services.embedding import EmbeddingService

client = TestClient(app)

@pytest.fixture
def mock_video_data():
    return {
        "platform": "instagram",
        "video_url": "https://www.instagram.com/p/test123/",
        "engagement_rate": 8.5,
        "view_count": 10000,
        "like_count": 800,
        "comment_count": 50,
        "share_count": 20
    }

@pytest.fixture
def mock_competitor_video(mock_video_data):
    return CompetitorVideo(**mock_video_data)

@patch("backend.app.services.scraper.VideoScraper.scrape_videos")
def test_scrape_competitor_videos(mock_scrape):
    mock_scrape.return_value = [
        {
            "platform": "instagram",
            "video_url": "https://www.instagram.com/p/test123/",
            "engagement_rate": 8.5,
            "view_count": 10000,
            "like_count": 800,
            "comment_count": 50,
            "share_count": 20
        }
    ]
    
    response = client.post(
        "/competitor/scrape",
        json=["https://www.instagram.com/p/test123/"]
    )
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["platform"] == "instagram"
    assert response.json()[0]["engagement_rate"] == 8.5

@patch("backend.app.services.scraper.VideoScraper.process_video")
def test_process_competitor_video(mock_process, mock_competitor_video):
    mock_process.return_value = CompetitorVideo(
        id=1,
        platform=mock_competitor_video.platform,
        video_url=mock_competitor_video.video_url,
        engagement_rate=mock_competitor_video.engagement_rate,
        view_count=mock_competitor_video.view_count,
        like_count=mock_competitor_video.like_count,
        comment_count=mock_competitor_video.comment_count,
        share_count=mock_competitor_video.share_count,
        transcript="This is a test transcript",
        time_codes={"0": 0, "3": 3, "6": 6},
        char_counts={"0": 10, "3": 15, "6": 12}
    )
    
    response = client.post(f"/competitor/process/1")
    
    assert response.status_code in [200, 404]

@patch("backend.app.services.embedding.EmbeddingService.search")
def test_generate_script(mock_search):
    mock_search.return_value = [
        {
            "path": "data/templates/1.txt",
            "distance": 0.1,
            "transcript": "This is a test transcript",
            "time_codes": {"0": 0, "3": 3, "6": 6},
            "char_counts": {"0": 10, "3": 15, "6": 12}
        }
    ]
    
    response = client.post(
        "/scripts/generate",
        json={
            "pattern": "test pattern",
            "client_info": {
                "industry": "beauty",
                "target_audience": "women 18-35",
                "key_message": "natural skincare"
            }
        }
    )
    
    assert response.status_code == 200
    assert "script" in response.json()
    assert "template_path" in response.json()
    assert "template_distance" in response.json()
