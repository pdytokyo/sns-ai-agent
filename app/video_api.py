from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse
import os
import sqlite3
import uuid
import json
from typing import List, Optional
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_processing import process_video

DB_PATH = "app.db"

router = APIRouter()

@router.post("/process-video/")
async def process_video_endpoint(
    client_id: str = Form(...),
    file_id: str = Form(...),
    aspect_ratio: str = Form("16:9"),
    silence_threshold: float = Form(0.02),
    min_clip_duration: float = Form(0.5),
    start_margin: float = Form(0.0),
    end_margin: float = Form(0.0)
):
    """
    Process a video with jet cut and aspect ratio conversion.
    
    Args:
        client_id: Client ID
        file_id: File ID of the uploaded video
        aspect_ratio: Aspect ratio for the output video (16:9, 1:1, or 9:16)
        silence_threshold: Threshold for detecting silence (0.0-1.0)
        min_clip_duration: Minimum duration of clips to keep (seconds)
        start_margin: Margin to add at the start of each clip (seconds)
        end_margin: Margin to add at the end of each clip (seconds)
        
    Returns:
        dict: Information about the processed video
    """
    if aspect_ratio not in ["16:9", "1:1", "9:16"]:
        raise HTTPException(status_code=400, detail="Invalid aspect ratio. Must be one of: 16:9, 1:1, 9:16")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT file_path, file_type FROM uploaded_files WHERE id = ? AND client_id = ?",
        (file_id, client_id)
    )
    
    file_info = cursor.fetchone()
    if not file_info:
        conn.close()
        raise HTTPException(status_code=404, detail="File not found or does not belong to this client")
    
    file_path, file_type = file_info
    
    if file_type != "video":
        conn.close()
        raise HTTPException(status_code=400, detail="File is not a video")
    
    try:
        result = process_video(
            input_path=file_path,
            aspect_ratio=aspect_ratio,
            silence_threshold=silence_threshold,
            min_clip_duration=min_clip_duration,
            start_margin=start_margin,
            end_margin=end_margin
        )
        
        edit_id = str(uuid.uuid4())
        cursor.execute('''
        INSERT INTO video_edits 
        (id, client_id, file_id, aspect_ratio, trim_start, trim_end, start_margin, end_margin, output_quality, output_format)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            edit_id,
            client_id,
            file_id,
            aspect_ratio,
            0.0,  # trim_start (not used in jet cut)
            0.0,  # trim_end (not used in jet cut)
            start_margin,
            end_margin,
            "high",  # output_quality
            "mp4"  # output_format
        ))
        
        conn.commit()
        
        result["edit_id"] = edit_id
        
        if "silent_segments" in result and isinstance(result["silent_segments"], list):
            result["silent_segments"] = [
                {"start": segment["start"], "end": segment["end"]} 
                for segment in result["silent_segments"]
            ]
        
        conn.close()
        return result
        
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

@router.get("/video-edits/{client_id}")
async def get_video_edits(client_id: str):
    """
    Get all video edits for a client.
    
    Args:
        client_id: Client ID
        
    Returns:
        list: List of video edits
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT ve.id, ve.file_id, uf.original_filename, ve.aspect_ratio, 
           ve.trim_start, ve.trim_end, ve.start_margin, ve.end_margin,
           ve.output_quality, ve.output_format, ve.created_at
    FROM video_edits ve
    JOIN uploaded_files uf ON ve.file_id = uf.id
    WHERE ve.client_id = ?
    ORDER BY ve.created_at DESC
    ''', (client_id,))
    
    edits = cursor.fetchall()
    conn.close()
    
    result = []
    for edit in edits:
        edit_id, file_id, original_filename, aspect_ratio, trim_start, trim_end, \
        start_margin, end_margin, output_quality, output_format, created_at = edit
        
        result.append({
            "id": edit_id,
            "file_id": file_id,
            "original_filename": original_filename,
            "aspect_ratio": aspect_ratio,
            "trim_start": trim_start,
            "trim_end": trim_end,
            "start_margin": start_margin,
            "end_margin": end_margin,
            "output_quality": output_quality,
            "output_format": output_format,
            "created_at": created_at
        })
    
    return result

@router.get("/video-edit/{edit_id}")
async def get_video_edit(edit_id: str):
    """
    Get details of a specific video edit.
    
    Args:
        edit_id: Edit ID
        
    Returns:
        dict: Video edit details
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT ve.id, ve.client_id, ve.file_id, uf.original_filename, uf.file_path,
           ve.aspect_ratio, ve.trim_start, ve.trim_end, ve.start_margin, ve.end_margin,
           ve.output_quality, ve.output_format, ve.created_at
    FROM video_edits ve
    JOIN uploaded_files uf ON ve.file_id = uf.id
    WHERE ve.id = ?
    ''', (edit_id,))
    
    edit = cursor.fetchone()
    if not edit:
        conn.close()
        raise HTTPException(status_code=404, detail="Video edit not found")
    
    edit_id, client_id, file_id, original_filename, file_path, aspect_ratio, \
    trim_start, trim_end, start_margin, end_margin, output_quality, output_format, created_at = edit
    
    cursor.execute('''
    SELECT output_path, original_duration, processed_duration, reduction_percentage, silent_segments
    FROM video_processing_results
    WHERE input_path = ?
    ORDER BY created_at DESC
    LIMIT 1
    ''', (file_path,))
    
    processing_result = cursor.fetchone()
    conn.close()
    
    result = {
        "id": edit_id,
        "client_id": client_id,
        "file_id": file_id,
        "original_filename": original_filename,
        "file_path": file_path,
        "aspect_ratio": aspect_ratio,
        "trim_start": trim_start,
        "trim_end": trim_end,
        "start_margin": start_margin,
        "end_margin": end_margin,
        "output_quality": output_quality,
        "output_format": output_format,
        "created_at": created_at
    }
    
    if processing_result:
        output_path, original_duration, processed_duration, reduction_percentage, silent_segments = processing_result
        
        result["processed_video_path"] = output_path
        result["original_duration"] = original_duration
        result["processed_duration"] = processed_duration
        result["reduction_percentage"] = reduction_percentage
        
        try:
            result["silent_segments"] = json.loads(silent_segments)
        except:
            result["silent_segments"] = []
    
    return result

@router.post("/update-video-edit/{edit_id}")
async def update_video_edit(
    edit_id: str,
    aspect_ratio: Optional[str] = Form(None),
    trim_start: Optional[float] = Form(None),
    trim_end: Optional[float] = Form(None),
    start_margin: Optional[float] = Form(None),
    end_margin: Optional[float] = Form(None),
    output_quality: Optional[str] = Form(None),
    output_format: Optional[str] = Form(None)
):
    """
    Update a video edit.
    
    Args:
        edit_id: Edit ID
        aspect_ratio: Aspect ratio for the output video (16:9, 1:1, or 9:16)
        trim_start: Start time for trimming (seconds)
        trim_end: End time for trimming (seconds)
        start_margin: Margin to add at the start of each clip (seconds)
        end_margin: Margin to add at the end of each clip (seconds)
        output_quality: Output quality (low, medium, high)
        output_format: Output format (mp4, webm)
        
    Returns:
        dict: Updated video edit details
    """
    if aspect_ratio and aspect_ratio not in ["16:9", "1:1", "9:16"]:
        raise HTTPException(status_code=400, detail="Invalid aspect ratio. Must be one of: 16:9, 1:1, 9:16")
    
    if output_quality and output_quality not in ["low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="Invalid output quality. Must be one of: low, medium, high")
    
    if output_format and output_format not in ["mp4", "webm"]:
        raise HTTPException(status_code=400, detail="Invalid output format. Must be one of: mp4, webm")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, client_id, file_id FROM video_edits WHERE id = ?", (edit_id,))
    edit = cursor.fetchone()
    if not edit:
        conn.close()
        raise HTTPException(status_code=404, detail="Video edit not found")
    
    _, client_id, file_id = edit
    
    cursor.execute("SELECT file_path FROM uploaded_files WHERE id = ?", (file_id,))
    file_path = cursor.fetchone()[0]
    
    update_fields = []
    update_values = []
    
    if aspect_ratio:
        update_fields.append("aspect_ratio = ?")
        update_values.append(aspect_ratio)
    
    if trim_start is not None:
        update_fields.append("trim_start = ?")
        update_values.append(trim_start)
    
    if trim_end is not None:
        update_fields.append("trim_end = ?")
        update_values.append(trim_end)
    
    if start_margin is not None:
        update_fields.append("start_margin = ?")
        update_values.append(start_margin)
    
    if end_margin is not None:
        update_fields.append("end_margin = ?")
        update_values.append(end_margin)
    
    if output_quality:
        update_fields.append("output_quality = ?")
        update_values.append(output_quality)
    
    if output_format:
        update_fields.append("output_format = ?")
        update_values.append(output_format)
    
    if not update_fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_query = f"UPDATE video_edits SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(edit_id)
    
    cursor.execute(update_query, update_values)
    conn.commit()
    
    if aspect_ratio or start_margin is not None or end_margin is not None:
        cursor.execute(
            "SELECT aspect_ratio, start_margin, end_margin FROM video_edits WHERE id = ?",
            (edit_id,)
        )
        current_params = cursor.fetchone()
        current_aspect_ratio, current_start_margin, current_end_margin = current_params
        
        aspect_ratio = aspect_ratio or current_aspect_ratio
        start_margin = start_margin if start_margin is not None else current_start_margin
        end_margin = end_margin if end_margin is not None else current_end_margin
        
        try:
            result = process_video(
                input_path=file_path,
                aspect_ratio=aspect_ratio,
                silence_threshold=0.02,  # Default
                min_clip_duration=0.5,  # Default
                start_margin=start_margin,
                end_margin=end_margin
            )
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
    
    conn.close()
    
    return await get_video_edit(edit_id)
