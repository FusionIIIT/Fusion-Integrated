"""Authoritative public Python API contract for Other Academic Procedures (ADR 0013).

Other modules in Fusion ERP query these procedures through this contract rather than
attempting cross-module database joins or foreign keys. Plural by signature.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.oap.models.bonafide import BonafideRequest, BonafideStatus
from modules.oap.models.leave import RequestStatus, StudentLeaveRequest
from modules.oap.models.nodues import NoDuesOverallStatus, NoDuesRequest


@dataclass(frozen=True)
class OapNoDuesStatusDTO:
    student_id: str
    is_cleared: bool
    status: str


def get_no_dues_clearances(student_ids: Sequence[str]) -> dict[str, OapNoDuesStatusDTO]:
    """Returns no-dues clearance status for a sequence of student IDs."""
    ids = {str(s) for s in student_ids if s}
    if not ids:
        return {}
    requests = NoDuesRequest.objects.filter(student_id__in=ids)
    results = {}
    for req in requests:
        results[req.student_id] = OapNoDuesStatusDTO(
            student_id=req.student_id,
            is_cleared=(req.overall_status == NoDuesOverallStatus.CLEARED),
            status=req.overall_status,
        )
    for sid in ids:
        if sid not in results:
            results[sid] = OapNoDuesStatusDTO(student_id=sid, is_cleared=False, status="NONE")
    return results


def get_active_leaves(student_ids: Sequence[str]) -> dict[str, bool]:
    """Returns True if the student currently holds an approved or pending leave of absence."""
    ids = {str(s) for s in student_ids if s}
    if not ids:
        return {}
    active = set(
        StudentLeaveRequest.objects.filter(
            student_id__in=ids, status__in=[RequestStatus.APPROVED, RequestStatus.PENDING]
        ).values_list("student_id", flat=True)
    )
    return {sid: (sid in active) for sid in ids}


def get_active_bonafide_numbers(student_ids: Sequence[str]) -> dict[str, str | None]:
    """Returns certificate number of student's latest issued bonafide certificate."""
    ids = {str(s) for s in student_ids if s}
    if not ids:
        return {}
    reqs = (
        BonafideRequest.objects.filter(
            student_id__in=ids, status=BonafideStatus.APPROVED
        ).order_by("-issued_at")
    )
    result: dict[str, str | None] = dict.fromkeys(ids)
    for r in reqs:
        if result[r.student_id] is None:
            result[r.student_id] = r.certificate_number
    return result

