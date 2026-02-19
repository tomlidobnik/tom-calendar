import subprocess
import logging
import time
import os

from parse import parse_all_schedules
from db import init_db, sync_events, is_empty
from sync_google import sync_to_google
from clean import clean

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

CALENDAR_ID = "a43ff19f77f57af42c91a0657c168ce9fa7c47bd79230a09e6aa2bd796685d1a@group.calendar.google.com"
INTERVAL_SECONDS = 60 * 60  # 1 hour
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GET_CALENDAR_SCRIPT = os.path.join(SCRIPT_DIR, "get_calendar.sh")


def fetch_schedules():
    logger.info("▶️  Running get_calendar.sh...")
    result = subprocess.run(
        ["bash", GET_CALENDAR_SCRIPT],
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"get_calendar.sh failed:\n{result.stderr}")
        return False
    logger.info("✅ Schedules downloaded.")
    return True


def run_once():
    # 1. Download fresh JSONs
    if not fetch_schedules():
        return

    # 2. Parse all JSON files in schedule/
    events = parse_all_schedules()
    if not events:
        logger.warning("No events parsed, skipping sync.")
        return

    # 3. Sync to DB — detect new / changed / disabled
    empty_before = is_empty()
    created, updated, removed = sync_events(events)

    # 4. Push to Google Calendar only if there are changes
    if empty_before or created or updated or removed:
        logger.info("Changes detected — syncing to Google Calendar...")
        sync_to_google(CALENDAR_ID, created, updated)
    else:
        logger.info("No changes — nothing to push to Google Calendar.")


def main():
    os.chdir(SCRIPT_DIR)
    init_db()

    logger.info("🚀 tom-calendar started. Running every hour.")
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)

        logger.info(f"💤 Sleeping for {INTERVAL_SECONDS // 60} minutes...")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        os.chdir(SCRIPT_DIR)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )
        confirm = input(f"⚠️  This will delete ALL events from Google Calendar and wipe the DB.\nType 'yes' to confirm: ").strip()
        if confirm == "yes":
            clean(CALENDAR_ID)
        else:
            print("Aborted.")
    else:
        main()
