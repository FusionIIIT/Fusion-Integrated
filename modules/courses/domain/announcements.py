"""Pure Python domain entities and validation rules for Course Announcements (CFR-LMS-005)."""
from __future__ import annotations

from dataclasses import dataclass

from modules.courses.domain.errors import InvalidCourseDataError, UnauthorizedCourseActionError


@dataclass(frozen=True)
class AnnouncementCreateDTO:
    title: str
    body: str
    is_published: bool = True

    def validate(self) -> None:
        if not self.title or not self.title.strip():
            raise InvalidCourseDataError("Announcement title cannot be empty.")
        if len(self.title.strip()) > 200:
            raise InvalidCourseDataError("Announcement title cannot exceed 200 characters.")
        if not self.body or not self.body.strip():
            raise InvalidCourseDataError("Announcement message body cannot be empty.")


@dataclass(frozen=True)
class AnnouncementUpdateDTO:
    title: str | None = None
    body: str | None = None
    is_published: bool | None = None

    def validate(self) -> None:
        if self.title is not None:
            if not self.title.strip():
                raise InvalidCourseDataError("Announcement title cannot be empty.")
            if len(self.title.strip()) > 200:
                raise InvalidCourseDataError("Announcement title cannot exceed 200 characters.")
        if self.body is not None:
            if not self.body.strip():
                raise InvalidCourseDataError("Announcement message body cannot be empty.")


def validate_announcement_author(role: str | None) -> None:
    """Enforce that only assigned faculty instructors can author/edit announcements (BR-LMS-004, BR-LMS-007)."""
    if role != "instructor":
        raise UnauthorizedCourseActionError(
            "Only assigned faculty instructors may create, edit, or delete course announcements."
        )

