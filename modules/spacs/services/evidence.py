from collections.abc import Mapping
from typing import BinaryIO
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.models import (
    Application,
    ApplicationEvidence,
    AuditEvent,
    WorkflowTask,
)
from modules.spacs.services import applications
from modules.spacs.services.contracts import (
    DocumentStorage,
    configured_document_storage,
)
from modules.spacs.services.errors import IntegrationUnavailableError

_EDITABLE_STATES = {"Not Started / Draft", "Correction Required"}
_REVIEW_ROLES = {"SPACS Assistant", "SPACS Convener"}


def _owned_application(*, public_id: UUID, user_id: int) -> Application:
    application = (
        Application.objects.select_for_update()
        .select_related("catalogue_version")
        .filter(public_id=public_id, user_id=user_id)
        .first()
    )
    if application is None:
        raise NotFoundError("No such application.")
    if application.state not in _EDITABLE_STATES:
        raise ConflictError(
            "Evidence can only be changed while the application is editable.",
            code="application_not_editable",
        )
    return application


def _requirement_exists(application: Application, requirement_id: str) -> None:
    requirements = applications.configured_evidence_requirements(
        application.catalogue_version.configuration
    )
    if requirement_id not in {row.requirement_id for row in requirements}:
        raise BadRequestError(
            "The evidence requirement is not part of this application policy.",
            code="unknown_evidence_requirement",
        )


def _storage(storage: DocumentStorage | None) -> DocumentStorage:
    return storage if storage is not None else configured_document_storage()


def _storage_reference(reference: str) -> str:
    if not isinstance(reference, str) or not reference.strip():
        raise IntegrationUnavailableError(
            "The document storage provider returned an invalid reference."
        )
    return reference


@transaction.atomic
def upload(
    *,
    public_id: UUID,
    user_id: int,
    requirement_id: str,
    filename: str,
    content_type: str,
    content: BinaryIO,
    storage: DocumentStorage | None = None,
) -> ApplicationEvidence:
    if not requirement_id.strip() or not filename.strip() or not content_type.strip():
        raise BadRequestError(
            "A requirement, filename, and content type are required.",
            code="invalid_evidence_metadata",
        )
    application = _owned_application(public_id=public_id, user_id=user_id)
    _requirement_exists(application, requirement_id)
    provider = _storage(storage)
    reference = _storage_reference(
        provider.store(
            filename=filename,
            content_type=content_type,
            content=content,
        )
    )
    evidence = ApplicationEvidence.objects.create(
        application=application,
        requirement_id=requirement_id,
        storage_reference=reference,
        metadata={"filename": filename, "content_type": content_type},
        uploaded_by_user_id=user_id,
    )
    AuditEvent.objects.create(
        aggregate_type="application",
        aggregate_id=str(application.public_id),
        event_type="application.evidence_uploaded",
        actor_user_id=user_id,
        actor_label="Student",
        payload={
            "evidence_id": evidence.pk,
            "requirement_id": requirement_id,
        },
    )
    return evidence


@transaction.atomic
def reuse(
    *,
    public_id: UUID,
    user_id: int,
    evidence_id: int,
    requirement_id: str,
    storage: DocumentStorage | None = None,
) -> ApplicationEvidence:
    application = _owned_application(public_id=public_id, user_id=user_id)
    _requirement_exists(application, requirement_id)
    prior = (
        ApplicationEvidence.objects.select_for_update()
        .filter(
            pk=evidence_id,
            application__user_id=user_id,
            requirement_id=requirement_id,
        )
        .exclude(application=application)
        .first()
    )
    if prior is None:
        raise NotFoundError("No reusable evidence matches this requirement.")
    provider = _storage(storage)
    if not provider.is_valid(
        storage_reference=prior.storage_reference,
        requirement_id=requirement_id,
    ):
        raise ConflictError(
            "The previously uploaded evidence is no longer valid for this requirement.",
            code="evidence_not_reusable",
        )
    evidence = ApplicationEvidence.objects.create(
        application=application,
        requirement_id=requirement_id,
        storage_reference=prior.storage_reference,
        metadata=dict(prior.metadata),
        uploaded_by_user_id=user_id,
    )
    AuditEvent.objects.create(
        aggregate_type="application",
        aggregate_id=str(application.public_id),
        event_type="application.evidence_reused",
        actor_user_id=user_id,
        actor_label="Student",
        payload={
            "evidence_id": evidence.pk,
            "source_evidence_id": prior.pk,
            "requirement_id": requirement_id,
        },
    )
    return evidence


def reusable(
    *,
    public_id: UUID,
    user_id: int,
    requirement_id: str,
    storage: DocumentStorage | None = None,
) -> list[ApplicationEvidence]:
    application = (
        Application.objects.select_related("catalogue_version")
        .filter(public_id=public_id, user_id=user_id)
        .first()
    )
    if application is None:
        raise NotFoundError("No such application.")
    _requirement_exists(application, requirement_id)
    provider = _storage(storage)
    prior_rows = ApplicationEvidence.objects.filter(
        application__user_id=user_id,
        requirement_id=requirement_id,
    ).exclude(application=application)
    return [
        row
        for row in prior_rows.order_by("-created_at")
        if provider.is_valid(
            storage_reference=row.storage_reference,
            requirement_id=requirement_id,
        )
    ]


def open_for_review(
    *,
    public_id: UUID,
    evidence_id: int,
    user_id: int,
    storage: DocumentStorage | None = None,
) -> tuple[ApplicationEvidence, BinaryIO]:
    evidence = (
        ApplicationEvidence.objects.select_related("application")
        .filter(
            pk=evidence_id,
            application__public_id=public_id,
        )
        .first()
    )
    if evidence is None:
        raise NotFoundError("No such application evidence.")
    task_access = (
        WorkflowTask.objects.filter(
            application=evidence.application,
            role_name__in=_REVIEW_ROLES,
            completed_at__isnull=True,
        )
        .filter(
            # A null assignment is a role queue, not an individual assignment.
            Q(assigned_user_id__isnull=True) | Q(assigned_user_id=user_id)
        )
        .exists()
    )
    if evidence.application.user_id != user_id and not task_access:
        raise NotFoundError("No such application evidence.")
    metadata = evidence.metadata
    if not isinstance(metadata, Mapping):
        raise IntegrationUnavailableError(
            "Evidence metadata required to open this document is unavailable."
        )
    provider = _storage(storage)
    return evidence, provider.open(evidence.storage_reference)
