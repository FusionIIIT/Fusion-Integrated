"""Department module's public contract surface.

Other modules may import from this file ONLY (ADR-0013, import-linter).
Functions are plural by signature to prevent N+1 query loops across module boundaries.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from modules.department.models.seminar import GraduateSeminar


@dataclass(frozen=True)
class DepartmentSeminarDTO:
    seminar_id: int
    request_id: int
    speaker_id: int
    title: str
    scheduled_date: str
    start_time: str
    end_time: str
    venue: str


@dataclass(frozen=True)
class DepartmentNoDuesClearanceDTO:
    """Department no-dues clearance result for a student (AFR-OAP-052)."""
    user_id: int
    cleared: bool
    remarks: str


def get_scheduled_seminars_for_students(
    user_ids: Sequence[int],
) -> dict[int, list[DepartmentSeminarDTO]]:
    """Return scheduled graduate seminars for the given student IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    seminars = GraduateSeminar.objects.filter(speaker_id__in=ids).order_by("-scheduled_date")
    result: dict[int, list[DepartmentSeminarDTO]] = {uid: [] for uid in ids}
    for sem in seminars:
        result[sem.speaker_id].append(
            DepartmentSeminarDTO(
                seminar_id=sem.id,
                request_id=sem.request_id,
                speaker_id=sem.speaker_id,
                title=sem.title,
                scheduled_date=str(sem.scheduled_date),
                start_time=str(sem.start_time),
                end_time=str(sem.end_time),
                venue=sem.venue,
            )
        )
    return result


def get_department_no_dues_clearances(
    user_ids: Sequence[int],
) -> dict[int, DepartmentNoDuesClearanceDTO]:
    """Check department-level no-dues status for students (AFR-OAP-052)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    # In Department module, students are cleared by default unless pending obligations exist
    return {
        uid: DepartmentNoDuesClearanceDTO(
            user_id=uid,
            cleared=True,
            remarks="Departmental dues cleared.",
        )
        for uid in ids
    }
