"""PMS Application submission, revision, and withdrawal service.

Enforces business rules BR-PMS-014 through 017, BR-PMS-033 through 036, and BR-PMS-067 through 070.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import (
    validate_coinventor_shares,
    validate_document,
)
from modules.pms.domain.errors import (
    DeadlineExceededError,
    PreconditionNotMetError,
    WithdrawalNotAllowedError,
)
from modules.pms.domain.state_machine import (
    WITHDRAWAL_ELIGIBLE_STATES,
    PatentApplicationStatus,
    validate_transition,
)
from modules.pms.models import (
    ApplicationDocument,
    CoInventor,
    PatentApplication,
    PatentBudget,
)
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def generate_application_no() -> str:
    """Generate a sequential, unique application identifier."""
    year = timezone.now().year
    count = PatentApplication.objects.filter(created_at__year=year).count() + 1
    return f"PMS-{year}-{count:04d}"


def submit_application(
    *,
    applicant_user_id: int,
    title: str,
    abstract: str,
    detailed_description: str,
    claims: str,
    domain: str,
    jurisdiction: str = "IN",
    is_international: bool = False,
    international_justification: str = "",
    preferred_attorney_id: int | None = None,
    coinventors_data: list[dict[str, Any]] | None = None,
    documents_data: list[dict[str, Any]] | None = None,
) -> PatentApplication:
    """Submit a new patent application with validation (UC-PMS-001, CFR-PMS-005)."""
    # Validate required fields (BR-PMS-017)
    if not title or not title.strip():
        raise PreconditionNotMetError("Application title is required (BR-PMS-017).")
    if not abstract or not abstract.strip():
        raise PreconditionNotMetError("Application abstract is required (BR-PMS-017).")
    if not detailed_description or not detailed_description.strip():
        raise PreconditionNotMetError("Detailed description is required (BR-PMS-017).")
    if not claims or not claims.strip():
        raise PreconditionNotMetError("Patent claims are required (BR-PMS-017).")
    if not domain or not domain.strip():
        raise PreconditionNotMetError("Application domain is required.")

    # Validate documents if provided (BR-PMS-014, 015, 016)
    if documents_data:
        for doc in documents_data:
            validate_document(
                filename=doc.get("filename", doc.get("title", "document.pdf")),
                file_size_bytes=doc.get("file_size_bytes", 0),
                is_malware_clean=doc.get("is_clean", True),
            )

    # Validate inventor ownership shares (BR-PMS-074)
    if coinventors_data:
        shares = [Decimal(str(c.get("ownership_percentage", "0"))) for c in coinventors_data]
        validate_coinventor_shares(shares)

    with transaction.atomic():
        app_no = generate_application_no()
        app = PatentApplication.objects.create(
            application_no=app_no,
            title=title.strip(),
            abstract=abstract.strip(),
            detailed_description=detailed_description.strip(),
            claims=claims.strip(),
            domain=domain.strip(),
            status=PatentApplicationStatus.SUBMITTED.value,
            applicant_user_id=applicant_user_id,
            jurisdiction=jurisdiction,
            is_international=is_international,
            international_justification=international_justification.strip(),
            preferred_attorney_id=preferred_attorney_id,
        )

        # Create Budget entity
        PatentBudget.objects.create(
            application=app,
            filing_fees=Decimal("0.00"),
            attorney_fees=Decimal("0.00"),
            administrative_costs=Decimal("0.00"),
            total_cost=Decimal("0.00"),
            status="draft",
        )

        # Create Co-Inventors
        if coinventors_data:
            for c in coinventors_data:
                CoInventor.objects.create(
                    application=app,
                    user_id=c.get("user_id"),
                    name=c.get("name", "").strip(),
                    email=c.get("email", "").strip(),
                    department=c.get("department", "").strip(),
                    ownership_percentage=Decimal(str(c.get("ownership_percentage", "0"))),
                    consent_given=c.get("consent_given", False),
                    agreement_signed=c.get("agreement_signed", False),
                    electronic_signature=c.get("electronic_signature", ""),
                )

        # Create Documents
        if documents_data:
            for doc in documents_data:
                ApplicationDocument.objects.create(
                    application=app,
                    doc_type=doc.get("doc_type", "specification"),
                    title=doc.get("title", "Document"),
                    file_format=doc.get("file_format", "pdf"),
                    file_size_bytes=doc.get("file_size_bytes", 0),
                    malware_scanned=True,
                    is_clean=True,
                    sensitivity=doc.get("sensitivity", "confidential"),
                    version=1,
                    is_current=True,
                    uploaded_by_user_id=applicant_user_id,
                    file_url=doc.get("file_url", ""),
                )

        log_audit(
            application=app,
            actor_user_id=applicant_user_id,
            action_type="application_submitted",
            from_state=PatentApplicationStatus.DRAFT.value,
            to_state=app.status,
            details={"title": app.title, "domain": app.domain},
        )

        enqueue_notification(
            topic="application.submitted",
            dedupe_key=f"pms:app:submitted:{app.id}",
            subject=f"PMS: Application Submitted ({app.application_no})",
            body=f"Your patent application '{app.title}' has been successfully submitted.",
            recipient_user_id=applicant_user_id,
        )

    return app


def revise_and_resubmit_application(
    *,
    application_id: int,
    applicant_user_id: int,
    feedback_response: str,
    title: str | None = None,
    abstract: str | None = None,
    detailed_description: str | None = None,
    claims: str | None = None,
    new_documents_data: list[dict[str, Any]] | None = None,
) -> PatentApplication:
    """Revise and resubmit an application under revision or rejection (UC-PMS-005, CFR-PMS-008)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # The route permission only proves that the caller may revise PMS
        # applications in general. Keep the object-level ownership check in
        # the service as well so callers cannot revise another inventor's
        # application by changing the URL.
        if app.applicant_user_id != applicant_user_id:
            raise PreconditionNotMetError("Only the primary applicant may revise an application.")

        # Precondition check: must be Needs Revision or Rejected (BR-PMS-033, 034)
        if app.status not in (
            PatentApplicationStatus.NEEDS_REVISION.value,
            PatentApplicationStatus.REJECTED.value,
            PatentApplicationStatus.REMANDED_FOR_AMENDMENT.value,
        ):
            raise PreconditionNotMetError(
                f"Application status '{app.status}' cannot be revised. Must be Needs Revision, Rejected, or Remanded."
            )

        # Check revision deadline: must be within 60 days (BR-PMS-035)
        if app.revision_deadline and timezone.now() > app.revision_deadline:
            raise DeadlineExceededError(
                "Resubmission deadline has expired. Application cannot be revised (BR-PMS-035)."
            )

        # Validate feedback response (BR-PMS-036)
        if not feedback_response or len(feedback_response.strip()) < 10:
            raise PreconditionNotMetError(
                "A revised application must include notes addressing Director feedback (BR-PMS-036)."
            )

        # Validate state transition
        validate_transition(app.status, PatentApplicationStatus.RESUBMITTED, actor_role="Applicant")
        prev_status = app.status

        # Update application content
        if title:
            app.title = title.strip()
        if abstract:
            app.abstract = abstract.strip()
        if detailed_description:
            app.detailed_description = detailed_description.strip()
        if claims:
            app.claims = claims.strip()

        app.status = PatentApplicationStatus.RESUBMITTED.value
        app.save()

        # Handle document versioning (BR-PMS-082, 087)
        if new_documents_data:
            for doc in new_documents_data:
                validate_document(
                    filename=doc.get("filename", doc.get("title", "document.pdf")),
                    file_size_bytes=doc.get("file_size_bytes", 0),
                    is_malware_clean=doc.get("is_clean", True),
                )
                doc_type = doc.get("doc_type", "specification")
                # find latest version for this doc_type
                latest_doc = (
                    ApplicationDocument.objects.filter(application=app, doc_type=doc_type)
                    .order_by("-version")
                    .first()
                )
                new_ver = (latest_doc.version + 1) if latest_doc else 1

                # Archive previous current documents
                ApplicationDocument.objects.filter(
                    application=app, doc_type=doc_type, is_current=True
                ).update(is_current=False)

                ApplicationDocument.objects.create(
                    application=app,
                    doc_type=doc_type,
                    title=doc.get("title", f"{doc_type} v{new_ver}"),
                    file_format=doc.get("file_format", "pdf"),
                    file_size_bytes=doc.get("file_size_bytes", 0),
                    malware_scanned=True,
                    is_clean=True,
                    sensitivity=doc.get("sensitivity", "confidential"),
                    version=new_ver,
                    is_current=True,
                    uploaded_by_user_id=applicant_user_id,
                    file_url=doc.get("file_url", ""),
                )

        log_audit(
            application=app,
            actor_user_id=applicant_user_id,
            action_type="application_resubmitted",
            from_state=prev_status,
            to_state=app.status,
            details={"feedback_response": feedback_response},
        )

        enqueue_notification(
            topic="application.resubmitted",
            dedupe_key=f"pms:app:resubmitted:{app.id}:{timezone.now().timestamp()}",
            subject=f"PMS: Application Resubmitted ({app.application_no})",
            body=f"Application '{app.title}' has been resubmitted and will be reassigned for review.",
            recipient_user_id=applicant_user_id,
        )

    return app


def withdraw_application(
    *,
    application_id: int,
    applicant_user_id: int,
    reason: str,
) -> PatentApplication:
    """Withdraw a patent application before filing (UC-PMS-006, CFR-PMS-015)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Check ownership
        if app.applicant_user_id != applicant_user_id:
            raise PreconditionNotMetError("Only the primary applicant can withdraw an application.")

        # Check withdrawal eligibility before filing (BR-PMS-067, 068)
        if app.status not in WITHDRAWAL_ELIGIBLE_STATES or app.is_withdrawn:
            raise WithdrawalNotAllowedError(
                f"Application in status '{app.status}' cannot be withdrawn. Withdrawal only permitted before filing (BR-PMS-067)."
            )

        # Check applicant reason (BR-PMS-069)
        if not reason or not reason.strip():
            raise WithdrawalNotAllowedError("A withdrawal reason is required (BR-PMS-069).")

        # Check co-inventor consent (BR-PMS-070)
        unconsented = app.coinventors.filter(withdrawal_consent_given=False)
        if unconsented.exists():
            raise WithdrawalNotAllowedError(
                "All co-inventors must record consent before an application can be withdrawn (BR-PMS-070)."
            )

        validate_transition(
            app.status, PatentApplicationStatus.WITHDRAWN, actor_role="Applicant", reason=reason
        )
        prev_status = app.status

        app.status = PatentApplicationStatus.WITHDRAWN.value
        app.is_withdrawn = True
        app.withdrawal_reason = reason.strip()
        app.withdrawal_date = timezone.now()
        app.save()

        log_audit(
            application=app,
            actor_user_id=applicant_user_id,
            action_type="application_withdrawn",
            from_state=prev_status,
            to_state=app.status,
            details={"reason": reason},
        )

        enqueue_notification(
            topic="application.withdrawn",
            dedupe_key=f"pms:app:withdrawn:{app.id}",
            subject=f"PMS: Application Withdrawn ({app.application_no})",
            body=f"Patent application '{app.title}' has been withdrawn. Reason: {reason}",
            recipient_user_id=applicant_user_id,
        )

    return app
