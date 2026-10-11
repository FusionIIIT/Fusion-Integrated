from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.placement.domain import eligibility as elig
from modules.placement.domain import state_machine as sm
from modules.placement.models import (
    Application,
    ApplicationTransition,
    JobPosting,
    PlacementPolicy,
    PlacementRegistration,
    RoundParticipation,
)
from modules.placement.selectors import scoping
from modules.placement.services import facts as facts_service
from modules.placement.services import notifications
from modules.elm.models import Leave

log = logging.getLogger("fusion.placement.applications")


def actor_kind(actor, application=None) -> str:
    """Which lane of the state machine this caller is in.

    Follows what they were granted, not `principal.kind` — a student placement
    coordinator is a real role and would otherwise be locked out of the job
    they were appointed to do. Acting on their OWN application drops them back
    to the student lane, which is the self-approval guard.
    """
    if actor is None:
        return sm.SYSTEM
    if getattr(actor, "kind", None) == "recruiter":
        return sm.RECRUITER
    if scoping.is_staff(actor):
        own = (application is not None
               and application.user_id == getattr(actor, "user_id", None))
        return sm.STUDENT if own else sm.STAFF
    return sm.STUDENT


def _guard_conduct_sanction(application) -> None:
    """Rule 19's first tier bars the next two drives, not the season, so the
    season-wide debarred flag cannot express it."""
    from modules.placement.services import conduct as conduct_service

    registration = PlacementRegistration.objects.filter(
        policy__season=application.posting.placement_year,
        user_id=application.user_id).first()
    if registration is None:
        return
    if conduct_service.bars_posting(registration, application.posting):
        raise ConflictError(
            registration.debarred_reason
            or "A placement sanction is in force against your registration.",
            code="conduct_sanction")


def resolve_or_raise(frm: str, to: str, kind: str):
    """`sm.resolve` with its errors translated. Every path into the state
    machine must use this, or an illegal move surfaces as a 500."""
    try:
        return sm.resolve(frm, to, kind)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"An application cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition",
            details=[{"from": exc.frm, "to": exc.to,
                      "allowed": sm.allowed_targets(exc.frm, kind)}],
        ) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed",
            details=[{"from": exc.frm, "to": exc.to, "actor": exc.actor_kind}],
        ) from exc


def _guard(name: str, *, application, reason: str, actor) -> None:
    posting = application.posting
    now = timezone.now()

    if name == "has_reason" and not (reason or "").strip():
        raise ConflictError("A reason is required for this decision.",
                            code="reason_required")

    if name == "window_open":
        if posting.status != "published":
            raise ConflictError("This posting is not open for applications.",
                                code="posting_not_published")
        if posting.opens_at and now < posting.opens_at:
            raise ConflictError("Applications for this posting have not opened.",
                                code="window_not_open")
        if posting.closes_at and now > posting.closes_at:
            raise ConflictError("Applications for this posting have closed.",
                                code="window_closed")

    if name == "profile_complete":
        # PC-BR-001, answered by the ERP portal, which owns the one profile.
        person = directory.get_users([application.user_id]).get(application.user_id)
        if not getattr(person, "profile_completed", False):
            raise ConflictError(
                "Complete your profile on the Fusion portal before applying.",
                code="profile_incomplete")

    if name == "is_eligible":
        snapshot = application.eligibility_snapshot or {}
        if not snapshot.get("is_eligible"):
            raise ConflictError("You are not eligible for this posting.",
                                code="not_eligible",
                                details=snapshot.get("failed", []))

    if name == "may_apply":
        decision = (application.eligibility_snapshot or {}).get("season_decision")
        if decision and not decision.get("allowed"):
            raise ConflictError(decision.get("message", "You may not apply."),
                                code=decision.get("rule", "not_allowed"))
        _guard_conduct_sanction(application)

    if name == "has_scheduled_round" and not RoundParticipation.objects.filter(
            application=application).exists():
        raise ConflictError(
            "Schedule the candidate into an interview round first.",
            code="no_round_scheduled")

    if name == "company_authorized" and not posting.company.can_operate:
        raise ConflictError("This company is not currently authorized.",
                            code="company_not_approved")


@transaction.atomic
def transition(*, application_id: int, to_status: str, actor,
               reason: str = "", scope=None) -> Application:
    """Move one application. `scope` makes an out-of-scope one a 404."""
    qs = scope if scope is not None else Application.objects.all()
    app = (qs.select_for_update().select_related("posting", "posting__company")
           .filter(pk=application_id).first())
    if app is None:
        raise NotFoundError("No such application.")

    kind = actor_kind(actor, app)
    t = resolve_or_raise(app.status, to_status, kind)

    # Recruiters hold no codes; the company-scoped queryset is their authority.
    if kind in (sm.STAFF, sm.STUDENT) and not actor.has_permission(t.permission):
        raise PermissionDeniedError(f"This action needs {t.permission}.",
                                    code="permission_denied")

    for g in t.guards:
        _guard(g, application=app, reason=reason, actor=actor)

    frm, app.status = app.status, to_status
    touched = ["status", "updated_at"]
    if to_status == sm.SUBMITTED:
        app.applied_at = timezone.now()
        touched.append("applied_at")
    if to_status in (sm.WITHDRAWN, sm.AUTO_WITHDRAWN) and reason:
        app.withdrawn_reason = reason[:300]
        touched.append("withdrawn_reason")
    app.save(update_fields=touched)

    ApplicationTransition.objects.create(
        application=app, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None),
        actor_recruiter_id=getattr(actor, "account_id", None)
        if kind == sm.RECRUITER else None,
        actor_label=kind, reason=reason,
    )

    _notify_transition(app, to_status)
    return app


def _notify_transition(app: Application, to_status: str) -> None:
    topics = {
        sm.SHORTLISTED: ("application.shortlisted", "You have been shortlisted"),
        sm.REJECTED: ("application.rejected", "Update on your application"),
        sm.SUBMITTED: ("application.submitted", "Application received"),
    }
    entry = topics.get(to_status)
    if entry is None:
        return
    topic, subject = entry
    notifications.enqueue(
        topic=topic, dedupe_key=f"{topic}:{app.pk}:{to_status}",
        recipient_user_id=app.user_id,
        subject=f"{subject} — {app.posting.title}",
        body=f"Your application for {app.posting.title} is now {to_status}.",
        payload={"application_id": app.pk, "status": to_status},
    )


# -- Creating an application ---------------------------------------------------
@transaction.atomic
def apply_to(*, posting_id: int, actor, cover_note: str = "",
             resume_id: int | None = None) -> Application:
    """Create and submit in one step (PC-UC-003).

    Eligibility is frozen onto the row, so the decision stays reproducible
    after a CPI or rule change. That snapshot is what an appeal is judged on.
    """
    posting = (JobPosting.objects.select_related("company").get(pk=posting_id))
    user = actor.user

    if not user.has_permission("placement.application"):
        raise PermissionDeniedError("You do not have permission to apply for this posting.",
                                    code="permission_denied")

    # Check eligibility
    snapshot = elig.snapshot(user, posting)
    if not snapshot.get("is_eligible"):
        raise ConflictError(
            "You are not eligible for this posting.",
            code="not_eligible",
            details=snapshot.get("failed", []))

    # Create application
    app = Application.objects.create(
        user=user,
        posting=posting,
        cover_note=cover_note,
        resume_id=resume_id,
    )

    # Submit application
    transition(application_id=app.pk, to_status="submitted", actor=actor)

    return app

# BR-EL-020: Leave application creation and submission
def create_leave_application(*, user, leave_type, start_date, end_date, reason):
    """Create a new leave application."""
    if not user.has_permission("elm.leave"):
        raise PermissionDeniedError("You do not have permission to apply for leave.",
                                    code="permission_denied")

    # Check eligibility
    snapshot = elig.snapshot(user)
    if not snapshot.get("is_eligible", False):
        raise ConflictError(
            "You are not eligible for this leave type.",
            code="not_eligible",
            details=snapshot.get("failed", []))

    # Create application
    app = Leave.objects.create(
        user=user,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )

    return app

# BR-EL-021: Immediate withdrawal of pending request
def withdraw_leave_application(*, application_id, actor):
    """Withdraw a pending leave application."""
    qs = scoping.scope_by_user(actor)
    app = (qs.select_for_update().select_related("user")
           .filter(pk=application_id).first())
    if app is None:
        raise NotFoundError("No such application.")

    kind = actor_kind(actor, app)
    t = resolve_or_raise(app.status, "withdrawn", kind)

    # Recruiters hold no codes; the company-scoped queryset is their authority.
    if kind in (sm.STAFF, sm.STUDENT) and not actor.has_permission(t.permission):
        raise PermissionDeniedError(f"This action needs {t.permission}.",
                                    code="permission_denied")

    for g in t.guards:
        _guard(g, application=app, reason="", actor=actor)

    frm, app.status = app.status, "withdrawn"
    touched = ["status", "updated_at"]
    if to_status == sm.WITHDRAWN and reason:
        app.withdrawn_reason = reason[:300]
        touched.append("withdrawn_reason")
    app.save(update_fields=touched)

    ApplicationTransition.objects.create(
        application=app, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None),
        actor_recruiter_id=getattr(actor, "account_id", None)
        if kind == sm.RECRUITER else None,
        actor_label=kind, reason="",
    )

    _notify_transition(app, to_status)
    return app

# BR-EL-023: Cancellation of approved leave before start
def cancel_leave_application(*, application_id, actor):
    """Cancel an approved leave application."""
    qs = scoping.scope_by_user(actor)
    app = (qs.select_for_update().select_related("user")
           .filter(pk=application_id).first())
    if app is None:
        raise NotFoundError("No such application.")

    kind = actor_kind(actor, app)
    t = resolve_or_raise(app.status, "cancelled", kind)

    # Recruiters hold no codes; the company-scoped queryset is their authority.
    if kind in (sm.STAFF, sm.STUDENT) and not actor.has_permission(t.permission):
        raise PermissionDeniedError(f"This action needs {t.permission}.",
                                    code="permission_denied")

    for g in t.guards:
        _guard(g, application=app, reason="", actor=actor)

    frm, app.status = app.status, "cancelled"
    touched = ["status", "updated_at"]
    if to_status == sm.CANCELLED and reason:
        app.cancelled_reason = reason[:300]
        touched.append("cancelled_reason")
    app.save(update_fields=touched)

    ApplicationTransition.objects.create(
        application=app, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None),
        actor_recruiter_id=getattr(actor, "account_id", None)
        if kind == sm.RECRUITER else None,
        actor_label=kind, reason="",
    )

    _notify_transition(app, to_status)
    return app

# BR-EL-024: Extension of approved leave
def extend_leave_application(*, application_id, days, actor):
    """Extend an approved leave application."""
    qs = scoping.scope_by_user(actor)
    app = (qs.select_for_update().select_related("user")
           .filter(pk=application_id).first())
    if app is None:
        raise NotFoundError("No such application.")

    kind = actor_kind(actor, app)
    t = resolve_or_raise(app.status, "extended", kind)

    # Recruiters hold no codes; the company-scoped queryset is their authority.
    if kind in (sm.STAFF, sm.STUDENT) and not actor.has_permission(t.permission):
        raise PermissionDeniedError(f"This action needs {t.permission}.",
                                    code="permission_denied")

    for g in t.guards:
        _guard(g, application=app, reason="", actor=actor)

    frm, app.status = app.status, "extended"
    touched = ["status", "updated_at"]
    if to_status == sm.EXTENDED and reason:
        app.extended_reason = reason[:300]
        touched.append("extended_reason")
    app.save(update_fields=touched)

    ApplicationTransition.objects.create(
        application=app, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None),
        actor_recruiter_id=getattr(actor, "account_id", None)
        if kind == sm.RECRUITER else None,
        actor_label=kind, reason="",
    )

    _notify_transition(app, to_status)
    return app

# BR-EL-025: Resumption of approved leave
def resume_leave_application(*, application_id, actual_date, details, actor):
    """Resume an approved leave application."""
    qs = scoping.scope_by_user(actor)
    app = (qs.select_for_update().select_related("user")
           .filter(pk=application_id).first())
    if app is None:
        raise NotFoundError("No such application.")

    kind = actor_kind(actor, app)
    t = resolve_or_raise(app.status, "resumed", kind)

    # Recruiters hold no codes; the company-scoped queryset is their authority.
    if kind in (sm.STAFF, sm.STUDENT) and not actor.has_permission(t.permission):
        raise PermissionDeniedError(f"This action needs {t.permission}.",
                                    code="permission_denied")

    for g in t.guards:
        _guard(g, application=app, reason="", actor=actor)

    frm, app.status = app.status, "resumed"
    touched = ["status", "updated_at"]
    if to_status == sm.RESUMED and reason:
        app.resumed_reason = reason[:300]
        touched.append("resumed_reason")
    app.save(update_fields=touched)

    ApplicationTransition.objects.create(
        application=app, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None),
        actor_recruiter_id=getattr(actor, "account_id", None)
        if kind == sm.RECRUITER else None,
        actor_label=kind, reason="",
    )

    _notify_transition(app, to_status)
    return app
