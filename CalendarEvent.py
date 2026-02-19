import hashlib


class CalendarEvent:
    def __init__(
        self,
        uid,
        course_id,
        course,
        execution_type,
        start_time,
        end_time,
        location,
        lecturers,
        groups,
        note="",
        google_id=None,
        disabled=False,
    ):
        self.uid = uid
        self.course_id = course_id
        self.course = course
        self.execution_type = execution_type
        self.start_time = start_time   # str ISO format
        self.end_time = end_time       # str ISO format
        self.location = location       # room names joined by ", "
        self.lecturers = lecturers     # lecturer names joined by ", "
        self.groups = groups           # group names joined by ", "
        self.note = note
        self.google_id = google_id
        self.disabled = disabled

    @property
    def hash(self):
        """Stable hash of all fields that matter for change detection."""
        raw = "|".join([
            self.course or "",
            self.execution_type or "",
            self.start_time or "",
            self.end_time or "",
            self.location or "",
            self.lecturers or "",
            self.groups or "",
            self.note or "",
        ])
        return hashlib.sha256(raw.encode()).hexdigest()

    @property
    def summary(self):
        return f"{self.course} [{self.execution_type}]"

    @property
    def description(self):
        parts = []
        if self.lecturers:
            parts.append(f"Lecturer: {self.lecturers}")
        if self.groups:
            parts.append(f"Group: {self.groups}")
        if self.note:
            parts.append(f"Note: {self.note}")
        return "\n".join(parts)

    def __repr__(self):
        return f"<CalendarEvent {self.uid} {self.course} {self.start_time}>"
