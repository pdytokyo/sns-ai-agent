"""
Health check route for SNS AI Agent application.
Provides endpoint to verify application status and dependencies.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import importlib
import os
import sqlite3
from typing import Dict, List, Optional

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict:
    """
    Health check endpoint to verify application status.
    Checks database connection, critical modules, and environment variables.
    
    Returns:
        Dict: Health status information
    """
    health_status = {
        "status": "healthy",
        "checks": {
            "database": check_database_connection(),
            "modules": check_critical_modules(),
            "environment": check_environment_variables(),
            "filesystem": check_filesystem_access()
        },
        "version": "1.0.0"
    }
    
    for check_name, check_result in health_status["checks"].items():
        if not check_result["status"]:
            health_status["status"] = "unhealthy"
            return health_status
    
    return health_status

def check_database_connection() -> Dict:
    """Check database connection."""
    result = {"status": True, "message": "Database connection successful"}
    
    try:
        db_path = os.getenv("DB_PATH", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        cursor.fetchone()
        conn.close()
    except Exception as e:
        result["status"] = False
        result["message"] = f"Database connection failed: {str(e)}"
    
    return result

def check_critical_modules() -> Dict:
    """Check if critical modules are available."""
    critical_modules = [
        "fastapi", "uvicorn", "openai", "whisper", 
        "moviepy", "librosa", "youtube_transcript_api"
    ]
    
    result = {"status": True, "message": "All critical modules available", "details": {}}
    
    for module_name in critical_modules:
        try:
            importlib.import_module(module_name)
            result["details"][module_name] = "available"
        except ImportError:
            result["status"] = False
            result["details"][module_name] = "missing"
    
    if not result["status"]:
        result["message"] = "Some critical modules are missing"
    
    return result

def check_environment_variables() -> Dict:
    """Check if required environment variables are set."""
    required_vars = ["OPENAI_API_KEY"]
    optional_vars = ["YOUTUBE_API_KEY", "DB_PATH"]
    
    result = {
        "status": True, 
        "message": "All required environment variables are set",
        "details": {}
    }
    
    for var in required_vars:
        if not os.getenv(var):
            result["status"] = False
            result["details"][var] = "missing"
        else:
            result["details"][var] = "set"
    
    for var in optional_vars:
        if not os.getenv(var):
            result["details"][var] = "not set (optional)"
        else:
            result["details"][var] = "set"
    
    if not result["status"]:
        result["message"] = "Some required environment variables are missing"
    
    return result

def check_filesystem_access() -> Dict:
    """Check if application has access to required directories."""
    required_dirs = ["app/static", "app/static/uploaded_videos", "logs"]
    
    result = {
        "status": True, 
        "message": "All required directories are accessible",
        "details": {}
    }
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                result["details"][dir_path] = "created"
            except Exception as e:
                result["status"] = False
                result["details"][dir_path] = f"failed to create: {str(e)}"
        elif not os.access(dir_path, os.W_OK):
            result["status"] = False
            result["details"][dir_path] = "not writable"
        else:
            result["details"][dir_path] = "accessible"
    
    if not result["status"]:
        result["message"] = "Some required directories are not accessible"
    
    return result
