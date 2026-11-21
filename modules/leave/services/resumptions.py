"""EL-UC-010/011: resumption of duty after EL/COL/VL (BR-EL-027/028)."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.accounting import NotResumable, Outcome, Reason, resumption_outcome
from modules.leave.domain.categories import RESUMABLE, Category
from modules.leave.domain.workflow import State
from modules.leave.models import LeaveRequest, Resumption
from modules.leave.selectors import accounts as reads
from modules.leave.services import accounts
from modules.leave.services.notify import notify


def submit(leave_id: int, user_id: int, actual_date: date, remarks: str,
           today: date) -> Resumption:
    with transaction.atomic():
        leave = LeaveRequest.objects.select_for_update().filter(
            pk=leave_id, user_id=user_id, kind=LeaveRequest.NEW).first()
        if leave is None:
            raise NotFoundError("That leave does not exist.")
        if leave.status != State.APPROVED or Category(leave.category) not in RESUMABLE:
            raise ConflictError("Resumption is submitted for approved EL, COL or VL only.",
                                code="not_resumable")
        if today < leave.start_date:
            raise ConflictError("This leave has not begun; cancel it instead.",
                                code="not_started")
        if not leave.start_date <= actual_date <= today:
            raise BadRequestError("The resumption date must fall between the leave start "
                                  "and today.", code="invalid_resumption_date")
        if Resumption.objects.filter(leave=leave).exists():
            raise ConflictError("Resumption has already been submitted for this leave.",
                                code="already_submitted")
        if leave.sanctioning_user_id is None:
            raise ConflictError("This leave has no sanctioning authority on record. Ask the "
                                "Leave Administrator to record your return.",
                                code="no_reviewer")
        resumption = Resumption.objects.create(
            leave=leave, actual_date=actual_date, remarks=remarks.strip(),
            reviewer_user_id=leave.sanctioning_user_id)
        notify([resumption.reviewer_user_id], "assigned",  # BR-EL-035
               f"Resumption to review for leave request #{leave.pk}.", request=leave)
        return resumption


def review(resumption_id: int, user_id: int) -> Resumption:
    """BR-EL-028: adjust only when the actual date differs from the approved end."""
    with transaction.atomic():
        r = (Resumption.objects.select_for_update().select_related("leave")
             .filter(pk=resumption_id).first())
        if r is None:
            raise NotFoundError("That resumption does not exist.")
        if r.reviewer_user_id != user_id or (
                r.leave.user_id == user_id and not r.leave.director_self):
            raise PermissionDeniedError("This resumption is assigned to someone else.",
                                        code="not_assignee")
        if r.status != Resumption.PENDING:
            raise ConflictError("This resumption has already been reviewed.",
                                code="already_reviewed")
        leave = r.leave
        try:
            outcome, delta = resumption_outcome(Category(leave.category),
                                                reads.effective_end(leave), r.actual_date)
        except NotResumable as exc:
            raise ConflictError(str(exc), code="not_resumable") from exc
        if outcome is not Outcome.NORMAL:
            accounts.lock(leave.user_id)
            accounts.post(leave.user_id, Category(leave.category), leave.start_date.year,
                          delta, Reason.RESUMPTION_ADJUST, request=leave,
                          key=f"resume:{r.pk}", by=user_id,
                          note=f"{outcome.value} resumption on {r.actual_date}")
        r.status, r.outcome, r.adjustment_days = Resumption.REVIEWED, outcome.value, delta
        r.reviewed_at = timezone.now()
        r.save()
        notify([leave.user_id], "decision",
               f"Your resumption for leave request #{leave.pk} was reviewed ({outcome.value}).",
               request=leave)
        return r
