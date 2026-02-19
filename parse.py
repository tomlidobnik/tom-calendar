import json
import os
import logging
from CalendarEvent import CalendarEvent

logger = logging.getLogger(__name__)

SCHEDULE_DIR = "schedule"

# Manual group filters per subject ID (filename without .json).
# Only events whose group names contain at least one of the listed substrings
# will be included. Subject IDs not listed here are included without filtering.
# Example:
#   "1025": ["RV1"]        → only RV1 group for subject 1025
#   "1444": ["RV1", "RV2"] → RV1 and RV2 groups for subject 1444
GROUP_FILTER: dict[str, list[str]] = {
    # "1025": ["RV1"],
}


def parse_entry(entry: dict) -> CalendarEvent:
    """Convert a single API JSON entry to a CalendarEvent."""
    api_id = entry.get("id", "")
    start_time = entry.get("start_time", "")

    uid = f"{api_id}_{start_time}"

    location = ", ".join(r["name"] for r in entry.get("rooms", []))
    lecturers = ", ".join(l["name"] for l in entry.get("lecturers", []))
    groups = ", ".join(g["name"] for g in entry.get("groups", []))

    return CalendarEvent(
        uid=uid,
        course_id=entry.get("courseId", ""),
        course=entry.get("course", ""),
        execution_type=entry.get("executionType", ""),
        start_time=start_time,
        end_time=entry.get("end_time", ""),
        location=location,
        lecturers=lecturers,
        groups=groups,
        note=entry.get("note", ""),
    )


def _matches_group_filter(entry: dict, allowed_groups: list[str]) -> bool:
    """Return True if any group in the entry contains one of the allowed substrings."""
    for group in entry.get("groups", []):
        for allowed in allowed_groups:
            if allowed.lower() in group["name"].lower():
                return True
    return False


def parse_all_schedules() -> list[CalendarEvent]:
    """Read all JSON files from the schedule/ dir and return all events."""
    events = []

    if not os.path.isdir(SCHEDULE_DIR):
        logger.warning(f"Schedule directory '{SCHEDULE_DIR}' not found.")
        return events

    for filename in os.listdir(SCHEDULE_DIR):
        if not filename.endswith(".json"):
            continue

        subject_id = filename[:-5]  # strip .json
        allowed_groups = GROUP_FILTER.get(subject_id)

        filepath = os.path.join(SCHEDULE_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.warning(f"{filename}: expected a JSON array, skipping.")
                continue

            included = 0
            for entry in data:
                if allowed_groups and not _matches_group_filter(entry, allowed_groups):
                    continue
                events.append(parse_entry(entry))
                included += 1

            if allowed_groups:
                logger.info(f"Parsed {included}/{len(data)} entries from {filename} (group filter: {allowed_groups})")
            else:
                logger.info(f"Parsed {included} entries from {filename}")

        except Exception as e:
            logger.error(f"Failed to parse {filename}: {e}")

    logger.info(f"Total events parsed: {len(events)}")
    return events
