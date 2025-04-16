# Environment Variables Configuration

This document describes the environment variables required for the SNS AI Agent application.

## Required Environment Variables

### For GitHub Actions

Add these secrets to your GitHub repository:

1. `FLY_API_TOKEN` - Your Fly.io API token for deployment
2. `OPENAI_API_KEY` - Your OpenAI API key
3. `YOUTUBE_API_KEY` - Your YouTube API key
4. `INSTAGRAM_USERNAME` - Your Instagram username
5. `INSTAGRAM_PASSWORD` - Your Instagram password
6. `TIKTOK_API_KEY` - Your TikTok API key

### For Local Development

Create a `.env` file in the project root with the following variables:

```
OPENAI_API_KEY=your_openai_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
TIKTOK_API_KEY=your_tiktok_api_key_here
DB_PATH=data.db
DEBUG=False
LOG_LEVEL=INFO
```

## Setting up Environment Variables in Fly.io

To set environment variables in Fly.io:

```bash
flyctl secrets set OPENAI_API_KEY=your_openai_api_key_here
flyctl secrets set YOUTUBE_API_KEY=your_youtube_api_key_here
flyctl secrets set INSTAGRAM_USERNAME=your_instagram_username
flyctl secrets set INSTAGRAM_PASSWORD=your_instagram_password
flyctl secrets set TIKTOK_API_KEY=your_tiktok_api_key_here
```

Or import multiple secrets at once:

```bash
flyctl secrets import < .env.production
```
