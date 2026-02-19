import sqlite3
import logging
from CalendarEvent import CalendarEvent

logger = logging.getLogger(__name__)

DB_PATH = "calendar.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            uid          TEXT PRIMARY KEY,
            course_id    TEXT,
            course       TEXT,
            execution_type TEXT,
            start_time   TEXT,
            end_time     TEXT,
            location     TEXT,
            lecturers    TEXT,
            groups       TEXT,
            note         TEXT,
            hash         TEXT,
            google_id    TEXT,
            disabled     INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logger.info("DB initialised.")


def load_events_from_db():
    conn = get_conn()
    rows = conn.execute("""
        SELECT uid, course_id, course, execution_type, start_time, end_time,
               location, lecturers, groups, note, google_id, disabled
        FROM events
    """).fetchall()
    conn.close()

    events = []
    for row in rows:
        uid, course_id, course, execution_type, start_time, end_time, \
            location, lecturers, groups, note, google_id, disabled = row
        events.append(CalendarEvent(
            uid=uid,
            course_id=course_id,
            course=course,
            execution_type=execution_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            lecturers=lecturers,
            groups=groups,
            note=note,
            google_id=google_id,
            disabled=bool(disabled),
        ))
    return events


def update_google_id(uid, google_id):
    conn = get_conn()
    conn.execute("UPDATE events SET google_id = ? WHERE uid = ?", (google_id, uid))
    conn.commit()
    conn.close()


def sync_events(fresh_events: list[CalendarEvent]) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
    """
    Compare fresh_events against DB.
    Returns (created, updated) — events that changed and need Google sync.
    Marks DB-only events (removed from API) as disabled.
    """
    conn = get_conn()
    rows = conn.execute("SELECT uid, hash, google_id, disabled FROM events").fetchall()
    db_map = {row[0]: {"hash": row[1], "google_id": row[2], "disabled": row[3]} for row in rows}

    fresh_map = {e.uid: e for e in fresh_events}

    created = []
    updated = []

    for event in fresh_events:
        existing = db_map.get(event.uid)

        if existing is None:
            # New event
            conn.execute("""
                INSERT INTO events
                    (uid, course_id, course, execution_type, start_time, end_time,
                     location, lecturers, groups, note, hash, google_id, disabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0)
            """, (
                event.uid, event.course_id, event.course, event.execution_type,
                event.start_time, event.end_time, event.location, event.lecturers,
                event.groups, event.note, event.hash,
            ))
            logger.info(f"[CREATE] {event.uid} — {event.course} {event.start_time}")
            created.append(event)

        else:
            if existing["hash"] != event.hash:
                # Changed event — re-enable if disabled, update all fields
                conn.execute("""
                    UPDATE events SET
                        course_id = ?, course = ?, execution_type = ?,
                        start_time = ?, end_time = ?, location = ?,
                        lecturers = ?, groups = ?, note = ?, hash = ?, disabled = 0
                    WHERE uid = ?
                """, (
                    event.course_id, event.course, event.execution_type,
                    event.start_time, event.end_time, event.location,
                    event.lecturers, event.groups, event.note, event.hash,
                    event.uid,
                ))
                # Carry over existing google_id so we can update in place
                event.google_id = existing["google_id"]
                logger.info(f"[UPDATE] {event.uid} — {event.course} {event.start_time}")
                updated.append(event)
            else:
                logger.debug(f"[UNCHANGED] {event.uid}")

    # Mark events no longer in fresh data as disabled
    removed_uids = set(db_map.keys()) - set(fresh_map.keys())
    for uid in removed_uids:
        if not db_map[uid]["disabled"]:
            conn.execute("UPDATE events SET disabled = 1 WHERE uid = ?", (uid,))
            logger.info(f"[DISABLED] {uid} — no longer in API response")

    conn.commit()
    conn.close()

    logger.info(f"Sync complete: {len(created)} created, {len(updated)} updated, {len(removed_uids)} disabled.")
    return created, updated, len(removed_uids)


def is_empty():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    return count == 0
