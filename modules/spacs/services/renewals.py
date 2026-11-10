"""SPACS Scholarship Renewal Service (CFR-SPACS-012)."""

import uuid
from django.utils import timezone

from ..domain.rules import (
    assert_ownership,
    validate_completeness,
    validate_eligibility,
    validate_renewal_conditions,
)
from ..domain.state_machine import (
    DRAFT,
    RENEWAL_SUBMITTED,
    resolve_application_transition,
)
from ..models import SpacsApplication
from .audit import log_action, notify_user
from .tasks import create_task


def initiate_renewal(
    prior_application_id: str,
    acting_user_id: int,
    renewal_cycle: str = "2027-28",
) -> SpacsApplication:
    """Initiate a renewal application prefilling prior data (AFR-SPACS-037, AFR-SPACS-038, BR-SPACS-017)."""
    prior_app = SpacsApplication.objects.get(application_id=prior_application_id)
    assert_ownership(prior_app.applicant_user_id, acting_user_id)

    catalogue = prior_app.catalogue_entry
    now = timezone.now()

    # BR-SPACS-017: validate renewal conditions
    validate_renewal_conditions(
        parent_state=prior_app.state,
        renewal_allowed=catalogue.renewal_allowed,
        renewal_window_start=catalogue.renewal_window_start,
        renewal_window_end=catalogue.renewal_window_end,
        current_time=now,
    )

    renewal_id = f"SPACS-RNW-{uuid.uuid4().hex[:8].upper()}"

    # Prefill prior application data
    prefilled_data = dict(prior_app.application_data)
    prefilled_data["_renewal_of"] = prior_application_id

    renewal_app = SpacsApplication.objects.create(
        application_id=renewal_id,
        catalogue_entry=catalogue,
        catalogue_version=catalogue.version,
        applicant_user_id=acting_user_id,
        academic_cycle=renewal_cycle,
        is_renewal=True,
        parent_application=prior_app,
        state=DRAFT,
        cpi=prior_app.cpi,
        family_income=prior_app.family_income,
        application_data=prefilled_data,
    )

    log_action(
        event_type="renewal_draft_initiated",
        entity_type="application",
        entity_id=renewal_app.application_id,
        actor_user_id=acting_user_id,
        details={"parent_application_id": prior_application_id, "cycle": renewal_cycle},
    )
    return renewal_app


def submit_renewal(
    renewal_application_id: str,
    acting_user_id: int,
    current_cpi: float,
    current_family_income: float | None = None,
    mandatory_field_keys: list[str] | None = None,
) -> SpacsApplication:
    """Submit renewal application for fresh verification and decision (AFR-SPACS-039, AFR-SPACS-040, BW-SPACS-06)."""
    app = SpacsApplication.objects.get(application_id=renewal_application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)

    catalogue = app.catalogue_entry

    # Validate renewed eligibility
    validate_eligibility(
        student_cpi=current_cpi,
        student_family_income=current_family_income,
        min_cpi=float(catalogue.min_cpi),
        max_family_income=float(catalogue.max_family_income) if catalogue.max_family_income else None,
    )

    # Validate completeness
    uploaded_docs = app.documents.values_list("document_type", flat=True)
    validate_completeness(
        application_data=app.application_data,
        mandatory_fields=mandatory_field_keys or [],
        uploaded_doc_types=uploaded_docs,
        required_doc_types=catalogue.required_documents or [],
    )

    # Transition DRAFT -> RENEWAL_SUBMITTED (BW-SPACS-06)
    transition = resolve_application_transition(app.state, "submit_renewal", "student")
    app.state = transition.target
    app.cpi = current_cpi
    app.family_income = current_family_income
    app.submitted_at = timezone.now()
    app.save()

    # Route renewal verification task to assistant (never auto-approve! BR-SPACS-017)
    create_task(
        task_type="renewal_verification",
        entity_type="application",
        entity_id=app.application_id,
        assigned_role="spacs_assistant",
    )

    notify_user(
        recipient_user_id=acting_user_id,
        event_type="submitted",
        title="Scholarship Renewal Submitted",
        message=f"Your renewal application {app.application_id} has been submitted for verification.",
    )

    log_action(
        event_type="renewal_submitted",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=acting_user_id,
        details={"cpi": current_cpi},
    )
    return app


def send_renewal_reminders(scheme_code: str) -> list[int]:
    """Send reminders to eligible students for renewal (AFR-SPACS-041)."""
    eligible_apps = SpacsApplication.objects.filter(
        catalogue_entry__scheme_code=scheme_code,
        state="approved",
        is_renewal=False,
    )
    reminded_users = []
    for app in eligible_apps:
        notify_user(
            recipient_user_id=app.applicant_user_id,
            event_type="renewal_reminder",
            title="Scholarship Renewal Window Open",
            message=f"The renewal window for scheme {app.catalogue_entry.name} is now open. Submit your renewal before the deadline.",
        )
        reminded_users.append(app.applicant_user_id)

    return reminded_users
