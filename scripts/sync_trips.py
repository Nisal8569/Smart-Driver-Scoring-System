import os
import subprocess
import time
import socket
import logging
from datetime import datetime

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
TRIPS_DIR = 'data/trips'
SYNC_INTERVAL = 300  # Check every 5 minutes (increased from 60s to be less aggressive)
REMOTE_NAME = "origin"
BRANCH_NAME = "main"

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
        # Use a list of reliable hosts to check connectivity
        # github.com is the most relevant here
        socket.create_connection(("github.com", 443), timeout=5)
        return True
    except OSError:
        return False

def run_git_command(args, cwd=PROJECT_ROOT):
    """Run a git command and return output/error."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(e.cmd)}")
        logger.error(f"Error: {e.stderr.strip()}")
        return None

def check_git_config():
    """Ensure git user name and email are configured."""
    name = run_git_command(["config", "user.name"])
    email = run_git_command(["config", "user.email"])
    
    if not name:
        logger.warning("Git 'user.name' not configured. Setting temporary name.")
        run_git_command(["config", "user.name", "Smart Driver Pi"])
    if not email:
        logger.warning("Git 'user.email' not configured. Setting temporary email.")
        run_git_command(["config", "user.email", "pi@smartdriver.local"])

def sync_data():
    """Sync trip data to GitHub."""
    # 1. Pull latest changes to avoid conflicts
    logger.info("Syncing with remote branch...")
    pull_result = run_git_command(["pull", "--rebase", REMOTE_NAME, BRANCH_NAME])
    if pull_result is None:
        logger.warning("Failed to pull from remote. Proceeding with caution.")

    # 2. Check for new files in trips directory
    # Only track .csv files in data/trips
    status = run_git_command(["status", "--short", TRIPS_DIR])
    if not status:
        logger.info("No new trip data detected.")
        return

    # Check if there are actual new/modified CSV files
    lines = status.split('\n')
    csv_changes = [f for f in lines if f.strip().endswith('.csv')]
    
    if not csv_changes:
        logger.info("No new CSV data detected in status.")
        return

    logger.info(f"Detected {len(csv_changes)} changes. Starting sync process...")

    # 3. Add files
    run_git_command(["add", TRIPS_DIR])
    
    # 4. Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-sync trip data: {timestamp}"
    run_git_command(["commit", "-m", commit_msg])
    
    # 5. Push
    logger.info("Pushing to remote repository...")
    push_result = run_git_command(["push", REMOTE_NAME, BRANCH_NAME])
    
    if push_result is not None:
        logger.info("Sync successful!")
    else:
        logger.error("Sync failed during push. Check your Git credentials (PAT or SSH).")

def main():
    logger.info("Starting Smart Sync service...")
    logger.info(f"Target directory: {os.path.join(PROJECT_ROOT, TRIPS_DIR)}")
    
    # Run config check once at start
    check_git_config()
    
    while True:
        if is_connected():
            try:
                sync_data()
            except Exception as e:
                logger.exception(f"Unexpected error during sync cycle: {e}")
        else:
            # Only log connectivity issues occasionally to avoid log bloat
            pass
        
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()
