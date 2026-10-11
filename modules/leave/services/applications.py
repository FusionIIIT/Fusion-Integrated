"""Write paths for leave applications (EL-UC-001..011, WF-EL-01..05)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.leave.domain.categories import EXTENDABLE, RESUMABLE
from modules.leave.domain.eligibility import (
    LeaveRequest, OccupiedInterval, ValidationError, validate_request,
)
from modules.leave.domain.ledger import DEBIT, RESTORATION, REVERSAL
from modules.leave.domain.state_machine import (
    ACTIVE_OCCUPANCY, APPROVED, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD,
    CANCELLED, CLOSED, MODIFIABLE, ActorNotAllowed, GuardFailed,
    InvalidTransition, is_higher_sanction, is_unit_head_final, pick,
)
from modules.leave.models import LeaveApplication, LeaveTransition
from modules.leave.selectors import scoping
from modules.leave.services import accounts, notifications, policy as policy_svc
from modules.leave.services import routing
from modules.leave.services.authz import require


def _record(app: LeaveApplication, *, frm: str, to: str, event: str,
            actor, note: str = "") -> None:
    LeaveTransition.objects.create(
        application=app, frm=frm, to=to, event=event,
        actor_user_id=getattr(actor, "user_id", None),
        actor_kind=routing.actor_kind(actor, app), note=note,
    )


def _occupied(user_id: int, *, exclude_id: int | None = None) -> tuple[OccupiedInterval, ...]:
    qs = LeaveApplication.objects.filter(user_id=user_id, status__in=ACTIVE_OCCUPANCY)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return tuple(
        OccupiedInterval(r.start_on, r.end_on, r.half or None, r.category)
        for r in qs
    )


def _validate_substitute(applicant_id: int, nominee_id: int,
                         start: date, end: date) -> None:
    if nominee_id == applicant_id:
        raise ConflictError("A substitute cannot be the applicant.", code="BR-EL-014")
    people = directory.get_users([nominee_id])
    person = people.get(nominee_id)
    if person is None or person.kind not in ("faculty", "staff"):
        raise ConflictError("The nominee must be another employee.", code="BR-EL-014")
    for other in LeaveApplication.objects.filter(
            user_id=nominee_id, status__in=ACTIVE_OCCUPANCY):
        if not (other.end_on < start or other.start_on > end):
            raise ConflictError(
                "The nominee has overlapping pending or approved leave.",
                code="BR-EL-014")


def _build_request(app: LeaveApplication) -> LeaveRequest:
    return LeaveRequest(
        category=app.category, start=app.start_on, end=app.end_on,
        half=app.half or None, station_leave=app.station_leave,
        medical_evidence=app.medical_evidence, purpose=app.purpose,
        applicant_kind=app.applicant_kind, requires_substitute=app.requires_substitute,
    )


def _apply_validation(app: LeaveApplication, policy_snap, calendar) -> Decimal:
    try:
        return validate_request(
            request=_build_request(app), policy=policy_snap, calendar=calendar,
            balance=accounts.balance(app.user_id, app.category, app.start_on.year),
            occupied=_occupied(app.user_id, exclude_id=app.pk),
        )
    except ValidationError as exc:
        raise ConflictError(exc.message, code=exc.code) from exc


def _notify_status(app: LeaveApplication, subject: str, body: str, topic: str) -> None:
    notifications.notify_user(
        app.user_id, topic=topic,
        key=f"{topic}:{app.pk}:{app.status}:{app.updated_at.isoformat()}",
        subject=subject, body=body,
    )


@transaction.atomic
def submit(actor, *, category: str, start_on: date, end_on: date, purpose: str,
           half: str = "", station_leave: bool = False, station_details: str = "",
           medical_evidence: bool = False, medical_note: str = "",
           substitute_user_id: int | None = None,
           kind: str = "leave", parent: LeaveApplication | None = None,
           ) -> LeaveApplication:
    require(actor, "leave.application.create")
    _, snap = policy_svc.effective_policy()
    calendar = policy_svc.effective_calendar()
    uid = actor.user_id
    accounts.ensure_year_credits(uid, start_on.year, snap)
    kind_emp = accounts.employee_kind(uid)
    people = directory.get_users([uid])
    person = people.get(uid)
    unit = (person.department if person else "") or ""
    needs_sub = category in snap.categories_requiring_substitute
    if needs_sub and not substitute_user_id:
        raise ConflictError(
            "A substitute nomination is required before this request can be routed.",
            code="BR-EL-015")
    app = LeaveApplication(
        user_id=uid, kind=kind, parent=parent, category=category,
        start_on=start_on, end_on=end_on, half=half or "",
        purpose=purpose, chargeable_days=Decimal("0"),
        station_leave=station_leave, station_details=station_details,
        medical_evidence=medical_evidence, medical_note=medical_note,
        status="draft", unit_code=unit, applicant_kind=kind_emp,
        applicant_is_director=routing.is_director(actor),
        requires_substitute=needs_sub, substitute_user_id=substitute_user_id,
    )
    days = _apply_validation(app, snap, calendar)
    app.chargeable_days = days
    if needs_sub:
        _validate_substitute(uid, substitute_user_id, start_on, end_on)
        app.substitute_status = "pending"
    app.status = routing.next_status_after_submit(app, snap)
    app.submitted_at = timezone.now()
    app.save()
    _record(app, frm="draft", to=app.status, event="submit", actor=actor)
    routing.open_routing_task(app, snap)
    _notify_status(app, "Leave request submitted",
                   f"Your {category} request is now {app.status.replace('_', ' ')}.",
                   "leave.submitted")
    if needs_sub and substitute_user_id:
        notifications.notify_user(
            substitute_user_id, topic="leave.substitute",
            key=f"leave.substitute:{app.pk}:{substitute_user_id}",
            subject="Substitute nomination",
            body="You have been nominated as substitute for a leave request.",
        )
    return app


@transaction.atomic
def respond_substitute(actor, application_id: int, *, accept: bool) -> LeaveApplication:
    require(actor, "leave.substitute.review")
    app = scoping.get_visible_application(actor, application_id)
    if app.status != AWAITING_SUBSTITUTE:
        raise ConflictError("This request is not awaiting substitute consent.",
                            code="BR-EL-015")
    if actor.user_id != app.substitute_user_id:
        raise PermissionDeniedError("Only the nominated substitute may respond.")
    if accept:
        _validate_substitute(app.user_id, actor.user_id, app.start_on, app.end_on)
    _, snap = policy_svc.effective_policy()
    facts = {
        "accepted": accept, "declined": not accept,
        "director_applicant": app.applicant_is_director,
        "normal_path": not app.applicant_is_director,
    }
    try:
        t = pick(frm=app.status, event="substitute_accept" if accept else "substitute_decline",
                 actor_kind="substitute", facts=facts)
    except (InvalidTransition, GuardFailed) as exc:
        raise ConflictError(str(exc), code="WF-EL-01") from exc
    frm = app.status
    routing.close_open_tasks(app)
    if accept:
        app.substitute_status = "accepted"
        app.status = t.to
        routing.open_routing_task(app, snap)
    else:
        app.substitute_status = "declined"
        app.status = AWAITING_SUBSTITUTE
        _notify_status(app, "Substitute declined",
                       "Your nominated substitute declined. Nominate another or withdraw.",
                       "leave.status")
    app.save()
    _record(app, frm=frm, to=app.status, event=t.event, actor=actor)
    return app


@transaction.atomic
def nominate_substitute(actor, application_id: int, nominee_id: int) -> LeaveApplication:
    require(actor, "leave.application.update")
    app = scoping.get_visible_application(actor, application_id)
    if actor.user_id != app.user_id:
        raise PermissionDeniedError("Only the applicant may nominate a substitute.")
    if app.status != AWAITING_SUBSTITUTE or app.substitute_status != "declined":
        raise ConflictError("A new substitute can be nominated only after a decline.",
                            code="BR-EL-015")
    _, snap = policy_svc.effective_policy()
    _validate_substitute(app.user_id, nominee_id, app.start_on, app.end_on)
    routing.supersede_open_tasks(app)
    app.substitute_user_id = nominee_id
    app.substitute_status = "pending"
    app.save()
    routing.open_routing_task(app, snap)
    notifications.notify_user(
        nominee_id, topic="leave.substitute",
        key=f"leave.substitute:{app.pk}:{nominee_id}",
        subject="Substitute nomination",
        body="You have been nominated as substitute for a leave request.",
    )
    return app


def _post_approval(app: LeaveApplication) -> None:
    accounts.post(
        user_id=app.user_id, category=app.category, year=app.start_on.year,
        amount=-app.chargeable_days, entry_type=DEBIT,
        memo=f"Approved {app.category} {app.start_on}–{app.end_on}",
        application=app,
    )
    if app.category in RESUMABLE:
        app.status = APPROVED
    _notify_status(app, "Leave approved",
                   f"Your {app.category} leave has been approved.", "leave.decided")


@transaction.atomic
def unit_head_decide(actor, application_id: int, *, action: str,
                     note: str = "") -> LeaveApplication:
    require(actor, "leave.application.review", "leave.application.approve")
    app = scoping.get_visible_application(actor, application_id)
    if routing.actor_kind(actor, app) not in {"unit_head", "director", "leave_admin"}:
        if not actor.has_permission("leave.application.review"):
            raise PermissionDeniedError("Unit Head review is required.")
    _, snap = policy_svc.effective_policy()
    kind = routing.actor_kind(actor, app)
    if kind not in {"unit_head", "leave_admin", "director"}:
        kind = "unit_head"
    if is_unit_head_final(app.category):
        event = "unit_head_approve" if action == "approve" else "unit_head_reject"
        facts = {"cl_or_rh": True, "approve": action == "approve",
                 "reject": action == "reject"}
        perm = "leave.application.approve"
        require(actor, perm)
    elif is_higher_sanction(app.category):
        if action not in {"recommend", "not_recommend"}:
            raise ConflictError(
                "For SCL, EL, COL and VL the Unit Head records Recommended or Not Recommended.",
                code="BR-EL-017")
        event = "unit_head_recommend"
        facts = {
            "higher_sanction": True,
            "establishment_configured": snap.establishment_step_enabled,
            "no_establishment": not snap.establishment_step_enabled,
        }
        app.unit_head_recommendation = (
            "recommended" if action == "recommend" else "not_recommended")
    else:
        raise ConflictError("Unknown leave category for Unit Head review.", code="BR-EL-016")
    try:
        t = pick(frm=app.status, event=event, actor_kind=kind, facts=facts)
    except (InvalidTransition, GuardFailed, ActorNotAllowed) as exc:
        raise ConflictError(str(exc), code="WF-EL-01") from exc
    frm = app.status
    routing.close_open_tasks(app)
    app.status = t.to
    if t.to == APPROVED:
        app.decided_at = timezone.now()
        app.decided_by_user_id = actor.user_id
        _post_approval(app)
    elif t.to == "rejected":
        app.decided_at = timezone.now()
        app.decided_by_user_id = actor.user_id
        _notify_status(app, "Leave rejected",
                       f"Your {app.category} leave has been rejected.", "leave.decided")
    else:
        routing.open_routing_task(app, snap)
    app.save()
    _record(app, frm=frm, to=app.status, event=event, actor=actor, note=note)
    return app


@transaction.atomic
def establishment_route(actor, application_id: int, *, note: str = "") -> LeaveApplication:
    require(actor, "leave.application.review")
    app = scoping.get_visible_application(actor, application_id)
    _, snap = policy_svc.effective_policy()
    try:
        t = pick(frm=app.status, event="establishment_route",
                 actor_kind="establishment", facts={"authority_resolved": True})
    except (InvalidTransition, GuardFailed) as exc:
        raise ConflictError(str(exc), code="WF-EL-01") from exc
    frm = app.status
    routing.close_open_tasks(app)
    app.status = t.to
    app.save()
    routing.open_routing_task(app, snap)
    _record(app, frm=frm, to=app.status, event="establishment_route", actor=actor, note=note)
    return app


@transaction.atomic
def final_decide(actor, application_id: int, *, approve: bool,
                 note: str = "") -> LeaveApplication:
    require(actor, "leave.application.approve")
    app = scoping.get_visible_application(actor, application_id)
    kind = routing.actor_kind(actor, app)
    if app.status == "awaiting_director_self_sanction":
        if not routing.is_director(actor) or actor.user_id != app.user_id:
            raise PermissionDeniedError("Director self-sanction applies only to the Director applicant.")
        kind = "director"
        event = "director_self_approve" if approve else "director_self_reject"
    else:
        event = "final_approve" if approve else "final_reject"
        if kind not in {"sanctioning_authority", "director", "leave_admin"}:
            kind = "sanctioning_authority"
    facts = {"approve": approve, "reject": not approve}
    try:
        t = pick(frm=app.status, event=event, actor_kind=kind, facts=facts)
    except (InvalidTransition, GuardFailed) as exc:
        raise ConflictError(str(exc), code="WF-EL-01") from exc
    frm = app.status
    routing.close_open_tasks(app)
    app.status = t.to
    app.decided_at = timezone.now()
    app.decided_by_user_id = actor.user_id
    if approve:
        _post_approval(app)
    else:
        _notify_status(app, "Leave rejected",
                       f"Your {app.category} leave has been rejected.", "leave.decided")
    app.save()
    _record(app, frm=frm, to=app.status, event=event, actor=actor, note=note)
    return app


@transaction.atomic
def modify(actor, application_id: int, **fields) -> LeaveApplication:
    require(actor, "leave.application.update")
    app = scoping.get_visible_application(actor, application_id)
    if actor.user_id != app.user_id:
        raise PermissionDeniedError("Only the applicant may modify a pending request.")
    if app.status not in MODIFIABLE:
        raise ConflictError("This request may not be modified in its current status.",
                            code="BR-EL-021")
    _, snap = policy_svc.effective_policy()
    calendar = policy_svc.effective_calendar()
    for key in ("category", "start_on", "end_on", "purpose", "half",
                "station_leave", "station_details", "medical_evidence",
                "medical_note", "substitute_user_id"):
        if key in fields and fields[key] is not None:
            setattr(app, key, fields[key] if key != "half" else (fields[key] or ""))
    app.requires_substitute = app.category in snap.categories_requiring_substitute
    days = _apply_validation(app, snap, calendar)
    app.chargeable_days = days
    if app.requires_substitute:
        if not app.substitute_user_id:
            raise ConflictError("A substitute nomination is required.", code="BR-EL-015")
        _validate_substitute(app.user_id, app.substitute_user_id, app.start_on, app.end_on)
        app.substitute_status = "pending"
    routing.supersede_open_tasks(app)
    app.status = routing.next_status_after_submit(app, snap)
    app.save()
    routing.open_routing_task(app, snap)
    _record(app, frm="pending", to=app.status, event="modify", actor=actor)
    return app


@transaction.atomic
def withdraw(actor, application_id: int) -> LeaveApplication:
    require(actor, "leave.application.delete")
    app = scoping.get_visible_application(actor, application_id)
    if actor.user_id != app.user_id:
        raise PermissionDeniedError("Only the applicant may withdraw.")
    if app.status not in MODIFIABLE:
        raise ConflictError(
            "A finally approved request cannot be withdrawn; use cancellation.",
            code="BR-EL-022")
    frm = app.status
    routing.close_open_tasks(app)
    app.status = "withdrawn"
    app.save()
    _record(app, frm=frm, to=app.status, event="withdraw", actor=actor)
    _notify_status(app, "Leave withdrawn", "The pending leave request was withdrawn.",
                   "leave.withdrawn")
    return app


@transaction.atomic
def request_cancellation(actor, application_id: int, *, reason: str) -> LeaveApplication:
    require(actor, "leave.application.create")
    app = scoping.get_visible_application(actor, application_id)
    if actor.user_id != app.user_id:
        raise PermissionDeniedError("Only the applicant may request cancellation.")
    if app.status != APPROVED:
        raise ConflictError("Only approved leave may be cancelled.", code="BR-EL-023")
    if date.today() >= app.start_on:
        raise ConflictError(
            "Approved leave may be cancelled only before it begins.", code="BR-EL-023")
    _, snap = policy_svc.effective_policy()
    frm = app.status
    app.status = "cancellation_pending"
    app.save()
    routing.open_task(app, "cancellation", assignee_user_id=None,
                      assignee_role="Unit Head" if is_unit_head_final(app.category)
                      else "Sanctioning Authority", policy=snap)
    _record(app, frm=frm, to=app.status, event="request_cancellation", actor=actor,
            note=reason)
    return app


@transaction.atomic
def decide_cancellation(actor, application_id: int, *, approve: bool,
                        note: str = "") -> LeaveApplication:
    require(actor, "leave.application.approve")
    app = scoping.get_visible_application(actor, application_id)
    if app.status != "cancellation_pending":
        raise ConflictError("No cancellation is pending.", code="BR-EL-023")
    frm = app.status
    routing.close_open_tasks(app)
    if approve:
        accounts.post(
            user_id=app.user_id, category=app.category, year=app.start_on.year,
            amount=app.chargeable_days, entry_type=REVERSAL,
            memo="Approved cancellation reverses the original leave effect",
            application=app,
        )
        app.status = CANCELLED
    else:
        app.status = APPROVED
    app.save()
    _record(app, frm=frm, to=app.status,
            event="approve_cancellation" if approve else "reject_cancellation",
            actor=actor, note=note)
    _notify_status(app, "Cancellation decision",
                   "Cancellation approved." if approve else "Cancellation rejected; original leave stands.",
                   "leave.cancelled")
    return app


@transaction.atomic
def submit_extension(actor, application_id: int, *, extra_end_on: date,
                     purpose: str, substitute_user_id: int | None = None,
                     station_leave: bool = False, station_details: str = "",
                     ) -> LeaveApplication:
    require(actor, "leave.application.create")
    original = scoping.get_visible_application(actor, application_id)
    if actor.user_id != original.user_id:
        raise PermissionDeniedError("Only the applicant may extend leave.")
    if original.status != APPROVED or original.category not in EXTENDABLE:
        raise ConflictError("Extension is defined only for ongoing EL, COL or VL.",
                            code="BR-EL-025")
    if date.today() < original.start_on or date.today() > original.end_on:
        raise ConflictError("The original leave is not ongoing.", code="BR-EL-025")
    if extra_end_on <= original.end_on:
        raise ConflictError("The extension must add time after the approved end.")
    start = original.end_on
    from datetime import timedelta
    ext_start = original.end_on + timedelta(days=1)
    return submit(
        actor, category=original.category, start_on=ext_start, end_on=extra_end_on,
        purpose=purpose, substitute_user_id=substitute_user_id,
        station_leave=station_leave, station_details=station_details,
        kind="extension", parent=original,
    )


@transaction.atomic
def submit_resumption(actor, application_id: int, *, resumption_on: date,
                      details: str) -> LeaveApplication:
    require(actor, "leave.application.create")
    app = scoping.get_visible_application(actor, application_id)
    if actor.user_id != app.user_id:
        raise PermissionDeniedError("Only the applicant may submit resumption.")
    if app.status != APPROVED or app.category not in RESUMABLE:
        raise ConflictError("Resumption applies after EL, COL or VL.", code="BR-EL-027")
    _, snap = policy_svc.effective_policy()
    frm = app.status
    app.resumption_on = resumption_on
    app.resumption_details = details
    app.status = "awaiting_resumption_verification"
    app.save()
    routing.open_task(app, "resumption", assignee_user_id=None,
                      assignee_role="Unit Head", policy=snap)
    _record(app, frm=frm, to=app.status, event="submit_resumption", actor=actor)
    return app


@transaction.atomic
def verify_resumption(actor, application_id: int, *, verified: bool,
                      note: str = "") -> LeaveApplication:
    require(actor, "leave.application.review")
    app = scoping.get_visible_application(actor, application_id)
    if app.status != "awaiting_resumption_verification":
        raise ConflictError("No resumption is awaiting verification.", code="BR-EL-027")
    if not verified:
        _record(app, frm=app.status, to=app.status, event="resumption_rejected",
                actor=actor, note=note)
        return app
    routing.close_open_tasks(app)
    actual_end = app.resumption_on or app.end_on
    app.actual_end_on = actual_end
    if actual_end < app.end_on:
        calendar = policy_svc.effective_calendar()
        from modules.leave.domain.counting import chargeable_days
        used = chargeable_days(
            category=app.category, start=app.start_on, end=actual_end,
            half=app.half or None, closed_holidays=calendar.closed)
        unused = app.chargeable_days - used
        if unused > 0:
            accounts.post(
                user_id=app.user_id, category=app.category, year=app.start_on.year,
                amount=unused, entry_type=RESTORATION,
                memo="Verified early resumption restores unused approved leave",
                application=app)
    app.status = CLOSED
    app.save()
    _record(app, frm="awaiting_resumption_verification", to=CLOSED,
            event="verify_resumption", actor=actor, note=note)
    return app
