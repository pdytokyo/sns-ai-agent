"""
Error Notification Script for SNS AI Agent

This script provides enhanced notification capabilities for deployment errors,
including structured error reports and integration with notification services.
It works alongside the deployment_monitor.py script to provide more
comprehensive error reporting.
"""

import os
import json
import logging
import requests
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/error_notification.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("error_notification")

class ErrorNotifier:
    """Handles error notifications for deployment issues"""
    
    def __init__(self, error_data=None):
        """Initialize the error notifier with optional error data"""
        self.error_data = error_data or {}
        self.notification_services = {
            "webhook": self._send_webhook_notification,
            "github_issue": self._create_github_issue,
            "github_comment": self._add_github_comment
        }
    
    def load_error_data(self, error_file):
        """Load error data from a JSON file"""
        try:
            logger.info(f"Loading error data from {error_file}")
            with open(error_file, 'r') as f:
                self.error_data = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading error data: {str(e)}")
            return False
    
    def set_error_data(self, error_data):
        """Set error data directly"""
        self.error_data = error_data
    
    def send_notification(self, service="webhook", **kwargs):
        """Send notification using the specified service"""
        if not self.error_data:
            logger.warning("No error data to send notification for")
            return False
        
        if service not in self.notification_services:
            logger.error(f"Unknown notification service: {service}")
            return False
        
        logger.info(f"Sending notification via {service}")
        return self.notification_services[service](**kwargs)
    
    def _send_webhook_notification(self, webhook_url=None, **kwargs):
        """Send notification to a webhook URL"""
        webhook_url = webhook_url or os.environ.get("NOTIFICATION_WEBHOOK")
        
        if not webhook_url:
            logger.error("No webhook URL provided")
            return False
        
        try:
            message = self._format_webhook_message()
            
            response = requests.post(
                webhook_url,
                json={"text": message, "detailed_error": self.error_data}
            )
            
            if response.status_code in (200, 201, 202, 204):
                logger.info("Webhook notification sent successfully")
                return True
            else:
                logger.error(f"Failed to send webhook notification: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending webhook notification: {str(e)}")
            return False
    
    def _create_github_issue(self, repo=None, token=None, **kwargs):
        """Create a GitHub issue for the error"""
        repo = repo or os.environ.get("GITHUB_REPOSITORY") or "pdytokyo/sns-ai-agent"
        token = token or os.environ.get("GITHUB_TOKEN")
        
        if not token:
            logger.error("No GitHub token provided")
            return False
        
        try:
            title = f"Deployment Error: {self._get_error_summary()}"
            body = self._format_github_issue_body()
            
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.post(
                f"https://api.github.com/repos/{repo}/issues",
                headers=headers,
                json={
                    "title": title,
                    "body": body,
                    "labels": ["deployment", "error", "auto-detected"]
                }
            )
            
            if response.status_code == 201:
                issue_data = response.json()
                logger.info(f"GitHub issue created successfully: {issue_data['html_url']}")
                return True
            else:
                logger.error(f"Failed to create GitHub issue: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating GitHub issue: {str(e)}")
            return False
    
    def _add_github_comment(self, pr_number=None, repo=None, token=None, **kwargs):
        """Add a comment to a GitHub PR about the error"""
        repo = repo or os.environ.get("GITHUB_REPOSITORY") or "pdytokyo/sns-ai-agent"
        token = token or os.environ.get("GITHUB_TOKEN")
        
        if not pr_number:
            logger.error("No PR number provided")
            return False
        
        if not token:
            logger.error("No GitHub token provided")
            return False
        
        try:
            body = self._format_github_comment_body()
            
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.post(
                f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
                headers=headers,
                json={"body": body}
            )
            
            if response.status_code == 201:
                comment_data = response.json()
                logger.info(f"GitHub comment added successfully: {comment_data['html_url']}")
                return True
            else:
                logger.error(f"Failed to add GitHub comment: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error adding GitHub comment: {str(e)}")
            return False
    
    def _format_webhook_message(self):
        """Format the error message for webhook notification"""
        error_summary = self._get_error_summary()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"⚠️ DEPLOYMENT ERROR DETECTED - {timestamp}\n\n"
        message += f"Error: {error_summary}\n\n"
        
        if "suggestions" in self.error_data and self.error_data["suggestions"]:
            message += "Suggested fixes:\n"
            for suggestion in self.error_data["suggestions"]:
                message += f"- {suggestion['suggestion']}\n"
        
        message += "\nAuto-fix workflow has been triggered."
        
        return message
    
    def _format_github_issue_body(self):
        """Format the issue body for GitHub"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body = f"## Deployment Error Detected\n\n"
        body += f"**Timestamp:** {timestamp}\n\n"
        
        body += "### Error Summary\n\n"
        if "error_counts" in self.error_data:
            for error_type, count in self.error_data["error_counts"].items():
                body += f"- **{error_type}:** {count} occurrences\n"
        else:
            body += f"- {self._get_error_summary()}\n"
        
        if "suggestions" in self.error_data and self.error_data["suggestions"]:
            body += "\n### Suggested Fixes\n\n"
            for suggestion in self.error_data["suggestions"]:
                body += f"#### {suggestion['suggestion']}\n\n"
                
                if "fix_steps" in suggestion:
                    body += "Steps:\n"
                    for step in suggestion["fix_steps"]:
                        body += f"- {step}\n"
                
                if "fix_command" in suggestion:
                    body += f"\nCommand: `{suggestion['fix_command']}`\n"
                
                body += "\n"
        
        body += "### Automatic Actions\n\n"
        body += "- Auto-fix workflow has been triggered\n"
        body += "- This issue was automatically created by the error notification system\n"
        
        return body
    
    def _format_github_comment_body(self):
        """Format the comment body for GitHub PR"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body = f"## ⚠️ Deployment Error Detected - {timestamp}\n\n"
        
        body += "### Error Summary\n\n"
        if "error_counts" in self.error_data:
            for error_type, count in self.error_data["error_counts"].items():
                body += f"- **{error_type}:** {count} occurrences\n"
        else:
            body += f"- {self._get_error_summary()}\n"
        
        if "suggestions" in self.error_data and self.error_data["suggestions"]:
            body += "\n### Suggested Fixes\n\n"
            for suggestion in self.error_data["suggestions"]:
                body += f"- {suggestion['suggestion']}\n"
        
        body += "\n### Automatic Actions\n\n"
        body += "- Auto-fix workflow has been triggered\n"
        body += "- This comment was automatically added by the error notification system\n"
        
        return body
    
    def _get_error_summary(self):
        """Get a summary of the error"""
        if "error_summary" in self.error_data:
            return self.error_data["error_summary"]
        
        if "error_counts" in self.error_data:
            error_types = list(self.error_data["error_counts"].keys())
            if error_types:
                return f"{len(error_types)} error types detected: {', '.join(error_types)}"
        
        return "Unknown error"

def main():
    """Main function to run the error notifier from command line"""
    parser = argparse.ArgumentParser(description="Send notifications for deployment errors")
    parser.add_argument("--error-file", "-e", help="Path to the error data JSON file")
    parser.add_argument("--service", "-s", choices=["webhook", "github_issue", "github_comment"],
                        default="webhook", help="Notification service to use")
    parser.add_argument("--webhook-url", "-w", help="Webhook URL for notifications")
    parser.add_argument("--repo", "-r", help="GitHub repository (owner/repo)")
    parser.add_argument("--token", "-t", help="GitHub token")
    parser.add_argument("--pr-number", "-p", type=int, help="GitHub PR number")
    args = parser.parse_args()
    
    os.makedirs("logs", exist_ok=True)
    
    notifier = ErrorNotifier()
    
    if args.error_file:
        if not notifier.load_error_data(args.error_file):
            return
    else:
        notifier.set_error_data({
            "error_summary": "Sample deployment error",
            "error_counts": {"missing_module": 1, "docker_size": 1},
            "suggestions": [
                {
                    "error_type": "missing_module",
                    "suggestion": "Add missing module to requirements",
                    "fix_command": "echo 'module_name' >> requirements.txt"
                },
                {
                    "error_type": "docker_size",
                    "suggestion": "Optimize Dockerfile to reduce image size",
                    "fix_steps": ["Use multi-stage builds", "Remove unnecessary dependencies"]
                }
            ]
        })
    
    kwargs = {
        "webhook_url": args.webhook_url,
        "repo": args.repo,
        "token": args.token,
        "pr_number": args.pr_number
    }
    
    notifier.send_notification(args.service, **kwargs)

if __name__ == "__main__":
    main()
