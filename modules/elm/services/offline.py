"""Retrospective entry of leave sanctioned offline (EL-UC-016, BR-EL-029, WF-EL-06).

This synchronises records; it is not an approval, so no workflow tasks are created.
Anything inconsistent raises before a single row is written ("correction required").
"""
from datetime import date

from django.db import transaction

from modules.elm.models import LeaveRequest, OfflineRecord
from modules.elm.services import accounts, applications
from modules.elm.services.applications import ApplicationError


@transaction.atomic
def record_offline(admin_id: int, applicant_id: int, leave_type: str, start: date, end: date,
                   reference: str, sanctioned_by: str, sanctioned_on: date, half: str = "",
                   reason: str = "", today: date | None = None) -> LeaveRequest:
    today = today or date.today()
    if not reference.strip() or not sanctioned_by.strip():
        raise ApplicationError("Sanction reference and sanctioning authority are required.")
    if sanctioned_on > today:
        raise ApplicationError("The sanction date cannot be in the future.")
    applications._profile(applicant_id)
    # Same consistency rules as an online application: eligibility, calendar,
    # day counting, overlap with other leave, and balance.
    days = applications.validate_and_count(applicant_id, leave_type, start, end, half)
    req = LeaveRequest.objects.create(
        applicant_id=applicant_id, leave_type=leave_type, start_date=start, end_date=end,
        half=half, reason=reason or "Offline-sanctioned leave", days=days,
        status=LeaveRequest.Status.APPROVED)
    accounts.debit_for_offline(req, reference.strip())
    OfflineRecord.objects.create(
        request=req, recorded_by=admin_id, reference=reference.strip(),
        sanctioned_by=sanctioned_by.strip(), sanctioned_on=sanctioned_on)
    return req
