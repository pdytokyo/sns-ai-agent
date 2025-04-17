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
import traceback
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/deployment_monitor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("deployment_monitor")

class JsonFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
    
    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "path": record.pathname,
                "line": record.lineno
            }
            
            if hasattr(record, 'error_data'):
                log_entry["error_data"] = record.error_data
                
            if record.exc_info:
                log_entry["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                    "traceback": traceback.format_exception(*record.exc_info)
                }
            
            self.stream.write(json.dumps(log_entry) + '\n')
            self.flush()
        except Exception:
            self.handleError(record)

os.makedirs("logs", exist_ok=True)

json_handler = JsonFileHandler("logs/deployment_monitor.json")
logger.addHandler(json_handler)

APP_URL = "https://sns-ai-agent.fly.dev"
GITHUB_REPO = "pdytokyo/sns-ai-agent"
GITHUB_WORKFLOW = "ci_cd.yml"
CHECK_INTERVAL = 300  # 5 minutes
MAX_RETRIES = 3
LOG_DIR = Path("logs")

ERROR_PATTERNS = {
    "missing_module": r"ModuleNotFoundError: No module named '([^']+)'",
    "import_error": r"ImportError: cannot import name '([^']+)' from '([^']+)'",
    "docker_size": r"Not enough space to unpack image, possibly exceeds maximum of (\d+)GB",
    "boot_timeout": r"Error R10 \(Boot timeout\)",
    "permission_denied": r"PermissionError: \[Errno 13\] Permission denied: '([^']+)'",
    "file_not_found": r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'",
}

def check_application_health():
    """Check if the application is responding properly"""
    try:
        logger.info(f"Checking application health at {APP_URL}")
        response = requests.get(f"{APP_URL}/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            logger.info("Application is healthy", extra={"error_data": health_data})
            return True, None
        else:
            logger.warning(f"Application returned status code {response.status_code}", 
                          extra={"error_data": {"status_code": response.status_code}})
            return False, f"Unhealthy status code: {response.status_code}"
    except requests.RequestException as e:
        logger.error(f"Error connecting to application: {str(e)}", 
                    exc_info=True, 
                    extra={"error_data": {"error_type": "connection_error"}})
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
        error_details = {}
        
        log_file = LOG_DIR / f"fly_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w') as f:
            f.write(logs)
        
        import re
        for error_type, pattern in ERROR_PATTERNS.items():
            matches = re.finditer(pattern, logs)
            for match in matches:
                if error_type == "missing_module":
                    missing_module = match.group(1)
                    errors.append(f"Missing module: {missing_module}")
                    error_details[error_type] = error_details.get(error_type, []) + [missing_module]
                elif error_type == "docker_size":
                    size_limit = match.group(1)
                    errors.append(f"Docker image size exceeds {size_limit}GB limit")
                    error_details[error_type] = size_limit
                elif error_type == "import_error":
                    symbol = match.group(1)
                    module = match.group(2)
                    errors.append(f"Import error: cannot import {symbol} from {module}")
                    error_details[error_type] = error_details.get(error_type, []) + [{"symbol": symbol, "module": module}]
                elif error_type in ["permission_denied", "file_not_found"]:
                    path = match.group(1)
                    errors.append(f"{error_type.replace('_', ' ').title()}: {path}")
                    error_details[error_type] = error_details.get(error_type, []) + [path]
                else:
                    errors.append(f"Error: {error_type}")
                    error_details[error_type] = True
        
        if errors:
            logger.warning("Found errors in Fly.io logs", 
                          extra={"error_data": {"errors": errors, "details": error_details}})
        
        return errors, error_details
    except subprocess.SubprocessError as e:
        logger.error(f"Error checking Fly.io logs: {str(e)}", 
                    exc_info=True,
                    extra={"error_data": {"error_type": "subprocess_error"}})
        return [f"Error checking logs: {str(e)}"], {"subprocess_error": str(e)}

def analyze_logs():
    """Analyze logs using the log analyzer script"""
    try:
        logger.info("Running log analyzer")
        
        log_files = list(LOG_DIR.glob("fly_logs_*.log"))
        if not log_files:
            logger.warning("No log files found for analysis")
            return None
        
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        
        from scripts.log_analyzer import LogAnalyzer
        analyzer = LogAnalyzer(str(latest_log))
        if analyzer.load_log():
            analyzer.analyze()
            
            report_file = LOG_DIR / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            analyzer.save_report(str(report_file), format="json")
            
            with open(report_file, 'r') as f:
                report = json.load(f)
            
            logger.info(f"Log analysis complete", extra={"error_data": report})
            return report
        else:
            logger.error("Failed to load log file for analysis")
            return None
    except Exception as e:
        logger.error(f"Error analyzing logs: {str(e)}", exc_info=True)
        return None

def trigger_github_workflow(error_details=None):
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
        
        inputs = {"auto_fix": "true"}
        if error_details:
            for key, value in error_details.items():
                if isinstance(value, list):
                    inputs[f"error_{key}"] = ",".join(str(v) for v in value)
                else:
                    inputs[f"error_{key}"] = str(value)
        
        data = {
            "ref": "main",
            "inputs": inputs
        }
        
        response = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches",
            headers=headers,
            json=data
        )
        
        if response.status_code == 204:
            logger.info("Successfully triggered GitHub workflow", 
                       extra={"error_data": {"inputs": inputs}})
            return True
        else:
            logger.error(f"Failed to trigger workflow: {response.status_code} - {response.text}", 
                        extra={"error_data": {"status_code": response.status_code, "response": response.text}})
            return False
    except Exception as e:
        logger.error(f"Error triggering GitHub workflow: {str(e)}", exc_info=True)
        return False

def send_notification(message, error_details=None):
    """Send notification about deployment issues"""
    logger.info(f"NOTIFICATION: {message}", extra={"error_data": error_details})
    
    try:
        from scripts.error_notification import ErrorNotifier
        
        error_data = {
            "error_summary": message,
            "timestamp": datetime.now().isoformat(),
            "error_details": error_details
        }
        
        if error_details and "missing_module" in error_details:
            modules = error_details["missing_module"]
            if isinstance(modules, list):
                error_data["suggestions"] = [
                    {
                        "error_type": "missing_module",
                        "suggestion": f"Add missing module(s): {', '.join(modules)}",
                        "fix_command": f"pip install {' '.join(modules)}"
                    }
                ]
        
        notifier = ErrorNotifier(error_data)
        
        webhook_url = os.environ.get("NOTIFICATION_WEBHOOK")
        if webhook_url:
            notifier.send_notification("webhook", webhook_url=webhook_url)
        
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            notifier.send_notification("github_issue", token=github_token)
    except Exception as e:
        logger.error(f"Error using enhanced notification: {str(e)}", exc_info=True)
        
        webhook_url = os.environ.get("NOTIFICATION_WEBHOOK")
        if webhook_url:
            try:
                requests.post(webhook_url, json={"text": message})
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}", exc_info=True)

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
        
        log_errors, error_details = check_fly_logs()
        
        if log_errors:
            error_message = f"Detected errors in logs: {', '.join(log_errors)}"
            logger.error(error_message, extra={"error_data": error_details})
            
            analysis_report = analyze_logs()
            
            if trigger_github_workflow(error_details):
                notification = f"Deployment issues detected: {error_message}. Auto-fix workflow triggered."
            else:
                notification = f"Deployment issues detected: {error_message}. Failed to trigger auto-fix workflow."
            
            send_notification(notification, error_details)
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
