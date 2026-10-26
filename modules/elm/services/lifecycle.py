"""Changing a request after it exists: modify, cancel, extend, resume
(EL-UC-006, 008, 009, 010, 011; BR-EL-021, 023..025, 027, 028).

Reuses applications.py for routing, tasks and ledger posting, so an extension or a
cancellation travels through the same hierarchy as any other request.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.models import LeaveRequest, Resumption, SubstituteAssignment, WorkflowTask
from modules.elm.services import accounts, applications, routing, workflow
from modules.elm.services.applications import ApplicationError

S = LeaveRequest.Status
Kind = LeaveRequest.Kind
TaskStatus = WorkflowTask.Status
CONTINUOUS = ("EL", "COL", "VL")
EDITABLE = {"leave_type", "start_date", "end_date", "half", "reason", "substitute_required",
            "outside_station", "station_address", "station_contact", "medical_evidence_ref"}


def _owned(req: LeaveRequest, applicant_id: int) -> None:
    if req.applicant_id != applicant_id:
        raise ApplicationError("Only the applicant can do this.")


@transaction.atomic
def modify(request_id: int, applicant_id: int, nominee_id: int | None = None, **changes):
    """UC-006. Revalidate, supersede obsolete tasks, and reroute from the start.
    If revalidation fails nothing is changed."""
    req = applications._lock(request_id)
    _owned(req, applicant_id)
    if req.kind != Kind.ORIGINAL:
        raise ApplicationError("Only an original application can be modified.")
    if not workflow.can_modify(req.status):
        raise ApplicationError("This request can no longer be modified.")
    unknown = set(changes) - EDITABLE
    if unknown:
        raise ApplicationError(f"Cannot modify: {', '.join(sorted(unknown))}.")
    for field, value in changes.items():
        setattr(req, field, value)
    req.days = applications.validate_and_count(
        req.applicant_id, req.leave_type, req.start_date, req.end_date, req.half,
        exclude_id=req.pk)
    WorkflowTask.objects.filter(request=req, status=TaskStatus.OPEN).update(
        status=TaskStatus.SUPERSEDED)
    req.substitutes.filter(status=SubstituteAssignment.Status.PENDING).update(
        status=SubstituteAssignment.Status.SUPERSEDED)
    req.status = S.DRAFT
    req.save()
    return applications.submit(req.pk, nominee_id)


@transaction.atomic
def request_cancellation(request_id: int, applicant_id: int, today: date | None = None):
    """UC-008. Only an approved leave that has not begun; same hierarchy as the original."""
    today = today or date.today()
    parent = applications._lock(request_id)
    _owned(parent, applicant_id)
    if parent.kind != Kind.ORIGINAL or parent.status != S.APPROVED:
        raise ApplicationError("Only an approved leave can be cancelled.")
    if parent.start_date <= today:
        raise ApplicationError("The leave has begun; use extension or resumption instead.")
    prof = applications._profile(applicant_id)
    child = LeaveRequest.objects.create(
        applicant_id=applicant_id, leave_type=parent.leave_type, kind=Kind.CANCELLATION,
        parent=parent, start_date=parent.start_date, end_date=parent.end_date,
        half=parent.half, reason="Cancellation of approved leave", days=parent.days,
        status=S.DRAFT)
    new = workflow.submit(child.status, False, routing.is_director(applicant_id))
    parent.status = S.CANCELLATION_PENDING
    parent.save(update_fields=["status", "updated_at"])
    applications._advance(child, new, prof)
    return child


@transaction.atomic
def extend(request_id: int, applicant_id: int, new_end: date, nominee_id: int | None = None,
           substitute_required: bool = False, today: date | None = None):
    """UC-009. A separate request for only the additional days, for ongoing EL/COL/VL."""
    today = today or date.today()
    parent = applications._lock(request_id)
    _owned(parent, applicant_id)
    if parent.leave_type not in CONTINUOUS:
        raise ApplicationError("Extension is defined only for EL, COL and VL.")
    if parent.kind != Kind.ORIGINAL or parent.status != S.APPROVED:
        raise ApplicationError("Only an approved leave can be extended.")
    if not (parent.start_date <= today <= parent.end_date):
        raise ApplicationError("Only an ongoing leave can be extended.")
    if new_end <= parent.end_date:
        raise ApplicationError("The new end date must be after the current end date.")
    start = parent.end_date + timedelta(days=1)
    days = applications.validate_and_count(applicant_id, parent.leave_type, start, new_end)
    child = LeaveRequest.objects.create(
        applicant_id=applicant_id, leave_type=parent.leave_type, kind=Kind.EXTENSION,
        parent=parent, start_date=start, end_date=new_end,
        reason="Extension of ongoing leave", days=days,
        substitute_required=substitute_required, status=S.DRAFT)
    return applications.submit(child.pk, nominee_id)


@transaction.atomic
def submit_resumption(request_id: int, applicant_id: int, actual_date: date,
                      details: str = "", today: date | None = None):
    """UC-010. actual_date is the first day back at work."""
    today = today or date.today()
    req = applications._lock(request_id)
    _owned(req, applicant_id)
    if req.leave_type not in CONTINUOUS or req.kind != Kind.ORIGINAL:
        raise ApplicationError("Resumption applies only to EL, COL and VL.")
    if req.status != S.APPROVED:
        raise ApplicationError("Only an approved leave awaits resumption.")
    if req.start_date > today or actual_date < req.start_date or actual_date > today:
        raise ApplicationError("Invalid resumption date.")
    prof = applications._profile(applicant_id)
    verifier = routing.approver_for(
        routing.Stage.UNIT_HEAD, applicant_id=applicant_id, unit=prof.department,
        kind=prof.kind, leave_type=req.leave_type)       # assumption: Unit Head verifies
    Resumption.objects.create(request=req, actual_date=actual_date, details=details)
    WorkflowTask.objects.create(
        request=req, stage=WorkflowTask.Stage.VERIFY_RESUMPTION, assignee_id=verifier)
    req.status = S.AWAITING_RESUMPTION
    req.save(update_fields=["status", "updated_at"])
    return req


@transaction.atomic
def verify_resumption(request_id: int, verifier_id: int, verified: bool = True):
    """UC-011. Unused approved days are restored only after verification (SRS-EL-086)."""
    req = applications._lock(request_id)
    task = applications._take_task(req, WorkflowTask.Stage.VERIFY_RESUMPTION, verifier_id)
    if req.status != S.AWAITING_RESUMPTION:
        raise ApplicationError("This leave is not awaiting resumption verification.")
    if not verified:
        return req                                   # stays awaiting verification (WF-EL-05 step 2)
    res = req.resumptions.filter(status=Resumption.Status.PENDING).latest("id")
    unused = Decimal(max(0, (req.end_date - res.actual_date).days + 1))
    unused = min(unused, req.days)
    if unused > 0:
        accounts.restore_unused(req, unused)
    task.status = TaskStatus.DONE
    task.save(update_fields=["status", "updated_at"])
    res.status = Resumption.Status.VERIFIED
    res.verifier_id = verifier_id
    res.verified_at = timezone.now()
    res.unused_days = unused
    res.save()
    req.status = S.CLOSED
    req.save(update_fields=["status", "updated_at"])
    return req
