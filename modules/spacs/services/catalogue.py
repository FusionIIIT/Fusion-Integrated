"""Catalogue administration service (CFR-SPACS-002, BR-SPACS-014, BR-SPACS-015)."""
from __future__ import annotations

from typing import Any
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.models import SchemeCatalogue, SchemePolicyVersion
from modules.spacs.services.audit import record_audit_event


def create_catalogue_entry(
    *,
    code: str,
    name: str,
    scheme_type: str,
    description: str = "",
    actor,
) -> SchemeCatalogue:
    if actor is None or not actor.has_permission("spacs.catalogue.manage"):
        raise PermissionDeniedError("Only authorized SPACS administrators can manage catalogue entries.")

    if SchemeCatalogue.objects.filter(code=code).exists():
        raise ConflictError(f"A scheme with code {code!r} already exists.", code="duplicate_code")

    with transaction.atomic():
        scheme = SchemeCatalogue.objects.create(
            code=code,
            name=name,
            scheme_type=scheme_type,
            description=description,
            status="draft",
        )
        record_audit_event(
            actor_user_id=getattr(actor, "user_id", None),
            actor_role="spacs_convener",
            action="catalogue.created",
            entity_type="scheme_catalogue",
            entity_id=str(scheme.id),
            details={"code": code, "name": name, "scheme_type": scheme_type},
        )
        return scheme


def create_policy_version(
    *,
    scheme_id: int,
    title: str,
    description: str = "",
    eligibility_criteria: dict[str, Any] | None = None,
    required_documents: list[dict[str, Any]] | None = None,
    candidate_source_method: str = "application",
    is_renewable: bool = False,
    renewal_rules: dict[str, Any] | None = None,
    policy_approval_reference: str = "",
    policy_approved_by: str = "",
    effective_from=None,
    effective_to=None,
    application_window_start=None,
    application_window_end=None,
    renewal_window_start=None,
    renewal_window_end=None,
    sla_verification_days: int = 7,
    sla_decision_days: int = 14,
    actor,
) -> SchemePolicyVersion:
    if actor is None or not actor.has_permission("spacs.catalogue.manage"):
        raise PermissionDeniedError("Permission denied.")

    scheme = SchemeCatalogue.objects.filter(pk=scheme_id).first()
    if scheme is None:
        raise NotFoundError("Scheme not found.")

    with transaction.atomic():
        latest_version = SchemePolicyVersion.objects.filter(scheme=scheme).order_by("-version_number").first()
        next_ver = (latest_version.version_number + 1) if latest_version else 1

        version = SchemePolicyVersion.objects.create(
            scheme=scheme,
            version_number=next_ver,
            title=title or f"{scheme.name} Policy v{next_ver}",
            description=description,
            eligibility_criteria=eligibility_criteria or {},
            required_documents=required_documents or [],
            candidate_source_method=candidate_source_method,
            is_renewable=is_renewable,
            renewal_rules=renewal_rules or {},
            policy_approval_reference=policy_approval_reference,
            policy_approved_by=policy_approved_by,
            effective_from=effective_from,
            effective_to=effective_to,
            application_window_start=application_window_start,
            application_window_end=application_window_end,
            renewal_window_start=renewal_window_start,
            renewal_window_end=renewal_window_end,
            sla_verification_days=sla_verification_days,
            sla_decision_days=sla_decision_days,
            status="draft",
        )
        record_audit_event(
            actor_user_id=getattr(actor, "user_id", None),
            actor_role="spacs_convener",
            action="catalogue.version_created",
            entity_type="scheme_policy_version",
            entity_id=str(version.id),
            details={"scheme_code": scheme.code, "version_number": next_ver},
        )
        return version


def publish_policy_version(*, version_id: int, actor) -> SchemePolicyVersion:
    """Publishes a policy version (AFR-SPACS-005, BR-SPACS-015).

    Requires policy approval reference and effective dates.
    """
    if actor is None or not actor.has_permission("spacs.catalogue.manage"):
        raise PermissionDeniedError("Permission denied.")

    version = SchemePolicyVersion.objects.select_related("scheme").filter(pk=version_id).first()
    if version is None:
        raise NotFoundError("Policy version not found.")

    # Guard: BR-SPACS-015
    if not (version.policy_approval_reference or "").strip():
        raise ConflictError(
            "Publication requires an approved policy reference (e.g. Senate/Director approval).",
            code="missing_policy_approval",
        )

    if not version.effective_from:
        raise ConflictError(
            "Publication requires an effective start date.",
            code="missing_effective_date",
        )

    with transaction.atomic():
        version.status = "published"
        version.save(update_fields=["status", "updated_at"])

        scheme = version.scheme
        scheme.status = "published"
        scheme.save(update_fields=["status", "updated_at"])

        record_audit_event(
            actor_user_id=getattr(actor, "user_id", None),
            actor_role="spacs_convener",
            action="catalogue.version_published",
            entity_type="scheme_policy_version",
            entity_id=str(version.id),
            details={
                "scheme_code": scheme.code,
                "version_number": version.version_number,
                "approval_ref": version.policy_approval_reference,
            },
        )
        return version


def retire_catalogue_entry(*, scheme_id: int, reason: str, actor) -> SchemeCatalogue:
    """Retires a catalogue entry prospectively (AFR-SPACS-006). Preserves historical records."""
    if actor is None or not actor.has_permission("spacs.catalogue.manage"):
        raise PermissionDeniedError("Permission denied.")

    scheme = SchemeCatalogue.objects.filter(pk=scheme_id).first()
    if scheme is None:
        raise NotFoundError("Scheme not found.")

    if not (reason or "").strip():
        raise ConflictError("A retirement reason is required.", code="reason_required")

    with transaction.atomic():
        scheme.status = "retired"
        scheme.retired_at = timezone.now()
        scheme.retired_reason = reason
        scheme.save(update_fields=["status", "retired_at", "retired_reason", "updated_at"])

        # Also retire versions
        scheme.versions.filter(status="published").update(status="retired")

        record_audit_event(
            actor_user_id=getattr(actor, "user_id", None),
            actor_role="spacs_convener",
            action="catalogue.retired",
            entity_type="scheme_catalogue",
            entity_id=str(scheme.id),
            details={"scheme_code": scheme.code, "reason": reason},
        )
        return scheme
