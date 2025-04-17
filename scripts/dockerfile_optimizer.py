"""
Dockerfile Optimizer Script

This script automatically optimizes a Dockerfile to reduce image size
when the Docker image exceeds Fly.io's 8GB limit. It implements various
optimization techniques and can be run automatically by GitHub Actions.
"""

import os
import re
import sys
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dockerfile_optimizer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dockerfile_optimizer")

class DockerfileOptimizer:
    """Optimizes Dockerfile to reduce image size"""
    
    def __init__(self, dockerfile_path="Dockerfile"):
        """Initialize the optimizer with the path to the Dockerfile"""
        self.dockerfile_path = dockerfile_path
        self.original_content = ""
        self.optimized_content = ""
        self.optimization_steps = []
        
    def load_dockerfile(self):
        """Load the Dockerfile content"""
        try:
            logger.info(f"Loading Dockerfile from {self.dockerfile_path}")
            with open(self.dockerfile_path, 'r') as f:
                self.original_content = f.read()
            return True
        except Exception as e:
            logger.error(f"Error loading Dockerfile: {str(e)}")
            return False
    
    def save_dockerfile(self, backup=True):
        """Save the optimized Dockerfile"""
        if not self.optimized_content:
            logger.warning("No optimized content to save")
            return False
        
        try:
            if backup:
                backup_path = f"{self.dockerfile_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                logger.info(f"Creating backup at {backup_path}")
                with open(backup_path, 'w') as f:
                    f.write(self.original_content)
            
            logger.info(f"Saving optimized Dockerfile to {self.dockerfile_path}")
            with open(self.dockerfile_path, 'w') as f:
                f.write(self.optimized_content)
            
            return True
        except Exception as e:
            logger.error(f"Error saving Dockerfile: {str(e)}")
            return False
    
    def optimize(self):
        """Apply all optimization techniques"""
        if not self.original_content:
            if not self.load_dockerfile():
                return False
        
        self.optimized_content = self.original_content
        self.optimization_steps = []
        
        self._use_slim_base_image()
        self._add_no_cache_dir_to_pip()
        self._optimize_apt_get()
        self._use_multi_stage_build()
        self._remove_unnecessary_files()
        self._optimize_copy_commands()
        self._add_dockerignore_entries()
        
        if self.optimization_steps:
            logger.info(f"Applied {len(self.optimization_steps)} optimization techniques")
            for i, step in enumerate(self.optimization_steps, 1):
                logger.info(f"  {i}. {step}")
        else:
            logger.warning("No optimizations were applied")
        
        return len(self.optimization_steps) > 0
    
    def _use_slim_base_image(self):
        """Use a slim base image to reduce size"""
        if re.search(r'FROM\s+python:.*-slim', self.optimized_content):
            logger.info("Already using slim base image")
            return
        
        new_content = re.sub(
            r'FROM\s+python:(\d+\.\d+)',
            r'FROM python:\1-slim',
            self.optimized_content
        )
        
        if new_content != self.optimized_content:
            self.optimized_content = new_content
            self.optimization_steps.append("Switched to slim base image")
            logger.info("Switched to slim base image")
    
    def _add_no_cache_dir_to_pip(self):
        """Add --no-cache-dir to pip install commands"""
        if "--no-cache-dir" in self.optimized_content:
            pip_installs = re.findall(r'pip\s+install\s+(?!.*--no-cache-dir).*', self.optimized_content)
            if not pip_installs:
                logger.info("All pip install commands already use --no-cache-dir")
                return
        
        new_content = re.sub(
            r'pip\s+install\s+(?!.*--no-cache-dir)(.*)',
            r'pip install --no-cache-dir \1',
            self.optimized_content
        )
        
        if new_content != self.optimized_content:
            self.optimized_content = new_content
            self.optimization_steps.append("Added --no-cache-dir to pip install commands")
            logger.info("Added --no-cache-dir to pip install commands")
    
    def _optimize_apt_get(self):
        """Optimize apt-get commands"""
        if "apt-get" not in self.optimized_content:
            return
        
        if "apt-get clean" in self.optimized_content and "rm -rf /var/lib/apt/lists/*" in self.optimized_content:
            logger.info("apt-get commands already optimized")
            return
        
        apt_pattern = r'(RUN\s+apt-get\s+update.*?(?:apt-get\s+install|apt-get\s+-y\s+install).*?)(?:\n\s*RUN|\n\s*$)'
        
        def optimize_apt(match):
            apt_cmd = match.group(1)
            if "apt-get clean" in apt_cmd and "rm -rf /var/lib/apt/lists/*" in apt_cmd:
                return apt_cmd
            
            if "--no-install-recommends" not in apt_cmd:
                apt_cmd = apt_cmd.replace("apt-get install", "apt-get install --no-install-recommends")
            
            apt_cmd += " \\\n    && apt-get clean \\\n    && rm -rf /var/lib/apt/lists/*"
            return apt_cmd
        
        new_content = re.sub(apt_pattern, optimize_apt, self.optimized_content, flags=re.DOTALL)
        
        if new_content != self.optimized_content:
            self.optimized_content = new_content
            self.optimization_steps.append("Optimized apt-get commands with cleaning steps")
            logger.info("Optimized apt-get commands with cleaning steps")
    
    def _use_multi_stage_build(self):
        """Convert to multi-stage build if not already using it"""
        if re.search(r'FROM\s+.*\s+AS\s+', self.optimized_content):
            logger.info("Already using multi-stage build")
            return
        
        if "python" not in self.optimized_content.lower():
            logger.info("Not a Python application, skipping multi-stage build")
            return
        
        base_image_match = re.search(r'FROM\s+([^\s]+)', self.optimized_content)
        if not base_image_match:
            logger.warning("Could not extract base image, skipping multi-stage build")
            return
        
        base_image = base_image_match.group(1)
        
        build_stage = f"""FROM {base_image} AS builder

WORKDIR /build

COPY requirements*.txt ./

RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

COPY . .

"""
        
        final_stage = f"""FROM {base_image}

WORKDIR /app

COPY --from=builder /build/app ./app
COPY --from=builder /build/*.py ./
COPY --from=builder /build/fly.toml ./
COPY --from=builder /build/Procfile ./

COPY --from=builder /build/requirements-deploy.txt ./
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements-deploy.txt

RUN mkdir -p app/static/uploaded_videos app/static/output logs

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080
CMD cd app && uvicorn main:app --host 0.0.0.0 --port $PORT
"""
        
        if "WORKDIR /app" in self.optimized_content and "CMD" in self.optimized_content:
            self.optimized_content = build_stage + final_stage
            self.optimization_steps.append("Converted to multi-stage build")
            logger.info("Converted to multi-stage build")
        else:
            logger.warning("Dockerfile structure is too different, skipping multi-stage build")
    
    def _remove_unnecessary_files(self):
        """Add commands to remove unnecessary files"""
        if "rm -rf" in self.optimized_content and any(x in self.optimized_content for x in [".git", "__pycache__", "*.pyc"]):
            logger.info("Already removing unnecessary files")
            return
        
        last_run_match = re.search(r'(RUN\s+.*?)(\n\s*(?:CMD|ENTRYPOINT|EXPOSE|ENV|VOLUME)|\Z)', self.optimized_content, re.DOTALL)
        if not last_run_match:
            cmd_match = re.search(r'\n\s*(CMD|ENTRYPOINT)', self.optimized_content)
            if not cmd_match:
                logger.warning("Could not find a suitable place to add cleanup commands")
                return
            
            insertion_point = cmd_match.start()
            cleanup_cmd = "\n# Remove unnecessary files to reduce image size\nRUN find /app -type d -name __pycache__ -exec rm -rf {} +\n"
            
            self.optimized_content = (
                self.optimized_content[:insertion_point] + 
                cleanup_cmd + 
                self.optimized_content[insertion_point:]
            )
        else:
            last_run = last_run_match.group(1)
            after_run = last_run_match.group(2)
            
            if last_run.strip().endswith("\\"):
                cleanup_cmd = " \\\n    && find /app -type d -name __pycache__ -exec rm -rf {} +"
            else:
                cleanup_cmd = " && find /app -type d -name __pycache__ -exec rm -rf {} +"
            
            self.optimized_content = (
                self.optimized_content[:last_run_match.start()] + 
                last_run + cleanup_cmd + 
                after_run + 
                self.optimized_content[last_run_match.end():]
            )
        
        self.optimization_steps.append("Added commands to remove unnecessary files")
        logger.info("Added commands to remove unnecessary files")
    
    def _optimize_copy_commands(self):
        """Optimize COPY commands to be more specific"""
        if "COPY . ." in self.optimized_content:
            specific_copy = """# Copy only necessary files
COPY app/ ./app/
COPY *.py ./
COPY fly.toml ./
COPY Procfile ./
"""
            new_content = self.optimized_content.replace("COPY . .", specific_copy)
            
            if new_content != self.optimized_content:
                self.optimized_content = new_content
                self.optimization_steps.append("Replaced generic COPY with specific file copies")
                logger.info("Replaced generic COPY with specific file copies")
    
    def _add_dockerignore_entries(self):
        """Ensure .dockerignore has necessary entries"""
        dockerignore_path = ".dockerignore"
        required_entries = [
            "# Git",
            ".git",
            ".gitignore",
            "",
            "# Python",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "env/",
            "build/",
            "develop-eggs/",
            "dist/",
            "downloads/",
            "eggs/",
            ".eggs/",
            "lib/",
            "lib64/",
            "parts/",
            "sdist/",
            "var/",
            "*.egg-info/",
            ".installed.cfg",
            "*.egg",
            "",
            "# Virtual Environment",
            "venv/",
            "ENV/",
            "",
            "# IDE",
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            "",
            "# Local development",
            ".env.local",
            ".env.development.local",
            ".env.test.local",
            ".env.production.local",
            "",
            "# Large files and directories",
            "*.MP4",
            "*.mp4",
            "*.wav",
            "*.mp3",
            "uploaded_videos/",
            "output/",
            "logs/",
        ]
        
        try:
            if os.path.exists(dockerignore_path):
                with open(dockerignore_path, 'r') as f:
                    current_content = f.read()
                
                missing_entries = []
                for entry in required_entries:
                    if entry and entry not in current_content:
                        missing_entries.append(entry)
                
                if not missing_entries:
                    logger.info(".dockerignore already has all necessary entries")
                    return
                
                with open(dockerignore_path, 'a') as f:
                    f.write("\n# Added by Dockerfile optimizer\n")
                    for entry in missing_entries:
                        f.write(f"{entry}\n")
            else:
                with open(dockerignore_path, 'w') as f:
                    for entry in required_entries:
                        f.write(f"{entry}\n")
            
            self.optimization_steps.append("Updated .dockerignore with necessary entries")
            logger.info("Updated .dockerignore with necessary entries")
        except Exception as e:
            logger.error(f"Error updating .dockerignore: {str(e)}")
    
    def check_image_size(self):
        """Build and check the Docker image size"""
        try:
            logger.info("Building Docker image to check size")
            image_tag = f"size-check-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            build_cmd = ["docker", "build", "-t", image_tag, "."]
            build_result = subprocess.run(build_cmd, capture_output=True, text=True)
            
            if build_result.returncode != 0:
                logger.error(f"Error building Docker image: {build_result.stderr}")
                return None
            
            size_cmd = ["docker", "images", image_tag, "--format", "{{.Size}}"]
            size_result = subprocess.run(size_cmd, capture_output=True, text=True)
            
            if size_result.returncode != 0:
                logger.error(f"Error getting image size: {size_result.stderr}")
                return None
            
            image_size = size_result.stdout.strip()
            logger.info(f"Docker image size: {image_size}")
            
            size_value = 0
            if "GB" in image_size:
                size_value = float(image_size.replace("GB", "").strip()) * 1024
            elif "MB" in image_size:
                size_value = float(image_size.replace("MB", "").strip())
            elif "KB" in image_size:
                size_value = float(image_size.replace("KB", "").strip()) / 1024
            
            logger.info(f"Image size in MB: {size_value}")
            
            is_below_limit = size_value < 8 * 1024
            logger.info(f"Image size is {'below' if is_below_limit else 'above'} 8GB limit")
            
            return {
                "size": image_size,
                "size_mb": size_value,
                "is_below_limit": is_below_limit
            }
        except Exception as e:
            logger.error(f"Error checking image size: {str(e)}")
            return None

def main():
    """Main function to run the Dockerfile optimizer"""
    parser = argparse.ArgumentParser(description="Optimize Dockerfile to reduce image size")
    parser.add_argument("--dockerfile", "-f", default="Dockerfile", help="Path to the Dockerfile")
    parser.add_argument("--no-backup", action="store_true", help="Don't create a backup of the original Dockerfile")
    parser.add_argument("--check-only", action="store_true", help="Only check the image size without optimizing")
    args = parser.parse_args()
    
    os.makedirs("logs", exist_ok=True)
    
    optimizer = DockerfileOptimizer(args.dockerfile)
    
    if args.check_only:
        size_info = optimizer.check_image_size()
        if size_info:
            print(f"Docker image size: {size_info['size']} ({size_info['size_mb']:.2f} MB)")
            print(f"Size is {'below' if size_info['is_below_limit'] else 'above'} 8GB limit")
            
            if not size_info['is_below_limit']:
                print("Image size exceeds 8GB limit. Run without --check-only to optimize.")
                sys.exit(1)
        else:
            print("Failed to check image size")
            sys.exit(1)
    else:
        if not optimizer.load_dockerfile():
            print(f"Failed to load Dockerfile from {args.dockerfile}")
            sys.exit(1)
        
        if optimizer.optimize():
            if optimizer.save_dockerfile(not args.no_backup):
                print(f"Successfully optimized Dockerfile with {len(optimizer.optimization_steps)} techniques:")
                for i, step in enumerate(optimizer.optimization_steps, 1):
                    print(f"  {i}. {step}")
                
                print("\nChecking optimized image size...")
                size_info = optimizer.check_image_size()
                if size_info:
                    print(f"Optimized Docker image size: {size_info['size']} ({size_info['size_mb']:.2f} MB)")
                    print(f"Size is {'below' if size_info['is_below_limit'] else 'above'} 8GB limit")
                    
                    if not size_info['is_below_limit']:
                        print("Warning: Image size still exceeds 8GB limit after optimization.")
                        sys.exit(1)
            else:
                print("Failed to save optimized Dockerfile")
                sys.exit(1)
        else:
            print("No optimizations were applied to the Dockerfile")

if __name__ == "__main__":
    main()
