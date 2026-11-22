"""Transactional application services and state machine choke-point.

All state transitions flow through transition_application() under select_for_update().
Enforces BR-PMS-014..017, BR-PMS-020..027, BR-PMS-029..036, BR-PMS-038, BR-PMS-040..046,
BR-PMS-067..070, BR-PMS-092..095, BR-PMS-126..128, BR-PMS-130.
"""
from __future__ import annotations

import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.domain import filing as fil
from modules.patents.domain import state_machine as sm
from modules.patents.domain import validation as val
from modules.patents.models import (
    AppealRecord,
    AttorneyPanelMember,
    CoInventor,
    PatentApplication,
    PatentPolicy,
    ReviewDecision,
)
from modules.patents.selectors import scoping


def actor_lane(actor, application: PatentApplication | None = None) -> str:
    """Determine the state machine lane for the acting principal."""
    if actor is None:
        return sm.SYSTEM
    if scoping.is_pcc_admin(actor):
        return sm.PCC_ADMIN
    if scoping.is_director(actor):
        # Self-approval guard: if director authored the application, drop to applicant lane
        if application is not None and application.user_id == getattr(actor, "user_id", None):
            return sm.APPLICANT
        return sm.DIRECTOR
    if scoping.is_attorney(actor):
        return sm.ATTORNEY
    return sm.APPLICANT


def generate_application_number() -> str:
    """Generate a unique application number like PMS-2026-0001."""
    year = timezone.now().year
    prefix = f"PMS-{year}-"
    last_app = (
        PatentApplication.objects.filter(application_number__startswith=prefix)
        .order_by("-id")
        .first()
    )
    if last_app:
        try:
            seq = int(last_app.application_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def create_application(
    actor,
    title: str,
    abstract: str,
    description: str,
    claims: str,
    domain_category: str = "",
    co_inventors: list[dict] | None = None,
    jurisdiction: str = "IN",
) -> PatentApplication:
    """Create a new patent application in DRAFT status."""
    if not scoping.has_pms_access(actor):
        raise PermissionDeniedError("Valid PMS role required to create application.")

    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        raise PermissionDeniedError("Actor has no identity.")

    val.validate_application_fields(title, abstract, description, claims)

    if co_inventors:
        shares = [Decimal(str(c.get("share_percentage", 0))) for c in co_inventors]
        val.validate_ownership_shares(shares)

    app_num = generate_application_number()

    with transaction.atomic():
        app = PatentApplication.objects.create(
            user_id=user_id,
            application_number=app_num,
            title=title,
            abstract=abstract,
            description=description,
            claims=claims,
            domain_category=domain_category,
            jurisdiction=jurisdiction,
            status=sm.DRAFT,
            version=1,
        )
        if co_inventors:
            for c in co_inventors:
                CoInventor.objects.create(
                    application=app,
                    user_id=c.get("user_id"),
                    name=c["name"],
                    email=c["email"],
                    share_percentage=Decimal(str(c["share_percentage"])),
                )
    return app


def update_application(
    actor,
    application_id: int,
    title: str | None = None,
    abstract: str | None = None,
    description: str | None = None,
    claims: str | None = None,
    domain_category: str | None = None,
) -> PatentApplication:
    """Update an application in DRAFT, NEEDS_REVISION, or REJECTED status."""
    scope = scoping.applications_for(actor)
    with transaction.atomic():
        app = scope.select_for_update().filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("Patent application not found.")

        if app.status not in (sm.DRAFT, sm.NEEDS_REVISION, sm.REJECTED):
            raise ConflictError(f"Application in status {app.status} cannot be edited.")

        # BR-PMS-035: If REJECTED, must be within 60 days of decision_date
        if app.status == sm.REJECTED and app.decision_date:
            deadline = app.decision_date + datetime.timedelta(days=60)
            if timezone.now() > deadline:
                raise ConflictError("Resubmission period of 60 days has expired.")

        if title is not None:
            app.title = title
        if abstract is not None:
            app.abstract = abstract
        if description is not None:
            app.description = description
        if claims is not None:
            app.claims = claims
        if domain_category is not None:
            app.domain_category = domain_category

        val.validate_application_fields(app.title, app.abstract, app.description, app.claims)
        app.version += 1
        app.save()
    return app


def record_coinventor_consent(actor, application_id: int) -> bool:
    """Record consent for a co-inventor."""
    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        raise PermissionDeniedError("Actor has no identity.")

    with transaction.atomic():
        ci = CoInventor.objects.filter(application_id=application_id, user_id=user_id).first()
        if ci is None:
            raise NotFoundError("No co-inventor record found for current user.")
        ci.consent_granted = True
        ci.consent_timestamp = timezone.now()
        ci.save()
    return True


def _decrement_attorney_workload(user_id: int | None) -> None:
    if not user_id:
        return
    member = AttorneyPanelMember.objects.filter(user_id=user_id).first()
    if member and member.active_workload > 0:
        member.active_workload -= 1
        member.save(update_fields=["active_workload"])


def transition_application(
    application_id: int,
    event: str,
    actor,
    payload: dict | None = None,
    scope: QuerySet | None = None,
) -> PatentApplication:
    """Single transactional choke-point for all patent application state progression."""
    if payload is None:
        payload = {}

    if scope is None:
        scope = scoping.applications_for(actor)

    with transaction.atomic():
        app = scope.select_for_update().filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("Patent application not found.")

        lane = actor_lane(actor, app)

        # Resolve target state from event and payload
        to_status: str | None = None
        if event == "submit":
            to_status = sm.SUBMITTED
        elif event == "assign_director":
            to_status = sm.UNDER_REVIEW
            director_id = payload.get("director_id")
            if not director_id:
                raise BadRequestError("director_id required for assign_director.")
            val.validate_coi(app.user_id, director_id)
            for ci_uid in app.co_inventors.values_list("user_id", flat=True):
                if ci_uid:
                    val.validate_coi(ci_uid, director_id)
        elif event == "submit_review":
            decision = payload.get("decision")
            justification = payload.get("justification", "")
            if decision not in ("APPROVE", "REJECT", "NEEDS_REVISION"):
                raise ConflictError(f"Decision {decision!r} is invalid.")
            val.validate_justification(justification)
            to_status = {
                "APPROVE": sm.APPROVED,
                "REJECT": sm.REJECTED,
                "NEEDS_REVISION": sm.NEEDS_REVISION,
            }[decision]
        elif event == "assign_attorney":
            to_status = sm.ASSIGNMENT_OFFERED
            attorney_id = payload.get("attorney_id")
            if not attorney_id:
                raise BadRequestError("attorney_id required for assign_attorney.")
            member = AttorneyPanelMember.objects.filter(
                user_id=attorney_id, is_approved_panel=True
            ).first()
            if not member:
                raise ConflictError("Selected attorney is not an approved panel member.")
            policy = PatentPolicy.objects.filter(is_active=True).first()
            if (
                policy
                and policy.max_attorney_workload is not None
                and member.active_workload >= policy.max_attorney_workload
            ):
                raise ConflictError(
                    "Attorney has reached maximum active workload capacity (BR-PMS-043)."
                )
        elif event == "accept_assignment":
            to_status = sm.ATTORNEY_ASSIGNED
        elif event == "decline_assignment":
            to_status = sm.PENDING_REVIEW
        elif event == "start_assessment":
            to_status = sm.ASSESSMENT_IN_PROGRESS
        elif event == "file_external":
            to_status = sm.FILED
            has_approved_budget = app.budget_entries.filter(status="APPROVED").exists()
            all_consented = all(ci.consent_granted for ci in app.co_inventors.all())
            clearance = fil.evaluate_filing_clearance(
                has_inventor_agreements=all_consented,
                has_budget_approval=has_approved_budget,
                has_format_compliance=True,
            )
            if not clearance.cleared:
                raise ConflictError("; ".join(clearance.reasons))
        elif event == "grant":
            to_status = sm.GRANTED
        elif event == "withdraw":
            to_status = sm.WITHDRAWN
            reason = payload.get("reason", "")
            if not reason.strip():
                raise BadRequestError("Mandatory reason required for withdrawal.")
            policy = PatentPolicy.objects.filter(is_active=True).first()
            eligible_states = tuple(policy.withdrawal_eligible_states) if policy else ()
            if app.status not in eligible_states:
                raise ConflictError(
                    f"Application status {app.status} is not eligible for withdrawal."
                )
        elif event == "file_appeal":
            to_status = sm.APPEAL_SUBMITTED
            grounds = payload.get("grounds", "")
            if not grounds.strip():
                raise BadRequestError("Grounds required to file appeal.")
            if app.status != sm.REJECTED:
                raise ConflictError("Appeal can only be filed against a REJECTED application.")
        elif event == "decide_appeal":
            outcome = payload.get("outcome")
            val.validate_appeal_outcome(outcome)
            to_status = {
                "REMAND": sm.REMANDED,
                "UPHOLD": sm.REJECTION_UPHELD,
                "MODIFY": sm.DECISION_MODIFIED,
            }[outcome]
        elif event == "resubmit":
            to_status = sm.RESUBMITTED
        elif event == "expire":
            to_status = sm.EXPIRED
        else:
            to_status = payload.get("to_status")

        if not to_status:
            raise BadRequestError(f"Cannot resolve target status for event {event!r}.")

        # Check state machine transition and actor lane
        try:
            sm.resolve(app.status, to_status, lane)
        except sm.InvalidTransition as err:
            raise ConflictError(str(err)) from err
        except sm.ActorNotAllowed as err:
            raise PermissionDeniedError(str(err)) from err

        # Perform side effects
        had_active_attorney = (
            bool(app.assigned_attorney_id)
            and app.status in {sm.ATTORNEY_ASSIGNED, sm.ASSESSMENT_IN_PROGRESS, sm.FILED}
        )

        if event == "assign_director":
            app.assigned_director_id = payload["director_id"]
        elif event == "submit_review":
            decision = payload["decision"]
            justification = payload["justification"]
            ReviewDecision.objects.create(
                application=app,
                director_user_id=getattr(actor, "user_id", 0),
                decision=decision,
                justification=justification,
            )
            if decision in ("REJECT", "NEEDS_REVISION"):
                app.decision_date = timezone.now()
        elif event == "assign_attorney":
            app.assigned_attorney_id = payload["attorney_id"]
        elif event == "accept_assignment":
            if app.assigned_attorney_id:
                member = AttorneyPanelMember.objects.filter(
                    user_id=app.assigned_attorney_id
                ).first()
                if member:
                    member.active_workload += 1
                    member.save(update_fields=["active_workload"])
        elif event == "decline_assignment":
            if app.assigned_attorney_id:
                _decrement_attorney_workload(app.assigned_attorney_id)
            app.assigned_attorney_id = None
        elif event == "withdraw":
            if had_active_attorney:
                _decrement_attorney_workload(app.assigned_attorney_id)
        elif event == "file_appeal":
            AppealRecord.objects.create(
                application=app,
                applicant_user_id=getattr(actor, "user_id", app.user_id),
                grounds=payload["grounds"],
            )
        elif event == "decide_appeal":
            appeal = app.appeals.order_by("-id").first()
            if appeal:
                appeal.status = payload["outcome"]
                appeal.director_user_id = getattr(actor, "user_id", 0)
                appeal.decision_notes = payload.get("notes", "")
                appeal.decided_at = timezone.now()
                appeal.save()
        elif event == "file_external":
            app.external_filing_id = payload.get("external_filing_id", f"IPO-{app.id}")
            app.filing_date = timezone.now().date()
        elif event == "grant":
            app.grant_date = timezone.now().date()
            if had_active_attorney:
                _decrement_attorney_workload(app.assigned_attorney_id)

        app.status = to_status
        app.version += 1
        app.save()

    return app
