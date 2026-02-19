import os
import time
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from db import DB_PATH, get_conn

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def clear_google_calendar(calendar_id: str):
    """Delete every event in the given Google Calendar."""
    logger.info(f"🗑️  Clearing all Google Calendar events for: {calendar_id}")
    try:
        service = _get_service()
        page_token = None
        deleted = 0

        while True:
            response = service.events().list(
                calendarId=calendar_id,
                maxResults=2500,
                singleEvents=True,
                pageToken=page_token,
            ).execute()

            for item in response.get("items", []):
                event_id = item["id"]
                try:
                    service.events().delete(
                        calendarId=calendar_id, eventId=event_id
                    ).execute()
                    time.sleep(0.05)
                    deleted += 1
                    logger.info(f"  🗑️  Deleted: {item.get('summary', event_id)}")
                except HttpError as e:
                    logger.warning(f"  ⚠️  Could not delete {event_id}: {e}")

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        logger.info(f"✅ Deleted {deleted} events from Google Calendar.")

    except HttpError as e:
        logger.error(f"❌ Google Calendar error: {e}")


def delete_db():
    """Drop the local SQLite database file."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info(f"✅ Deleted database: {DB_PATH}")
    else:
        logger.info(f"ℹ️  Database not found, nothing to delete: {DB_PATH}")


def clean(calendar_id: str):
    """Full clean: delete all Google Calendar events and wipe the local DB."""
    logger.info("🧹 Starting clean...")
    clear_google_calendar(calendar_id)
    delete_db()
    logger.info("✅ Clean complete.")
