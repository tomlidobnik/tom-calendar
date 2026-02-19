import os
import time
import logging
from datetime import datetime

import pytz
from dateutil import parser as date_parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from CalendarEvent import CalendarEvent
import db

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TZ = pytz.timezone("Europe/Ljubljana")


def _localize(dt_str: str):
    dt = date_parser.parse(dt_str)
    return dt if dt.tzinfo else TZ.localize(dt)


def _build_google_body(event: CalendarEvent) -> dict:
    return {
        "summary": event.summary,
        "description": event.description,
        "location": event.location,
        "start": {
            "dateTime": _localize(event.start_time).isoformat(),
            "timeZone": "Europe/Ljubljana",
        },
        "end": {
            "dateTime": _localize(event.end_time).isoformat(),
            "timeZone": "Europe/Ljubljana",
        },
    }


def _create_event(service, calendar_id: str, event: CalendarEvent):
    try:
        body = _build_google_body(event)
        result = service.events().insert(calendarId=calendar_id, body=body).execute()
        time.sleep(0.05)
        db.update_google_id(event.uid, result["id"])
        logger.info(f"➕ Created: {event.summary} @ {event.start_time}")
    except HttpError as e:
        logger.error(f"❌ Failed to create {event.uid}: {e}")


def _update_event(service, calendar_id: str, event: CalendarEvent):
    try:
        # Fetch existing Google event to patch it
        google_event = service.events().get(
            calendarId=calendar_id, eventId=event.google_id
        ).execute()

        new_body = _build_google_body(event)
        changed = False

        for field in ("summary", "description", "location"):
            if google_event.get(field, "") != new_body.get(field, ""):
                google_event[field] = new_body[field]
                changed = True

        new_start = new_body["start"]["dateTime"]
        new_end = new_body["end"]["dateTime"]

        if date_parser.parse(google_event["start"]["dateTime"]) != date_parser.parse(new_start):
            google_event["start"]["dateTime"] = new_start
            changed = True
        if date_parser.parse(google_event["end"]["dateTime"]) != date_parser.parse(new_end):
            google_event["end"]["dateTime"] = new_end
            changed = True

        if changed:
            service.events().update(
                calendarId=calendar_id, eventId=event.google_id, body=google_event
            ).execute()
            time.sleep(0.05)
            logger.info(f"📝 Updated: {event.summary} @ {event.start_time}")
        else:
            logger.debug(f"✅ No Google change needed: {event.uid}")

    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(f"🟡 Event missing in Google, re-creating: {event.uid}")
            _create_event(service, calendar_id, event)
        else:
            logger.error(f"❌ Failed to update {event.uid}: {e}")


def _delete_disabled(service, calendar_id: str):
    """Delete Google Calendar events for events marked disabled in the DB."""
    events = db.load_events_from_db()
    for event in events:
        if event.disabled and event.google_id:
            try:
                service.events().delete(
                    calendarId=calendar_id, eventId=event.google_id
                ).execute()
                time.sleep(0.05)
                db.update_google_id(event.uid, None)
                logger.info(f"🗑️ Deleted disabled event: {event.uid}")
            except HttpError as e:
                logger.warning(f"⚠️ Failed to delete {event.uid}: {e}")


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


def sync_to_google(calendar_id: str, created: list[CalendarEvent], updated: list[CalendarEvent]):
    """Push only the changed events to Google Calendar."""
    if not created and not updated:
        logger.info("No changes to push to Google Calendar.")
        return

    try:
        service = _get_service()
        _delete_disabled(service, calendar_id)

        for event in created:
            _create_event(service, calendar_id, event)

        for event in updated:
            if event.google_id:
                _update_event(service, calendar_id, event)
            else:
                _create_event(service, calendar_id, event)

        logger.info(f"Google sync done: {len(created)} created, {len(updated)} updated.")

    except HttpError as e:
        logger.error(f"Google Calendar error: {e}")
