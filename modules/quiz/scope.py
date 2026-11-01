from __future__ import annotations

from collections.abc import Sequence

from modules.directory import contracts as directory


def professor_teaches(user, course) -> bool:
    """Use the platform directory projection; course integrations can provide
    a ``faculty_ids`` collection without introducing a cross-module FK."""
    if user is None or course is None:
        return False
    faculty_ids: Sequence[int] = getattr(course, "faculty_ids", ())
    return int(user.user_id) in {int(user_id) for user_id in faculty_ids}


def student_eligible(user, quiz) -> bool:
    if user is None or quiz is None or getattr(user, "kind", None) != "student":
        return False
    course = getattr(quiz, "course", None)
    if course is None:
        return False
    registered_ids: Sequence[int] = getattr(course, "student_ids", ())
    return int(user.user_id) in {int(user_id) for user_id in registered_ids}


def users_are_students(user_ids: Sequence[int]) -> bool:
    users = directory.get_users(user_ids)
    return all(user_id in users and users[user_id].kind == "student" for user_id in user_ids)
