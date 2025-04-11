import os
import subprocess
import tempfile
import numpy as np
import json
from datetime import datetime
import uuid
import sqlite3

try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: moviepy not installed. Using mock implementation.")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("Warning: librosa not installed. Using mock implementation.")

DB_PATH = "app.db"

class VideoProcessor:
    """Class for video processing operations including jet cut and aspect ratio conversion."""
    
    def __init__(self, input_path=None, output_dir="app/uploads/processed"):
        """Initialize the video processor."""
        self.input_path = input_path
        self.output_dir = output_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.silence_threshold = 0.02
        self.chunk_duration = 0.1  # seconds
        self.min_clip_duration = 0.5  # seconds
        self.start_margin = 0.0  # seconds
        self.end_margin = 0.0  # seconds
        
    def set_parameters(self, silence_threshold=None, chunk_duration=None, 
                      min_clip_duration=None, start_margin=None, end_margin=None):
        """Set processing parameters."""
        if silence_threshold is not None:
            self.silence_threshold = silence_threshold
        if chunk_duration is not None:
            self.chunk_duration = chunk_duration
        if min_clip_duration is not None:
            self.min_clip_duration = min_clip_duration
        if start_margin is not None:
            self.start_margin = start_margin
        if end_margin is not None:
            self.end_margin = end_margin
    
    def jet_cut(self, input_path=None, output_path=None, aspect_ratio="16:9"):
        """
        Perform jet cut on a video (remove silent parts).
        
        Args:
            input_path: Path to input video file
            output_path: Path to output video file
            aspect_ratio: Aspect ratio for the output video (16:9, 1:1, or 9:16)
            
        Returns:
            dict: Information about the processed video
        """
        if input_path:
            self.input_path = input_path
            
        if not self.input_path:
            raise ValueError("Input path not specified")
            
        if not output_path:
            filename = os.path.basename(self.input_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(self.output_dir, f"{name}_jetcut_{aspect_ratio.replace(':', '_')}{ext}")
        
        if not MOVIEPY_AVAILABLE or not LIBROSA_AVAILABLE:
            print(f"Mock jet cut: {self.input_path} -> {output_path}")
            print(f"Parameters: silence_threshold={self.silence_threshold}, chunk_duration={self.chunk_duration}")
            print(f"Margins: start={self.start_margin}s, end={self.end_margin}s")
            print(f"Aspect ratio: {aspect_ratio}")
            
            result = {
                "input_path": self.input_path,
                "output_path": output_path,
                "original_duration": 60.0,  # Mock 1 minute video
                "processed_duration": 45.0,  # Mock 45 seconds after processing
                "reduction_percentage": 25.0,
                "silent_segments": [
                    {"start": 10.2, "end": 15.3},
                    {"start": 25.7, "end": 30.1},
                    {"start": 45.5, "end": 50.0}
                ],
                "aspect_ratio": aspect_ratio,
                "start_margin": self.start_margin,
                "end_margin": self.end_margin
            }
            
            self._store_processing_result(result)
            
            return result
        
        try:
            video = VideoFileClip(self.input_path)
            original_duration = video.duration
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            subprocess.call([
                "ffmpeg", "-i", self.input_path, 
                "-q:a", "0", "-map", "a", temp_audio_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            y, sr = librosa.load(temp_audio_path, sr=None)
            
            energy = librosa.feature.rms(y=y, frame_length=int(self.chunk_duration * sr), hop_length=int(self.chunk_duration * sr))[0]
            
            silent_segments = []
            is_silent = False
            silent_start = 0
            
            for i, e in enumerate(energy):
                time = i * self.chunk_duration
                
                if e < self.silence_threshold and not is_silent:
                    is_silent = True
                    silent_start = time
                elif e >= self.silence_threshold and is_silent:
                    is_silent = False
                    silent_end = time
                    
                    if silent_end - silent_start >= self.min_clip_duration:
                        silent_segments.append((silent_start, silent_end))
            
            if is_silent:
                silent_end = len(energy) * self.chunk_duration
                if silent_end - silent_start >= self.min_clip_duration:
                    silent_segments.append((silent_start, silent_end))
            
            if not silent_segments:
                processed_video = video
            else:
                clips = []
                last_end = 0
                
                for start, end in silent_segments:
                    if start > last_end:
                        clip = video.subclip(last_end, start)
                        clips.append(clip)
                    last_end = end
                
                if last_end < video.duration:
                    clip = video.subclip(last_end, video.duration)
                    clips.append(clip)
                
                if clips:
                    processed_video = concatenate_videoclips(clips)
                else:
                    processed_video = video
            
            if self.start_margin > 0 or self.end_margin > 0:
                if self.start_margin > 0 and processed_video.duration > self.start_margin:
                    start_clip = processed_video.subclip(0, self.start_margin)
                    rest_clip = processed_video.subclip(0, processed_video.duration)
                    processed_video = concatenate_videoclips([start_clip, rest_clip])
                
                if self.end_margin > 0 and processed_video.duration > self.end_margin:
                    end_clip = processed_video.subclip(processed_video.duration - self.end_margin, processed_video.duration)
                    rest_clip = processed_video.subclip(0, processed_video.duration)
                    processed_video = concatenate_videoclips([rest_clip, end_clip])
            
            if aspect_ratio != "16:9":
                width, height = processed_video.size
                
                if aspect_ratio == "1:1":
                    new_width = min(width, height)
                    new_height = new_width
                    
                    x1 = (width - new_width) // 2
                    y1 = (height - new_height) // 2
                    processed_video = processed_video.crop(x1=x1, y1=y1, width=new_width, height=new_height)
                    
                elif aspect_ratio == "9:16":
                    if width / height > 9 / 16:
                        new_width = int(height * 9 / 16)
                        new_height = height
                        
                        x1 = (width - new_width) // 2
                        y1 = 0
                        processed_video = processed_video.crop(x1=x1, y1=y1, width=new_width, height=new_height)
                    else:
                        new_width = width
                        new_height = int(width * 16 / 9)
                        
                        x1 = 0
                        y1 = (height - new_height) // 2
                        processed_video = processed_video.crop(x1=x1, y1=y1, width=new_width, height=new_height)
            
            processed_video.write_videofile(output_path)
            
            processed_duration = processed_video.duration
            reduction_percentage = (original_duration - processed_duration) / original_duration * 100
            
            video.close()
            processed_video.close()
            os.unlink(temp_audio_path)
            
            result = {
                "input_path": self.input_path,
                "output_path": output_path,
                "original_duration": original_duration,
                "processed_duration": processed_duration,
                "reduction_percentage": reduction_percentage,
                "silent_segments": [{"start": start, "end": end} for start, end in silent_segments],
                "aspect_ratio": aspect_ratio,
                "start_margin": self.start_margin,
                "end_margin": self.end_margin
            }
            
            self._store_processing_result(result)
            
            return result
            
        except Exception as e:
            print(f"Error in jet_cut: {str(e)}")
            if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            
            raise
    
    def _store_processing_result(self, result):
        """Store video processing result in the database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_processing_results (
                id TEXT PRIMARY KEY,
                input_path TEXT NOT NULL,
                output_path TEXT NOT NULL,
                original_duration REAL,
                processed_duration REAL,
                reduction_percentage REAL,
                silent_segments TEXT,
                aspect_ratio TEXT,
                start_margin REAL,
                end_margin REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            silent_segments_json = json.dumps(result["silent_segments"])
            
            result_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO video_processing_results 
            (id, input_path, output_path, original_duration, processed_duration, 
             reduction_percentage, silent_segments, aspect_ratio, start_margin, end_margin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                result["input_path"],
                result["output_path"],
                result["original_duration"],
                result["processed_duration"],
                result["reduction_percentage"],
                silent_segments_json,
                result["aspect_ratio"],
                result["start_margin"],
                result["end_margin"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error storing processing result: {str(e)}")

def process_video(input_path, output_path=None, aspect_ratio="16:9", 
                 silence_threshold=0.02, chunk_duration=0.1, 
                 min_clip_duration=0.5, start_margin=0.0, end_margin=0.0):
    """
    Process a video with jet cut and aspect ratio conversion.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output video file (optional)
        aspect_ratio: Aspect ratio for the output video (16:9, 1:1, or 9:16)
        silence_threshold: Threshold for detecting silence (0.0-1.0)
        chunk_duration: Duration of audio chunks for analysis (seconds)
        min_clip_duration: Minimum duration of clips to keep (seconds)
        start_margin: Margin to add at the start of each clip (seconds)
        end_margin: Margin to add at the end of each clip (seconds)
        
    Returns:
        dict: Information about the processed video
    """
    processor = VideoProcessor()
    processor.set_parameters(
        silence_threshold=silence_threshold,
        chunk_duration=chunk_duration,
        min_clip_duration=min_clip_duration,
        start_margin=start_margin,
        end_margin=end_margin
    )
    
    return processor.jet_cut(input_path, output_path, aspect_ratio)

if __name__ == "__main__":
    sample_video = "app/uploads/sample.mp4"
    if os.path.exists(sample_video):
        print(f"Processing sample video: {sample_video}")
        result = process_video(
            sample_video,
            aspect_ratio="16:9",
            silence_threshold=0.02,
            start_margin=0.5,
            end_margin=1.0
        )
        print(f"Processing complete. Output: {result['output_path']}")
        print(f"Original duration: {result['original_duration']:.2f}s")
        print(f"Processed duration: {result['processed_duration']:.2f}s")
        print(f"Reduction: {result['reduction_percentage']:.2f}%")
    else:
        print(f"Sample video not found: {sample_video}")
        print("This module provides video processing functionality including:")
        print("- Jet cut (removing silent parts)")
        print("- Aspect ratio conversion (16:9, 1:1, 9:16)")
        print("- Margin adjustment")
