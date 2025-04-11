# SNS AI Agent

SNS AI Agent is a web application that helps users create social media content by leveraging AI to generate profiles, scripts, and process videos.

## Features

- Target attribute, operational purpose, and platform selection
- File upload (video, text, PDF)
- AI-generated account names and profile texts
- AI-generated scripts with unlimited generation
- YouTube transcript analysis
- Detailed success case database
- Copyright-free audio library
- Video processing with aspect ratio adjustment

## Installation

1. Clone the repository:
```bash
git clone https://github.com/pdytokyo/sns-ai-agent.git
cd sns-ai-agent
```

2. Install dependencies:
```bash
pip install -r requirements_enhanced.txt
```

3. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Running the Application

To run the application locally without authentication:

```bash
cd app
python main_final_integration.py
```

The application will be available at http://localhost:8000

## API Endpoints

### Client Management
- `POST /api/clients` - Create a new client
- `POST /api/selections` - Store client selections
- `POST /api/uploads/{client_id}` - Upload files

### Profile Generation
- `GET /api/generate-profiles/{client_id}` - Generate AI profiles
- `PUT /api/profiles/{profile_id}` - Update a profile
- `PUT /api/profiles/{profile_id}/select` - Select a profile

### Script Generation
- `GET /api/generate-scripts/{client_id}` - Generate AI scripts
- `PUT /api/scripts/{script_id}` - Update a script
- `PUT /api/scripts/{script_id}/select` - Select a script

### Audio Library
- `GET /api/audio-library` - Get copyright-free audio tracks
- `GET /api/audio/{audio_id}` - Stream an audio file

### Video Processing
- `POST /api/video-processing/{client_id}` - Process a video
- `GET /api/video/{result_id}` - Stream a processed video

## Database Schema

The application uses SQLite with the following tables:

- `clients` - Client information
- `selections` - Client selections for target attributes, purposes, and platforms
- `uploads` - Uploaded files
- `profiles` - AI-generated profiles
- `scripts` - AI-generated scripts
- `detailed_success_cases` - Database of successful social media content
- `client_video_transcripts` - YouTube video transcripts
- `transcript_analysis` - Analysis of video transcripts
- `copyright_free_audio` - Audio library
- `video_processing_results` - Results of video processing

## Testing the Application

1. Start the application:
```bash
cd app
python main_final_integration.py
```

2. Open a browser and navigate to:
```
http://localhost:8000
```

3. Test the API endpoints using curl:
```bash
curl -X GET http://localhost:8000/health
```

## Exposing the Application

To expose the application to the internet:

```bash
cd app
python main_final_integration.py
```

In a separate terminal:
```bash
# Using a tool like ngrok
ngrok http 8000
```

## Troubleshooting

- If you encounter issues with file uploads, ensure the `app/uploads` directory exists
- For OpenAI API errors, check your API key in the `.env` file
- If the application fails to start, check the console for error messages
