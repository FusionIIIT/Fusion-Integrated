"""Pure Python finite state machines for LMS entities."""

from __future__ import annotations

from datetime import datetime

from modules.lms.domain.constants import AssignmentStatus, GradeStatus, MaterialStatus


class IllegalTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""


class MaterialFSM:
    @staticmethod
    def publish(release_date: datetime | None, now: datetime) -> str:
        if release_date and release_date > now:
            return MaterialStatus.SCHEDULED
        return MaterialStatus.PUBLISHED

    @staticmethod
    def auto_release(current_status: str, release_date: datetime | None, now: datetime) -> str:
        if current_status != MaterialStatus.SCHEDULED:
            raise IllegalTransitionError(
                f"Cannot auto-release material in status: {current_status}"
            )
        if release_date and release_date > now:
            raise IllegalTransitionError("Release time has not yet arrived.")
        return MaterialStatus.PUBLISHED


class AssignmentFSM:
    @staticmethod
    def publish(current_status: str, release_date: datetime | None, now: datetime) -> str:
        if current_status != AssignmentStatus.DRAFT:
            raise IllegalTransitionError(
                f"Only DRAFT assignments can be published (got {current_status})."
            )
        if release_date and release_date > now:
            return AssignmentStatus.SCHEDULED
        return AssignmentStatus.PUBLISHED

    @staticmethod
    def auto_release(current_status: str, release_date: datetime | None, now: datetime) -> str:
        if current_status != AssignmentStatus.SCHEDULED:
            raise IllegalTransitionError(
                f"Only SCHEDULED assignments can be auto-released (got {current_status})."
            )
        if release_date and release_date > now:
            raise IllegalTransitionError("Release time has not yet arrived.")
        return AssignmentStatus.PUBLISHED

    @staticmethod
    def close(current_status: str) -> str:
        if current_status not in (AssignmentStatus.PUBLISHED, AssignmentStatus.SCHEDULED):
            raise IllegalTransitionError(f"Cannot close assignment in status {current_status}.")
        return AssignmentStatus.CLOSED


class GradeFSM:
    @staticmethod
    def publish(current_status: str) -> str:
        if current_status != GradeStatus.DRAFT:
            raise IllegalTransitionError(
                f"Only DRAFT grades can be published (got {current_status})."
            )
        return GradeStatus.PUBLISHED
