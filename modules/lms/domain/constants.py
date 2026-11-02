class Role:
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    TA = "ta"
    OBSERVER = "observer"

    CHOICES = (
        (STUDENT, "Student"),
        (INSTRUCTOR, "Instructor"),
        (TA, "Teaching Assistant"),
        (OBSERVER, "Observer"),
    )


class MaterialKind:
    FILE = "file"
    LINK = "link"
    NOTE = "note"

    CHOICES = (
        (FILE, "File"),
        (LINK, "Link"),
        (NOTE, "Note"),
    )


class ContentStatus:
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"

    CHOICES = (
        (DRAFT, "Draft"),
        (SCHEDULED, "Scheduled"),
        (PUBLISHED, "Published"),
    )


class SubmissionType:
    FILE = "file"
    TEXT = "text"
    LINK = "link"

    CHOICES = (
        (FILE, "File"),
        (TEXT, "Text"),
        (LINK, "Link"),
    )


class SubmissionStatus:
    SUBMITTED = "submitted"
    LATE = "late"
    MISSING = "missing"

    CHOICES = (
        (SUBMITTED, "Submitted"),
        (LATE, "Late"),
        (MISSING, "Missing"),
    )


class GradeStatus:
    DRAFT = "draft"
    RELEASED = "released"

    CHOICES = (
        (DRAFT, "Draft"),
        (RELEASED, "Released"),
    )


class GradeAction:
    CREATED = "created"
    UPDATED = "updated"
    RELEASED = "released"

    CHOICES = (
        (CREATED, "Created"),
        (UPDATED, "Updated"),
        (RELEASED, "Released"),
    )


class ScheduleStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    CHOICES = (
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    )


ACTIVE_SCHEDULE_STATUSES = (ScheduleStatus.PENDING, ScheduleStatus.PROCESSING)
TERMINAL_SCHEDULE_STATUSES = (ScheduleStatus.COMPLETED, ScheduleStatus.FAILED, ScheduleStatus.CANCELLED)
