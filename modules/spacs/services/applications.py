"""SPACS Scholarship Application Service (CFR-SPACS-003, 004, 005, 009, 010, 011)."""

import uuid
from datetime import date
from django.utils import timezone

from ..domain.rules import (
    assert_ownership,
    check_no_duplicate,
    preserve_draft_payload,
    validate_can_modify,
    validate_can_withdraw,
    validate_catalogue_published_and_open,
    validate_completeness,
    validate_document_reuse,
    validate_download_access,
    validate_eligibility,
)
from ..domain.state_machine import (
    CORRECTION_REQUIRED,
    DRAFT,
    RESUBMITTED,
    SUBMITTED,
    WITHDRAWN,
    resolve_application_transition,
)
from ..models import (
    SpacsApplication,
    SpacsCatalogueEntry,
    SpacsDocument,
)
from .audit import log_action, notify_user
from .tasks import close_pending_tasks, create_task


def create_draft_application(
    scheme_code: str,
    applicant_user_id: int,
    academic_cycle: str = "2026-27",
    application_data: dict | None = None,
) -> SpacsApplication:
    """Initiate a scholarship application draft (AFR-SPACS-008, AFR-SPACS-014)."""
    catalogue = SpacsCatalogueEntry.objects.get(scheme_code=scheme_code)
    now = timezone.now()

    # BR-SPACS-014: published & open window check
    validate_catalogue_published_and_open(
        catalogue.status,
        catalogue.application_window_start,
        catalogue.application_window_end,
        now,
    )

    # BR-SPACS-002: duplicate check
    existing_states = SpacsApplication.objects.filter(
        catalogue_entry=catalogue,
        applicant_user_id=applicant_user_id,
        academic_cycle=academic_cycle,
        is_renewal=False,
    ).values_list("state", flat=True)
    check_no_duplicate(existing_states)

    # Generate unique ID (AFR-SPACS-016)
    unique_id = f"SPACS-APP-{uuid.uuid4().hex[:8].upper()}"

    app = SpacsApplication.objects.create(
        application_id=unique_id,
        catalogue_entry=catalogue,
        catalogue_version=catalogue.version,
        applicant_user_id=applicant_user_id,
        academic_cycle=academic_cycle,
        state=DRAFT,
        application_data=application_data or {},
    )

    log_action(
        event_type="application_draft_created",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=applicant_user_id,
        details={"scheme_code": scheme_code, "cycle": academic_cycle},
    )
    return app


def update_draft(
    application_id: str,
    acting_user_id: int,
    data_updates: dict,
) -> SpacsApplication:
    """Save draft changes and preserve input (AFR-SPACS-011, AFR-SPACS-014, BR-SPACS-007, BR-SPACS-010)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)
    validate_can_modify(app.state)

    app.application_data = preserve_draft_payload(app.application_data, data_updates)
    if "cpi" in data_updates:
        app.cpi = data_updates["cpi"]
    if "family_income" in data_updates:
        app.family_income = data_updates["family_income"]
    app.save()

    return app


def upload_document(
    application_id: str,
    acting_user_id: int,
    document_type: str,
    file_path: str,
    valid_until: date | None = None,
) -> SpacsDocument:
    """Upload a supporting document for an application (AFR-SPACS-012)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)
    validate_can_modify(app.state)

    doc = SpacsDocument.objects.create(
        application=app,
        user_id=acting_user_id,
        document_type=document_type,
        file_path=file_path,
        valid_until=valid_until,
    )
    log_action(
        event_type="document_uploaded",
        entity_type="document",
        entity_id=str(doc.id),
        actor_user_id=acting_user_id,
        details={"doc_type": document_type, "app_id": application_id},
    )
    return doc


def reuse_prior_document(
    application_id: str,
    acting_user_id: int,
    prior_document_id: int,
    required_doc_type: str,
) -> SpacsDocument:
    """Reuse an existing valid uploaded document (AFR-SPACS-013, BR-SPACS-003)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)
    validate_can_modify(app.state)

    prior_doc = SpacsDocument.objects.get(id=prior_document_id)
    validate_document_reuse(
        doc_user_id=prior_doc.user_id,
        applicant_user_id=acting_user_id,
        doc_type=prior_doc.document_type,
        required_doc_type=required_doc_type,
        doc_valid_until=prior_doc.valid_until,
        reference_date=date.today(),
    )

    reused_doc = SpacsDocument.objects.create(
        application=app,
        user_id=acting_user_id,
        document_type=required_doc_type,
        file_path=prior_doc.file_path,
        valid_until=prior_doc.valid_until,
        is_verified=False,
    )
    log_action(
        event_type="document_reused",
        entity_type="document",
        entity_id=str(reused_doc.id),
        actor_user_id=acting_user_id,
        details={"source_doc_id": prior_document_id, "app_id": application_id},
    )
    return reused_doc


def submit_application(
    application_id: str,
    acting_user_id: int,
    student_cpi: float,
    student_family_income: float | None = None,
    mandatory_field_keys: list[str] | None = None,
) -> SpacsApplication:
    """Submit application for verification (AFR-SPACS-009, 015, 016, 017, 018)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)

    catalogue = app.catalogue_entry

    # BR-SPACS-001: machine-checkable eligibility
    validate_eligibility(
        student_cpi=student_cpi,
        student_family_income=student_family_income,
        min_cpi=float(catalogue.min_cpi),
        max_family_income=float(catalogue.max_family_income) if catalogue.max_family_income else None,
    )

    # BR-SPACS-004: completeness check
    uploaded_docs = app.documents.values_list("document_type", flat=True)
    required_docs = catalogue.required_documents or []
    mandatory_fields = mandatory_field_keys or []
    validate_completeness(
        application_data=app.application_data,
        mandatory_fields=mandatory_fields,
        uploaded_doc_types=uploaded_docs,
        required_doc_types=required_docs,
    )

    # State transition DRAFT -> SUBMITTED (BW-SPACS-01)
    transition = resolve_application_transition(app.state, "submit", "student")
    app.state = transition.target
    app.cpi = student_cpi
    app.family_income = student_family_income
    app.submitted_at = timezone.now()
    app.catalogue_version = catalogue.version
    app.save()

    # Route task to Assistant (AFR-SPACS-017)
    create_task(
        task_type="verification",
        entity_type="application",
        entity_id=app.application_id,
        assigned_role="spacs_assistant",
    )

    # Notify student and assistant (AFR-SPACS-018, BR-SPACS-008)
    notify_user(
        recipient_user_id=acting_user_id,
        event_type="submitted",
        title="Application Submitted",
        message=f"Your scholarship application {app.application_id} has been successfully submitted.",
    )

    log_action(
        event_type="application_submitted",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=acting_user_id,
        details={"version": app.catalogue_version, "cpi": student_cpi},
    )
    return app


def modify_application_in_correction(
    application_id: str,
    acting_user_id: int,
    data_updates: dict,
) -> SpacsApplication:
    """Modify an application in Correction Required state (AFR-SPACS-022, AFR-SPACS-031)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)
    validate_can_modify(app.state)

    app.application_data = preserve_draft_payload(app.application_data, data_updates)
    if "cpi" in data_updates:
        app.cpi = data_updates["cpi"]
    if "family_income" in data_updates:
        app.family_income = data_updates["family_income"]
    app.save()

    log_action(
        event_type="application_corrected",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=acting_user_id,
        details={"updates": data_updates},
    )
    return app


def resubmit_application(
    application_id: str,
    acting_user_id: int,
    mandatory_field_keys: list[str] | None = None,
) -> SpacsApplication:
    """Resubmit corrected application, revalidating and invalidating prior verification (AFR-SPACS-023, BR-SPACS-011)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)

    catalogue = app.catalogue_entry

    # Re-evaluate eligibility if CPI/income present
    if app.cpi is not None:
        validate_eligibility(
            student_cpi=float(app.cpi),
            student_family_income=float(app.family_income) if app.family_income else None,
            min_cpi=float(catalogue.min_cpi),
            max_family_income=float(catalogue.max_family_income) if catalogue.max_family_income else None,
        )

    # Re-evaluate completeness
    uploaded_docs = app.documents.values_list("document_type", flat=True)
    validate_completeness(
        application_data=app.application_data,
        mandatory_fields=mandatory_field_keys or [],
        uploaded_doc_types=uploaded_docs,
        required_doc_types=catalogue.required_documents or [],
    )

    # Transition CORRECTION_REQUIRED -> RESUBMITTED (BW-SPACS-02)
    transition = resolve_application_transition(app.state, "resubmit", "student")
    app.state = transition.target

    # Invalidate prior verification findings & authenticity
    app.verification_findings = ""
    app.verification_authenticity_confirmed = False
    app.correction_reason = ""
    app.save()

    # Route task to assistant again
    create_task(
        task_type="verification",
        entity_type="application",
        entity_id=app.application_id,
        assigned_role="spacs_assistant",
    )

    notify_user(
        recipient_user_id=acting_user_id,
        event_type="resubmitted",
        title="Application Resubmitted",
        message=f"Application {app.application_id} has been resubmitted for verification.",
    )

    log_action(
        event_type="application_resubmitted",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=acting_user_id,
    )
    return app


def withdraw_application(
    application_id: str,
    acting_user_id: int,
    convener_review_started: bool = False,
) -> SpacsApplication:
    """Withdraw application before final decision (AFR-SPACS-033, 034, BR-SPACS-009, 010)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    assert_ownership(app.applicant_user_id, acting_user_id)
    validate_can_withdraw(app.state, convener_review_started)

    transition = resolve_application_transition(app.state, "withdraw", "student")
    app.state = transition.target
    app.save()

    # Close pending tasks
    close_pending_tasks(entity_type="application", entity_id=app.application_id)

    notify_user(
        recipient_user_id=acting_user_id,
        event_type="withdrawn",
        title="Application Withdrawn",
        message=f"Application {app.application_id} has been successfully withdrawn.",
    )

    log_action(
        event_type="application_withdrawn",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=acting_user_id,
    )
    return app


def export_application(
    application_id: str,
    acting_user_id: int,
    acting_user_roles: list[str],
) -> dict:
    """Download/export application data with permission checks (AFR-SPACS-036, BR-SPACS-012)."""
    app = SpacsApplication.objects.get(application_id=application_id)
    validate_download_access(app.applicant_user_id, acting_user_id, acting_user_roles)

    log_action(
        event_type="application_exported",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=acting_user_id,
    )

    return {
        "application_id": app.application_id,
        "scheme": app.catalogue_entry.name,
        "applicant_user_id": app.applicant_user_id,
        "academic_cycle": app.academic_cycle,
        "state": app.state,
        "cpi": float(app.cpi) if app.cpi else None,
        "family_income": float(app.family_income) if app.family_income else None,
        "application_data": app.application_data,
        "submitted_at": str(app.submitted_at) if app.submitted_at else None,
        "decision": {
            "actor": app.decision_actor_user_id,
            "reason": app.decision_reason,
            "at": str(app.decision_at) if app.decision_at else None,
        },
    }
