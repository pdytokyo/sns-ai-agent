"""
Deployment Monitor Script

This script monitors the deployed application for errors and triggers
automatic fixes when issues are detected. It can be run as a scheduled
task or manually to verify deployment health.
"""

import os
import sys
import time
import json
import logging
import requests
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/deployment_monitor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("deployment_monitor")

APP_URL = "https://sns-ai-agent.fly.dev"
GITHUB_REPO = "pdytokyo/sns-ai-agent"
GITHUB_WORKFLOW = "ci_cd.yml"
CHECK_INTERVAL = 300  # 5 minutes
MAX_RETRIES = 3

def check_application_health():
    """Check if the application is responding properly"""
    try:
        logger.info(f"Checking application health at {APP_URL}")
        response = requests.get(f"{APP_URL}/health", timeout=10)
        
        if response.status_code == 200:
            logger.info("Application is healthy")
            return True, None
        else:
            logger.warning(f"Application returned status code {response.status_code}")
            return False, f"Unhealthy status code: {response.status_code}"
    except requests.RequestException as e:
        logger.error(f"Error connecting to application: {str(e)}")
        return False, str(e)

def check_fly_logs():
    """Check Fly.io logs for common errors"""
    try:
        logger.info("Checking Fly.io logs for errors")
        result = subprocess.run(
            ["flyctl", "logs", "--app", "sns-ai-agent", "--instance", "all"],
            capture_output=True, text=True, check=True
        )
        
        logs = result.stdout
        errors = []
        
        if "ModuleNotFoundError: No module named" in logs:
            import re
            match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", logs)
            if match:
                missing_module = match.group(1)
                errors.append(f"Missing module: {missing_module}")
        
        if "Not enough space to unpack image" in logs:
            errors.append("Docker image size exceeds limit")
        
        if "Error R10 (Boot timeout)" in logs:
            errors.append("Application boot timeout")
        
        return errors
    except subprocess.SubprocessError as e:
        logger.error(f"Error checking Fly.io logs: {str(e)}")
        return [f"Error checking logs: {str(e)}"]

def trigger_github_workflow():
    """Trigger GitHub Actions workflow for auto-fixing"""
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return False
    
    try:
        logger.info(f"Triggering GitHub workflow {GITHUB_WORKFLOW}")
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "ref": "main",
            "inputs": {"auto_fix": "true"}
        }
        
        response = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches",
            headers=headers,
            json=data
        )
        
        if response.status_code == 204:
            logger.info("Successfully triggered GitHub workflow")
            return True
        else:
            logger.error(f"Failed to trigger workflow: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error triggering GitHub workflow: {str(e)}")
        return False

def send_notification(message):
    """Send notification about deployment issues"""
    logger.info(f"NOTIFICATION: {message}")
    
    webhook_url = os.environ.get("NOTIFICATION_WEBHOOK")
    if webhook_url:
        try:
            requests.post(webhook_url, json={"text": message})
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

def main():
    """Main monitoring function"""
    logger.info("Starting deployment monitor")
    
    os.makedirs("logs", exist_ok=True)
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        is_healthy, error = check_application_health()
        
        if is_healthy:
            logger.info("Application is running correctly")
            break
        
        logger.warning(f"Application health check failed: {error}")
        
        log_errors = check_fly_logs()
        
        if log_errors:
            error_message = f"Detected errors in logs: {', '.join(log_errors)}"
            logger.error(error_message)
            
            if trigger_github_workflow():
                notification = f"Deployment issues detected: {error_message}. Auto-fix workflow triggered."
            else:
                notification = f"Deployment issues detected: {error_message}. Failed to trigger auto-fix workflow."
            
            send_notification(notification)
        else:
            logger.warning("No specific errors found in logs")
        
        retry_count += 1
        if retry_count < MAX_RETRIES:
            wait_time = retry_count * 60  # Increasing wait time
            logger.info(f"Waiting {wait_time} seconds before retry {retry_count+1}/{MAX_RETRIES}")
            time.sleep(wait_time)
    
    if retry_count == MAX_RETRIES:
        logger.error("Maximum retry attempts reached. Application remains unhealthy.")
        send_notification("CRITICAL: Application remains unhealthy after maximum retry attempts")

if __name__ == "__main__":
    main()
