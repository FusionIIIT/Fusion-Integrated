"""Course announcement selectors."""

from __future__ import annotations

from typing import Any

from modules.lms.models import CourseAnnouncement
from modules.lms.selectors.scoping import has_course_access


def list_announcements(course_id: int, principal: Any) -> list[CourseAnnouncement]:
    if not has_course_access(course_id, principal):
        return []
    return list(CourseAnnouncement.objects.filter(course_id=course_id).order_by("-created_at"))
