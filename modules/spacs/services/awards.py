"""Convocation awards and prizes service (CW-SPACS-03, BW-SPACS-08, 09, 11).

Administers candidate pools, committee evaluations, institutional approvals, and result publication.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.domain import award_state_machine as asm
from modules.spacs.models import (
    AwardCandidate,
    AwardCycle,
    AwardCycleTransition,
    SchemeCatalogue,
    SchemePolicyVersion,
)
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import notify


def create_award_cycle(
    *,
    scheme_id: int,
    academic_cycle: str,
    convocation_year: int,
    evaluating_body: str,
    committee_members: list[int] | None = None,
    actor,
) -> AwardCycle:
    if actor is None or not actor.has_permission("spacs.award.manage"):
        raise PermissionDeniedError("Permission denied.")

    scheme = SchemeCatalogue.objects.filter(pk=scheme_id).first()
    if scheme is None:
        raise NotFoundError("Scheme not found.")

    version = (
        SchemePolicyVersion.objects.filter(scheme=scheme, status="published")
        .order_by("-version_number")
        .first()
    )
    if version is None:
        raise ConflictError("No active published policy version found for this award scheme.")

    if AwardCycle.objects.filter(scheme=scheme, convocation_year=convocation_year).exists():
        raise ConflictError(
            f"An award cycle for {scheme.name} in Convocation {convocation_year} already exists.",
            code="cycle_exists",
        )

    with transaction.atomic():
        cycle = AwardCycle.objects.create(
            scheme=scheme,
            policy_version=version,
            academic_cycle=academic_cycle,
            convocation_year=convocation_year,
            evaluating_body=evaluating_body,
            committee_members=committee_members or [],
            status=asm.OPEN,
        )
        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            action="award_cycle.created",
            entity_type="award_cycle",
            entity_id=str(cycle.id),
            details={"scheme_code": scheme.code, "year": convocation_year},
        )
        return cycle


def prepare_candidate_pool(
    *,
    award_cycle_id: int,
    candidates: list[dict[str, Any]],
    actor,
) -> AwardCycle:
    """Prepares and finalizes candidate pool for committee review (UC-SPACS-017, BW-SPACS-08)."""
    if actor is None or not actor.has_permission("spacs.award.manage"):
        raise PermissionDeniedError("Permission denied.")

    with transaction.atomic():
        cycle = AwardCycle.objects.select_for_update().filter(pk=award_cycle_id).first()
        if cycle is None:
            raise NotFoundError("Award cycle not found.")

        if cycle.status != asm.OPEN:
            raise ConflictError(f"Candidate pool cannot be prepared in '{cycle.status}' status.")

        if not candidates:
            raise ConflictError("At least one candidate is required to prepare the pool.", code="empty_pool")

        for c in candidates:
            cpi_val = c.get("cpi")
            cpi_dec = Decimal(str(cpi_val)) if cpi_val is not None else None
            AwardCandidate.objects.update_or_create(
                award_cycle=cycle,
                student_user_id=c["student_user_id"],
                defaults={
                    "source_method": c.get("source_method", cycle.policy_version.candidate_source_method),
                    "cpi": cpi_dec,
                    "discipline": c.get("discipline", ""),
                    "merit_data": c.get("merit_data", {}),
                    "recommendation_status": "pending",
                    "final_outcome": "pending",
                },
            )

        asm.resolve_award_transition(asm.OPEN, asm.POOL_PREPARED, asm.CONVENER)
        from_st = cycle.status
        cycle.status = asm.POOL_PREPARED
        cycle.save(update_fields=["status", "updated_at"])

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=from_st,
            to_status=asm.POOL_PREPARED,
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            reason=f"Candidate pool prepared with {len(candidates)} candidate(s).",
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            action="award_cycle.pool_prepared",
            entity_type="award_cycle",
            entity_id=str(cycle.id),
            details={"candidates_count": len(candidates)},
        )
        return cycle


def record_committee_evaluations(
    *,
    award_cycle_id: int,
    evaluations: list[dict[str, Any]],
    actor,
) -> AwardCycle:
    """Committee evaluates candidates and records shortlists/recommendations (UC-SPACS-018, BW-SPACS-08)."""
    if actor is None or not (actor.has_permission("spacs.award.review") or actor.has_permission("spacs.award.manage")):
        raise PermissionDeniedError("Permission denied.")

    with transaction.atomic():
        cycle = AwardCycle.objects.select_for_update().filter(pk=award_cycle_id).first()
        if cycle is None:
            raise NotFoundError("Award cycle not found.")

        if cycle.status not in [asm.POOL_PREPARED, asm.UNDER_EVALUATION]:
            raise ConflictError(f"Evaluations cannot be recorded in '{cycle.status}' status.")

        from_st = cycle.status

        for ev in evaluations:
            cand = AwardCandidate.objects.filter(award_cycle=cycle, student_user_id=ev["student_user_id"]).first()
            if cand is not None:
                if "score" in ev and ev["score"] is not None:
                    cand.evaluation_score = Decimal(str(ev["score"]))
                if "remarks" in ev:
                    cand.evaluation_remarks = ev["remarks"]
                if "is_shortlisted" in ev:
                    cand.is_shortlisted = bool(ev["is_shortlisted"])
                if "recommendation_status" in ev:
                    cand.recommendation_status = ev["recommendation_status"]
                cand.save()

        # Transition to RESULT_RECORDED
        cycle.status = asm.RESULT_RECORDED
        cycle.save(update_fields=["status", "updated_at"])

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=from_st,
            to_status=asm.RESULT_RECORDED,
            actor_user_id=actor.user_id,
            actor_role="award_committee",
            reason=f"Recorded evaluations for {len(evaluations)} candidate(s).",
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="award_committee",
            action="award_cycle.results_recorded",
            entity_type="award_cycle",
            entity_id=str(cycle.id),
            details={"evaluations_count": len(evaluations)},
        )
        return cycle


def record_final_approval(
    *,
    award_cycle_id: int,
    approval_reference: str = "",
    approving_authority: str = "",
    approved_candidate_ids: list[int] | None = None,
    actor,
) -> AwardCycle:
    """Records final institutional award approval (UC-SPACS-019, BW-SPACS-09, BW-SPACS-11, BR-SPACS-019)."""
    if actor is None or not actor.has_permission("spacs.award.approve"):
        raise PermissionDeniedError("Permission denied.")

    with transaction.atomic():
        cycle = AwardCycle.objects.select_for_update().filter(pk=award_cycle_id).first()
        if cycle is None:
            raise NotFoundError("Award cycle not found.")

        if cycle.status not in [asm.RESULT_RECORDED, asm.AWAITING_APPROVAL]:
            raise ConflictError(f"Approval cannot be recorded in '{cycle.status}' status.")

        from_st = cycle.status
        now = timezone.now()

        # If institutional approval reference is available (BW-SPACS-09 / BW-SPACS-11 step 2)
        if approval_reference.strip():
            cycle.status = asm.READY_FOR_PUBLICATION
            cycle.approval_reference = approval_reference
            cycle.approving_authority = approving_authority or cycle.policy_version.policy_approved_by or "Senate"
            cycle.approval_recorded_at = now
            cycle.approval_recorded_by_user_id = actor.user_id
            cycle.save()

            if approved_candidate_ids is not None:
                # Mark approved candidates
                AwardCandidate.objects.filter(
                    award_cycle=cycle,
                    student_user_id__in=approved_candidate_ids,
                ).update(final_outcome="approved")
                # Mark others rejected
                AwardCandidate.objects.filter(
                    award_cycle=cycle,
                ).exclude(student_user_id__in=approved_candidate_ids).update(final_outcome="rejected")

            reason_text = f"Approved by {cycle.approving_authority} (ref: {approval_reference}). Ready for publication."
        else:
            # Approval is pending (BW-SPACS-11 step 1)
            cycle.status = asm.AWAITING_APPROVAL
            cycle.save(update_fields=["status", "updated_at"])
            reason_text = "Committee results recorded; awaiting institutional approval evidence."

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=from_st,
            to_status=cycle.status,
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            reason=reason_text,
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            action="award_cycle.approval_recorded",
            entity_type="award_cycle",
            entity_id=str(cycle.id),
            details={
                "from_status": from_st,
                "to_status": cycle.status,
                "approval_reference": approval_reference,
            },
        )
        return cycle


def publish_award_results(
    *,
    award_cycle_id: int,
    actor,
) -> AwardCycle:
    """Publishes approved award results (UC-SPACS-020, AFR-SPACS-046).

    Guarded: cannot publish without final approval outcome recorded!
    """
    if actor is None or not actor.has_permission("spacs.award.publish"):
        raise PermissionDeniedError("Permission denied.")

    with transaction.atomic():
        cycle = AwardCycle.objects.select_for_update().filter(pk=award_cycle_id).first()
        if cycle is None:
            raise NotFoundError("Award cycle not found.")

        # Guard: AFR-SPACS-046: Must be READY_FOR_PUBLICATION
        if cycle.status != asm.READY_FOR_PUBLICATION:
            raise ConflictError(
                f"Award results cannot be published from '{cycle.status}' status. Required approval must be recorded first.",
                code="premature_publication",
            )

        from_st = cycle.status
        now = timezone.now()

        cycle.status = asm.PUBLISHED
        cycle.published_at = now
        cycle.published_by_user_id = actor.user_id
        cycle.save(update_fields=["status", "published_at", "published_by_user_id", "updated_at"])

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=from_st,
            to_status=asm.PUBLISHED,
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            reason="Published approved convocation award results",
        )

        # Notify awardees
        approved_awardees = AwardCandidate.objects.filter(award_cycle=cycle, final_outcome="approved")
        for awardee in approved_awardees:
            notify(
                recipient_user_id=awardee.student_user_id,
                recipient_role="student",
                event_type="award.published",
                title=f"Award Announcement: {cycle.scheme.name}",
                message=f"Congratulations! You have been awarded {cycle.scheme.name} for Convocation {cycle.convocation_year}.",
                reference_id=str(cycle.id),
            )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            action="award_cycle.published",
            entity_type="award_cycle",
            entity_id=str(cycle.id),
            details={"convocation_year": cycle.convocation_year, "scheme": cycle.scheme.name},
        )
        return cycle
