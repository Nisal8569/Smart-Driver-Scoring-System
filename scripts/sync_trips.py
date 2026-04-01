import os
import subprocess
import time
import socket
import logging
from datetime import datetime

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
TRIPS_DIR = os.path.join(PROJECT_ROOT, 'data/trips')
SYNC_INTERVAL = 60  # Check every 60 seconds
REMOTE_NAME = "origin"
BRANCH_NAME = "main" # Change if your branch is different (e.g., 'master')

# Logging setup
log_dir = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'sync_trips.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_connected():
    """Check if there is an active internet connection."""
    try:
        # Connect to a reliable host (GitHub) to check connectivity
        socket.create_connection(("github.com", 80), timeout=5)
        return True
    except OSError:
        return False

def run_git_command(args):
    """Run a git command and return output/error."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(e.cmd)}")
        logger.error(f"Error: {e.stderr.strip()}")
        return None

def sync_data():
    """Sync trip data to GitHub."""
    logger.info("Checking for new trip data to sync...")
    
    # 1. Check if there are changes in the trips directory
    status = run_git_command(["status", "--short", TRIPS_DIR])
    if not status:
        logger.info("No new trip data detected.")
        return

    logger.info("New data detected. Starting sync process...")

    # 2. Add files
    run_git_command(["add", TRIPS_DIR])
    
    # 3. Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-sync trip data: {timestamp}"
    run_git_command(["commit", "-m", commit_msg])
    
    # 4. Push
    logger.info("Pushing to remote repository...")
    push_result = run_git_command(["push", REMOTE_NAME, BRANCH_NAME])
    
    if push_result is not None:
        logger.info("Sync successful!")
    else:
        logger.error("Sync failed during push. Check your Git credentials.")

def main():
    logger.info("Starting Auto-Sync service...")
    logger.info(f"Monitoring: {TRIPS_DIR}")
    
    while True:
        if is_connected():
            try:
                sync_data()
            except Exception as e:
                logger.error(f"Unexpected error during sync: {e}")
        else:
            logger.warning("No internet connection. Waiting for connectivity...")
        
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()
