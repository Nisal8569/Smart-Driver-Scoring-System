import os
import subprocess
import time
import socket
import logging
from datetime import datetime

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
TRIPS_DIR = 'data/trips'
SYNC_INTERVAL = 300  # Check every 5 minutes
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

def get_already_synced_files():
    """Return set of CSV filenames already tracked by git in the trips directory."""
    output = run_git_command(["ls-files", TRIPS_DIR])
    if not output:
        return set()
    tracked = set()
    for line in output.splitlines():
        if line.strip().endswith('.csv'):
            tracked.add(os.path.basename(line.strip()))
    return tracked

def get_local_trip_files():
    """Return set of CSV filenames present locally in the trips directory."""
    trips_path = os.path.join(PROJECT_ROOT, TRIPS_DIR)
    if not os.path.isdir(trips_path):
        return set()
    return {f for f in os.listdir(trips_path) if f.endswith('.csv')}

def sync_data():
    """Sync new trip data to GitHub, skipping files already synced."""
    # 1. Fetch latest from remote then hard-reset to match it.
    #    This avoids untracked-file conflicts that block git pull --rebase,
    #    while still picking up any remote changes (e.g. files committed from PC).
    logger.info("Fetching latest changes from remote...")
    fetch_result = run_git_command(["fetch", REMOTE_NAME, BRANCH_NAME])
    if fetch_result is None:
        logger.error("Fetch failed. Skipping sync this cycle.")
        return

    reset_result = run_git_command(["reset", "--hard", f"{REMOTE_NAME}/{BRANCH_NAME}"])
    if reset_result is None:
        logger.error("Reset failed. Skipping sync this cycle.")
        return

    # 2. Compare local files against already-tracked (synced) files
    already_synced = get_already_synced_files()
    local_files = get_local_trip_files()
    new_files = local_files - already_synced

    if not new_files:
        logger.info(f"No new trips to sync. ({len(already_synced)} already synced)")
        return

    logger.info(f"Found {len(new_files)} new trip(s) to sync (skipping {len(already_synced)} already synced):")
    for f in sorted(new_files):
        logger.info(f"  + {f}")

    # 3. Stage only the new files
    for f in sorted(new_files):
        rel_path = os.path.join(TRIPS_DIR, f)
        run_git_command(["add", rel_path])

    # 4. Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto-sync trip data: {timestamp} ({len(new_files)} trip(s))"
    commit_result = run_git_command(["commit", "-m", commit_msg])
    if commit_result is None:
        logger.error("Commit failed. Aborting sync.")
        return

    # 5. Push
    logger.info("Pushing to remote repository...")
    push_result = run_git_command(["push", REMOTE_NAME, BRANCH_NAME])
    if push_result is not None:
        logger.info(f"Sync successful! {len(new_files)} trip(s) pushed.")
    else:
        logger.error("Push failed. Check Git credentials (PAT or SSH key).")

def main():
    logger.info("Starting Smart Sync service...")
    logger.info(f"Target directory: {os.path.join(PROJECT_ROOT, TRIPS_DIR)}")

    check_git_config()

    while True:
        if is_connected():
            try:
                sync_data()
            except Exception as e:
                logger.exception(f"Unexpected error during sync cycle: {e}")
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()
