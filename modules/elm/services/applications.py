"""Applying for leave and deciding it (EL-UC-001..007, WF-EL-01, WF-EL-02).

Every function locks the request, checks the actor holds the open task, asks
workflow.py for the next state, and applies it. Notifications (SRS-EL-054) are not
sent here yet.
"""
from datetime import date

from django.db import transaction

from modules.directory.contracts import get_users
from modules.elm.models import Decision, LeaveRequest, SubstituteAssignment, WorkflowTask
from modules.elm.services import accounts, policy, routing, validation, workflow

S = LeaveRequest.Status
TaskStage = WorkflowTask.Stage
TaskStatus = WorkflowTask.Status


class ApplicationError(Exception):
    pass


def _profile(user_id: int):
    user = get_users([user_id]).get(user_id)
    if user is None:
        raise ApplicationError("Person not found in the directory.")
    return user


def _lock(request_id: int) -> LeaveRequest:
    return LeaveRequest.objects.select_for_update().get(pk=request_id)


def _open_task(req: LeaveRequest, stage: str, assignee_id: int) -> WorkflowTask:
    return WorkflowTask.objects.create(request=req, stage=stage, assignee_id=assignee_id)


def _take_task(req: LeaveRequest, stage: str, actor_id: int) -> WorkflowTask:
    """Authorisation: only the person holding the open task may act on it."""
    task = WorkflowTask.objects.filter(
        request=req, stage=stage, assignee_id=actor_id, status=TaskStatus.OPEN).first()
    if task is None:
        raise ApplicationError("You do not hold an open task of this kind for this request.")
    return task


def _close_open_tasks(req: LeaveRequest, status: str) -> None:
    WorkflowTask.objects.filter(request=req, status=TaskStatus.OPEN).update(status=status)


def validate_and_count(applicant_id: int, leave_type: str, start: date, end: date,
                       half: str = "", exclude_id: int | None = None):
    """Eligibility, calendar, day counting, overlap and balance (BR-EL-001..012).
    Returns the chargeable days. Raises PolicyError or LeaveValidationError."""
    pol = policy.get_effective_policy()
    if leave_type not in pol.params:
        raise ApplicationError(f"{leave_type} is not enabled in the effective policy.")
    try:
        cal = policy.get_effective_calendar(start.year)
    except policy.NoPublishedCalendar:
        cal = None
    if leave_type in ("RH", "VL") and cal is None:
        raise ApplicationError(f"A published calendar is needed to validate {leave_type}.")
    if leave_type == "RH":
        if start != end:
            raise ApplicationError("RH is a single day.")
        validation.check_rh_date(cal, start)
    if leave_type == "VL":
        validation.check_vl_period(cal, start, end)
    closed = frozenset()
    if cal:
        closed = frozenset(validation.calendar_dates(cal, "holiday", start, end))
    days = validation.chargeable_days(leave_type, start, end, half, closed)
    validation.check_no_overlap(applicant_id, start, end, half, exclude_id)
    validation.check_balance(applicant_id, start.year, leave_type, days)
    return days


@transaction.atomic
def create_draft(applicant_id: int, leave_type: str, start: date, end: date, reason: str,
                 half: str = "", substitute_required: bool = False,
                 outside_station: bool = False, station_address: str = "",
                 station_contact: str = "", medical_evidence_ref: str = "") -> LeaveRequest:
    _profile(applicant_id)
    days = validate_and_count(applicant_id, leave_type, start, end, half)
    return LeaveRequest.objects.create(
        applicant_id=applicant_id, leave_type=leave_type, start_date=start, end_date=end,
        half=half, reason=reason, days=days, substitute_required=substitute_required,
        outside_station=outside_station, station_address=station_address,
        station_contact=station_contact, medical_evidence_ref=medical_evidence_ref)
def _on_approved(req: LeaveRequest) -> None:
    """What final approval does depends on what kind of request it was."""
    parent = req.parent
    if req.kind == LeaveRequest.Kind.CANCELLATION:        # SRS-EL-066
        accounts.reverse_for_request(parent)
        parent.status = S.CANCELLED
        parent.save(update_fields=["status", "updated_at"])
    elif req.kind == LeaveRequest.Kind.EXTENSION:         # SRS-EL-075: only the increment
        accounts.debit_for_request(req)
        parent.end_date = req.end_date
        parent.days = parent.days + req.days
        parent.save(update_fields=["end_date", "days", "updated_at"])
    else:
        accounts.debit_for_request(req)


def _on_rejected(req: LeaveRequest) -> None:
    """A rejected cancellation leaves the original leave approved (SRS-EL-067).
    A rejected extension changes nothing (SRS-EL-076)."""
    if req.kind == LeaveRequest.Kind.CANCELLATION:
        req.parent.status = S.APPROVED
        req.parent.save(update_fields=["status", "updated_at"])


def _advance(req: LeaveRequest, new_status: str, prof) -> None:
    """Open the task the new state is waiting on, save, and post to the ledger on approval."""
    who = {"applicant_id": req.applicant_id, "unit": prof.department, "kind": prof.kind,
               "leave_type": req.leave_type}
    if new_status == S.AWAITING_UNIT_HEAD:
        _open_task(req, TaskStage.UNIT_HEAD, routing.approver_for(routing.Stage.UNIT_HEAD, **who))
    elif new_status == S.AWAITING_ESTABLISHMENT:
        _open_task(req, TaskStage.ESTABLISHMENT,
                   routing.approver_for(routing.Stage.ESTABLISHMENT, **who))
    elif new_status == S.AWAITING_FINAL:
        _open_task(req, TaskStage.FINAL, routing.approver_for(routing.Stage.FINAL, **who))
    elif new_status == S.AWAITING_DIRECTOR_SELF:
        _open_task(req, TaskStage.FINAL, req.applicant_id)      # BR-EL-020, assumption
    req.status = new_status
    req.save(update_fields=["status", "days", "updated_at"])
    if new_status == S.APPROVED:
        _on_approved(req)
    elif new_status == S.REJECTED:
        _on_rejected(req)


@transaction.atomic
def submit(request_id: int, nominee_id: int | None = None) -> LeaveRequest:
    """UC-001 steps 4 to 8."""
    req = _lock(request_id)
    prof = _profile(req.applicant_id)
    req.days = validate_and_count(req.applicant_id, req.leave_type, req.start_date,
                                  req.end_date, req.half, exclude_id=req.pk)
    director = routing.is_director(req.applicant_id)
    new = workflow.submit(req.status, req.substitute_required, director)
    if new == S.AWAITING_SUBSTITUTE:
        if nominee_id is None:
            raise ApplicationError("A substitute must be nominated.")
        validation.check_substitute(req.applicant_id, nominee_id, req.start_date, req.end_date)
        SubstituteAssignment.objects.create(request=req, nominee_id=nominee_id)
        _open_task(req, TaskStage.SUBSTITUTE, nominee_id)
        req.status = new
        req.save(update_fields=["status", "days", "updated_at"])
    else:
        _advance(req, new, prof)
    return req


@transaction.atomic
def nominate_substitute(request_id: int, applicant_id: int, nominee_id: int) -> LeaveRequest:
    """After a decline the applicant may nominate another substitute (UC-001 alternative)."""
    req = _lock(request_id)
    if req.applicant_id != applicant_id:
        raise ApplicationError("Only the applicant can nominate a substitute.")
    if req.status != S.AWAITING_SUBSTITUTE or req.substitutes.filter(
            status=SubstituteAssignment.Status.PENDING).exists():
        raise ApplicationError("A new nomination is only possible after a decline.")
    validation.check_substitute(req.applicant_id, nominee_id, req.start_date, req.end_date)
    SubstituteAssignment.objects.create(request=req, nominee_id=nominee_id)
    _open_task(req, TaskStage.SUBSTITUTE, nominee_id)
    return req


@transaction.atomic
def respond_substitute(request_id: int, nominee_id: int, accept: bool) -> LeaveRequest:
    """UC-002."""
    req = _lock(request_id)
    task = _take_task(req, TaskStage.SUBSTITUTE, nominee_id)
    sub = req.substitutes.get(nominee_id=nominee_id, status=SubstituteAssignment.Status.PENDING)
    task.status = TaskStatus.DONE
    task.save(update_fields=["status", "updated_at"])
    if accept:
        # A nominee who no longer qualifies cannot release the gate.
        validation.check_substitute(req.applicant_id, nominee_id, req.start_date, req.end_date)
        new = workflow.substitute_accepted(req.status, routing.is_director(req.applicant_id))
        sub.status = SubstituteAssignment.Status.ACCEPTED
        sub.save(update_fields=["status", "updated_at"])
        _advance(req, new, _profile(req.applicant_id))
    else:
        workflow.substitute_declined(req.status)
        sub.status = SubstituteAssignment.Status.DECLINED
        sub.save(update_fields=["status", "updated_at"])
    return req


def _decide(request_id: int, actor_id: int, task_stage: str, outcome: str, remarks: str,
            compute_next) -> LeaveRequest:
    req = _lock(request_id)
    task = _take_task(req, task_stage, actor_id)
    prof = _profile(req.applicant_id)
    new = compute_next(req, prof)
    if outcome:
        Decision.objects.create(request=req, task=task, actor_id=actor_id,
                                outcome=outcome, remarks=remarks)
    task.status = TaskStatus.DONE
    task.save(update_fields=["status", "updated_at"])
    _advance(req, new, prof)
    return req


@transaction.atomic
def unit_head_decide(request_id: int, actor_id: int, outcome: str, remarks: str = ""):
    """UC-003."""
    def nxt(req, prof):
        est = routing.establishment_configured(
            applicant_id=req.applicant_id, unit=prof.department, kind=prof.kind,
            leave_type=req.leave_type)
        return workflow.unit_head_decision(req.status, req.leave_type, outcome, est)
    return _decide(request_id, actor_id, TaskStage.UNIT_HEAD, outcome, remarks, nxt)


@transaction.atomic
def establishment_route(request_id: int, actor_id: int, remarks: str = ""):
    """UC-004."""
    return _decide(request_id, actor_id, TaskStage.ESTABLISHMENT, "", remarks,
                   lambda req, prof: workflow.establishment_routed(req.status))


@transaction.atomic
def final_decide(request_id: int, actor_id: int, outcome: str, remarks: str = ""):
    """UC-005, including the Director deciding on their own request."""
    return _decide(request_id, actor_id, TaskStage.FINAL, outcome, remarks,
                   lambda req, prof: workflow.final_decision(req.status, outcome))


@transaction.atomic
def withdraw(request_id: int, applicant_id: int) -> LeaveRequest:
    """UC-007: immediate, closes every open task, blocks later decisions."""
    req = _lock(request_id)
    if req.applicant_id != applicant_id:
        raise ApplicationError("Only the applicant can withdraw this request.")
    new = workflow.withdraw(req.status)
    _close_open_tasks(req, TaskStatus.CANCELLED)
    req.substitutes.filter(status=SubstituteAssignment.Status.PENDING).update(
        status=SubstituteAssignment.Status.SUPERSEDED)
    req.status = new
    req.save(update_fields=["status", "updated_at"])
    if req.kind == LeaveRequest.Kind.CANCELLATION:        # withdrawn cancellation: leave stands
        req.parent.status = S.APPROVED
        req.parent.save(update_fields=["status", "updated_at"])
    return req
