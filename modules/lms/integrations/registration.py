"""Boundary to the existing academic registration and course assignment source.

The Fusion branch currently has no course-registration contract. Deployments
may provide one through ``LMS_COURSE_ACCESS_PROVIDER``. LMS fails closed and
returns an explicit unavailable response until that adapter is configured.
The provider is read-only: it cannot add or change academic registrations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string


class RegistrationSourceUnavailable(Exception):
    """The authoritative course access provider is missing or unavailable."""


@dataclass(frozen=True)
class PersonRef:
    user_id: int
    display_name: str


@dataclass(frozen=True)
class CourseAccess:
    course_id: str
    code: str
    title: str
    role: str
    instructors: tuple[PersonRef, ...] = ()
    teaching_assistants: tuple[PersonRef, ...] = ()
    # The PS leaves these TA permission policies open. The provider owns the
    # existing institute policy and returns its per-course decision.
    may_announce: bool = False
    may_grade: bool = False


class Provider(Protocol):
    def courses_for(self, user_id: int) -> list[CourseAccess]: ...

    def course_for(self, user_id: int, course_id: str) -> CourseAccess | None: ...


def get_provider() -> Provider:
    path = getattr(settings, "LMS_COURSE_ACCESS_PROVIDER", "")
    if not path:
        raise RegistrationSourceUnavailable(
            "The academic course-registration provider is not configured.")
    try:
        provider_class = import_string(path)
        provider = provider_class()
    except (ImportError, AttributeError, TypeError) as exc:
        raise RegistrationSourceUnavailable(
            "The academic course-registration provider could not be loaded.") from exc
    return provider


def courses_for(user_id: int) -> list[CourseAccess]:
    try:
        return get_provider().courses_for(user_id)
    except RegistrationSourceUnavailable:
        raise
    except Exception as exc:  # provider outages must never become an allow
        raise RegistrationSourceUnavailable(
            "The academic course-registration source is unavailable.") from exc


def course_for(user_id: int, course_id: str) -> CourseAccess | None:
    try:
        return get_provider().course_for(user_id, course_id)
    except RegistrationSourceUnavailable:
        raise
    except Exception as exc:
        raise RegistrationSourceUnavailable(
            "The academic course-registration source is unavailable.") from exc
