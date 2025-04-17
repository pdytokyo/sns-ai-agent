"""
Log Analyzer Script for SNS AI Agent

This script analyzes deployment logs to identify patterns of errors
and provides structured reports for automated analysis and fixing.
It works alongside the deployment_monitor.py script to provide
more detailed error analysis capabilities.
"""

import os
import re
import json
import logging
import argparse
from datetime import datetime
from collections import Counter, defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/log_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("log_analyzer")

ERROR_PATTERNS = {
    "missing_module": r"ModuleNotFoundError: No module named '([^']+)'",
    "import_error": r"ImportError: cannot import name '([^']+)' from '([^']+)'",
    "docker_size": r"Not enough space to unpack image, possibly exceeds maximum of (\d+)GB",
    "boot_timeout": r"Error R10 \(Boot timeout\)",
    "permission_denied": r"PermissionError: \[Errno 13\] Permission denied: '([^']+)'",
    "file_not_found": r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'",
    "syntax_error": r"SyntaxError: (.*) \(([^,]+), line (\d+)\)",
    "memory_error": r"MemoryError",
    "disk_quota": r"Disk quota exceeded",
}

class LogAnalyzer:
    """Analyzes deployment logs to identify error patterns and suggest fixes"""
    
    def __init__(self, log_file=None):
        """Initialize the log analyzer with an optional log file"""
        self.log_file = log_file
        self.log_content = ""
        self.errors = defaultdict(list)
        self.error_counts = Counter()
        self.suggestions = []
        
    def load_log(self, log_file=None):
        """Load log content from file"""
        if log_file:
            self.log_file = log_file
            
        if not self.log_file:
            logger.error("No log file specified")
            return False
            
        try:
            logger.info(f"Loading log file: {self.log_file}")
            with open(self.log_file, 'r') as f:
                self.log_content = f.read()
            return True
        except Exception as e:
            logger.error(f"Error loading log file: {str(e)}")
            return False
    
    def analyze(self):
        """Analyze log content for error patterns"""
        if not self.log_content:
            logger.warning("No log content to analyze")
            return
            
        logger.info("Analyzing logs for error patterns")
        
        self.errors = defaultdict(list)
        self.error_counts = Counter()
        self.suggestions = []
        
        for error_type, pattern in ERROR_PATTERNS.items():
            matches = re.finditer(pattern, self.log_content)
            for match in matches:
                self.errors[error_type].append(match)
                self.error_counts[error_type] += 1
        
        self._generate_suggestions()
        
        logger.info(f"Analysis complete. Found {sum(self.error_counts.values())} errors across {len(self.error_counts)} categories")
    
    def _generate_suggestions(self):
        """Generate fix suggestions based on identified errors"""
        if "missing_module" in self.errors:
            for match in self.errors["missing_module"]:
                module_name = match.group(1)
                self.suggestions.append({
                    "error_type": "missing_module",
                    "details": {"module": module_name},
                    "suggestion": f"Add '{module_name}' to requirements.txt and requirements-deploy.txt",
                    "fix_command": f"pip install {module_name} && echo '{module_name}' >> requirements.txt && echo '{module_name}' >> requirements-deploy.txt"
                })
        
        if "docker_size" in self.errors:
            self.suggestions.append({
                "error_type": "docker_size",
                "details": {"limit": self.errors["docker_size"][0].group(1) + "GB"},
                "suggestion": "Optimize Dockerfile to reduce image size",
                "fix_steps": [
                    "Use multi-stage builds",
                    "Remove unnecessary dependencies",
                    "Clean up package manager caches",
                    "Use --no-cache-dir with pip",
                    "Remove unnecessary files and directories"
                ]
            })
        
        if "boot_timeout" in self.errors:
            self.suggestions.append({
                "error_type": "boot_timeout",
                "suggestion": "Application is taking too long to start",
                "fix_steps": [
                    "Check for long-running initialization code",
                    "Ensure database migrations are efficient",
                    "Consider lazy-loading large resources",
                    "Increase boot timeout in fly.toml if necessary"
                ]
            })
            
        if "permission_denied" in self.errors:
            paths = [match.group(1) for match in self.errors["permission_denied"]]
            self.suggestions.append({
                "error_type": "permission_denied",
                "details": {"paths": paths},
                "suggestion": "Fix permission issues for paths",
                "fix_steps": [
                    "Ensure directories are created with proper permissions",
                    "Add directory creation commands to Dockerfile",
                    "Use volume mounts for persistent data"
                ]
            })
            
        if "file_not_found" in self.errors:
            paths = [match.group(1) for match in self.errors["file_not_found"]]
            self.suggestions.append({
                "error_type": "file_not_found",
                "details": {"paths": paths},
                "suggestion": "Create missing files or directories",
                "fix_steps": [
                    "Add directory creation commands to Dockerfile",
                    "Ensure all required files are included in the Docker image",
                    "Check for hardcoded paths that might not exist in production"
                ]
            })
    
    def get_report(self, format="text"):
        """Generate a report of the analysis results"""
        if format == "json":
            return self._get_json_report()
        else:
            return self._get_text_report()
    
    def _get_text_report(self):
        """Generate a text report of the analysis results"""
        report = []
        report.append("=" * 50)
        report.append(f"Log Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 50)
        
        if sum(self.error_counts.values()) == 0:
            report.append("No errors found in logs.")
            return "\n".join(report)
        
        report.append("\nError Summary:")
        for error_type, count in self.error_counts.items():
            report.append(f"  - {error_type}: {count} occurrences")
        
        if self.suggestions:
            report.append("\nSuggested Fixes:")
            for i, suggestion in enumerate(self.suggestions, 1):
                report.append(f"\n{i}. {suggestion['suggestion']} ({suggestion['error_type']})")
                if "fix_command" in suggestion:
                    report.append(f"   Command: {suggestion['fix_command']}")
                if "fix_steps" in suggestion:
                    report.append("   Steps:")
                    for step in suggestion["fix_steps"]:
                        report.append(f"    - {step}")
        
        return "\n".join(report)
    
    def _get_json_report(self):
        """Generate a JSON report of the analysis results"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "error_counts": dict(self.error_counts),
            "suggestions": self.suggestions,
            "total_errors": sum(self.error_counts.values())
        }
        return json.dumps(report, indent=2)
    
    def save_report(self, output_file, format="text"):
        """Save the report to a file"""
        try:
            report = self.get_report(format)
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            return False

def main():
    """Main function to run the log analyzer from command line"""
    parser = argparse.ArgumentParser(description="Analyze deployment logs for errors")
    parser.add_argument("log_file", help="Path to the log file to analyze")
    parser.add_argument("--output", "-o", help="Output file for the report")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text",
                        help="Output format (text or json)")
    args = parser.parse_args()
    
    os.makedirs("logs", exist_ok=True)
    
    analyzer = LogAnalyzer(args.log_file)
    if analyzer.load_log():
        analyzer.analyze()
        
        if args.output:
            analyzer.save_report(args.output, args.format)
        else:
            print(analyzer.get_report(args.format))
    
if __name__ == "__main__":
    main()
