"""
Automatic PR Creator Script

This script automatically creates a GitHub Pull Request with Dockerfile
optimizations when Docker image size issues are detected. It works with
GitHub Actions to create a fully automated CI/CD pipeline.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/auto_pr_creator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_pr_creator")

class AutoPRCreator:
    """Creates GitHub Pull Requests automatically for Dockerfile optimizations"""
    
    def __init__(self, repo=None, base_branch="main"):
        """Initialize the PR creator"""
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "pdytokyo/sns-ai-agent")
        self.base_branch = base_branch
        self.pr_branch = f"devin/{int(datetime.now().timestamp())}-docker-optimization"
        self.pr_title = "Optimize Dockerfile to reduce image size"
        self.pr_body = ""
        self.changed_files = []
    
    def check_gh_cli(self):
        """Check if GitHub CLI is installed and authenticated"""
        try:
            result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("GitHub CLI (gh) is not installed")
                return False
            
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("GitHub CLI is not authenticated")
                return False
            
            logger.info("GitHub CLI is installed and authenticated")
            return True
        except Exception as e:
            logger.error(f"Error checking GitHub CLI: {str(e)}")
            return False
    
    def create_branch(self):
        """Create a new branch for the PR"""
        try:
            logger.info(f"Creating branch {self.pr_branch} from {self.base_branch}")
            
            subprocess.run(["git", "checkout", self.base_branch], check=True)
            
            subprocess.run(["git", "pull", "origin", self.base_branch], check=True)
            
            subprocess.run(["git", "checkout", "-b", self.pr_branch], check=True)
            
            logger.info(f"Successfully created branch {self.pr_branch}")
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Error creating branch: {str(e)}")
            return False
    
    def optimize_dockerfile(self):
        """Run the Dockerfile optimizer"""
        try:
            from dockerfile_optimizer import DockerfileOptimizer
            
            logger.info("Running Dockerfile optimizer")
            optimizer = DockerfileOptimizer()
            
            if not optimizer.load_dockerfile():
                logger.error("Failed to load Dockerfile")
                return False
            
            if not optimizer.optimize():
                logger.warning("No optimizations were applied to the Dockerfile")
                return False
            
            if not optimizer.save_dockerfile():
                logger.error("Failed to save optimized Dockerfile")
                return False
            
            self.changed_files.append("Dockerfile")
            
            if os.path.exists(".dockerignore") and ".dockerignore" not in self.changed_files:
                self.changed_files.append(".dockerignore")
            
            logger.info(f"Successfully optimized Dockerfile with {len(optimizer.optimization_steps)} techniques")
            
            self.pr_body = f"""# Dockerfile Optimization

This PR automatically optimizes the Dockerfile to reduce the Docker image size below Fly.io's 8GB limit.


"""
            for i, step in enumerate(optimizer.optimization_steps, 1):
                self.pr_body += f"{i}. {step}\n"
            
            self.pr_body += """

This PR was automatically created by the CI/CD pipeline after detecting that the Docker image size exceeded Fly.io's 8GB limit. The optimization process is fully automated to ensure deployment success without manual intervention.

Link to Devin run: https://app.devin.ai/sessions/c9b10f8e87d141459c92061f4bbe4707
Requested by: yusuke_minari@pdytokyo.com
"""
            
            return True
        except Exception as e:
            logger.error(f"Error optimizing Dockerfile: {str(e)}")
            return False
    
    def commit_changes(self):
        """Commit the changes to the branch"""
        if not self.changed_files:
            logger.warning("No files to commit")
            return False
        
        try:
            logger.info(f"Committing changes to {len(self.changed_files)} files")
            
            for file in self.changed_files:
                subprocess.run(["git", "add", file], check=True)
            
            commit_message = "Optimize Dockerfile to reduce image size"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            
            subprocess.run(["git", "push", "-u", "origin", self.pr_branch], check=True)
            
            logger.info("Successfully committed and pushed changes")
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Error committing changes: {str(e)}")
            return False
    
    def create_pr(self):
        """Create a Pull Request"""
        try:
            logger.info(f"Creating PR from {self.pr_branch} to {self.base_branch}")
            
            pr_body_file = "pr_body.md"
            with open(pr_body_file, 'w') as f:
                f.write(self.pr_body)
            
            result = subprocess.run([
                "gh", "pr", "create",
                "--title", self.pr_title,
                "--body-file", pr_body_file,
                "--base", self.base_branch,
                "--head", self.pr_branch,
                "--repo", self.repo
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error creating PR: {result.stderr}")
                return None
            
            pr_url = result.stdout.strip()
            logger.info(f"Successfully created PR: {pr_url}")
            
            if os.path.exists(pr_body_file):
                os.remove(pr_body_file)
            
            return pr_url
        except Exception as e:
            logger.error(f"Error creating PR: {str(e)}")
            return None
    
    def run(self):
        """Run the complete PR creation process"""
        if not self.check_gh_cli():
            return False
        
        if not self.create_branch():
            return False
        
        if not self.optimize_dockerfile():
            return False
        
        if not self.commit_changes():
            return False
        
        pr_url = self.create_pr()
        if not pr_url:
            return False
        
        logger.info(f"Successfully created PR: {pr_url}")
        print(f"PR URL: {pr_url}")
        
        return True

def main():
    """Main function to run the auto PR creator"""
    parser = argparse.ArgumentParser(description="Automatically create a PR with Dockerfile optimizations")
    parser.add_argument("--repo", help="GitHub repository in owner/repo format")
    parser.add_argument("--base", default="main", help="Base branch for the PR")
    args = parser.parse_args()
    
    os.makedirs("logs", exist_ok=True)
    
    creator = AutoPRCreator(repo=args.repo, base_branch=args.base)
    if creator.run():
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
