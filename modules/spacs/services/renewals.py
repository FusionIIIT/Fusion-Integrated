"""Scholarship renewal lifecycle services for SPACS.

Enforces:
- CFR-SPACS-012 (Scholarship Renewal)
- BR-SPACS-017 (Renewal uses scheme-specific rules and fresh decision - no auto-approval)
- UC-SPACS-015 (Apply for Scholarship Renewal)
- BW-SPACS-06, BW-SPACS-07, BW-SPACS-10, CW-SPACS-02
"""
from __future__ import annotations

from typing import Any
from django.db import transaction
from django.utils import timezone as dj_timezone

from core.api.exceptions import ValidationError, NotFoundError, PermissionDenied
from modules.spacs.domain.renewal import check_renewal_eligibility, is_document_reusable
from modules.spacs.models import (
    ScholarshipApplication,
    ApplicationDocument,
    CataloguePolicyVersion,
)
from modules.spacs.services.applications import save_draft, submit_application
from modules.spacs.services.audit import record_audit_event


def initiate_renewal(
    prior_application_id: int,
    user_id: int,
    new_academic_cycle: str,
    active_policy_version: CataloguePolicyVersion,
) -> ScholarshipApplication:
    """Initiates a renewal draft prefilled with reusable information (UC-SPACS-015, AFR-SPACS-038)."""
    with transaction.atomic():
        prior_app = (
            ScholarshipApplication.objects.filter(pk=prior_application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .prefetch_related("documents")
            .first()
        )
        if not prior_app:
            raise NotFoundError("Prior scholarship application record not found.")
        if prior_app.user_id != user_id:
            raise PermissionDenied("You can only renew your own scholarship award.")

        next_cycle_number = prior_app.renewal_cycle_number + 1
        policy_dict = {
            "is_renewable": active_policy_version.is_renewable,
            "max_renewal_cycles": active_policy_version.max_renewal_cycles,
        }
        prior_dict = {"status": prior_app.status}

        is_eligible, deficiencies = check_renewal_eligibility(
            policy_dict, prior_dict, next_cycle_number
        )
        if not is_eligible:
            raise ValidationError(f"Renewal not permissible: {'; '.join(deficiencies)}")

        # Create new renewal application draft
        renewal_app = save_draft(
            user_id=user_id,
            policy_version=active_policy_version,
            academic_cycle=new_academic_cycle,
            submission_data=prior_app.submission_data,
            applicant_snapshot=prior_app.applicant_snapshot,
        )
        renewal_app.is_renewal = True
        renewal_app.prior_award = prior_app
        renewal_app.renewal_cycle_number = next_cycle_number
        renewal_app.save()

        # Identify reusable documents
        today = dj_timezone.now().date()
        for doc in prior_app.documents.all():
            doc_data = {
                "doc_type": doc.doc_type,
                "drive_url": doc.drive_url,
                "drive_file_id": doc.drive_file_id,
                "declared_validity_date": doc.declared_validity_date,
            }
            if is_document_reusable(doc_data, doc.doc_type, today):
                ApplicationDocument.objects.create(
                    application=renewal_app,
                    user_id=user_id,
                    doc_type=doc.doc_type,
                    title=f"[Reused] {doc.title}",
                    drive_file_id=doc.drive_file_id,
                    drive_url=doc.drive_url,
                    declared_validity_date=doc.declared_validity_date,
                    is_reused=True,
                    reused_from_doc_id=doc.id,
                    verification_status="pending",
                )

        record_audit_event(
            action="renewal.draft_created",
            entity_type="ScholarshipApplication",
            entity_id=renewal_app.id,
            actor_user_id=user_id,
            actor_role="student",
            details={
                "prior_app_id": prior_app.id,
                "cycle": new_academic_cycle,
                "cycle_number": next_cycle_number,
            },
        )

        return renewal_app
