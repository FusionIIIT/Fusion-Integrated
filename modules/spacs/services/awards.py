"""Convocation award pool preparation, evaluation, and publication services.

Enforces:
- CFR-SPACS-013 (Award Candidate Sourcing and Pool Preparation)
- CFR-SPACS-014 (Award Evaluation, Approval and Publication)
- BR-SPACS-019 (Award evaluation & approval follow award policy)
- BR-SPACS-020 (Award criteria versioning)
- BR-SPACS-023 (Award candidate source is scheme-specific)
- UC-SPACS-017, 018, 019, 020
- BW-SPACS-08, BW-SPACS-09, BW-SPACS-11, CW-SPACS-03
"""
from __future__ import annotations

from typing import Any
from django.db import transaction
from django.utils import timezone as dj_timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.spacs.domain.state_machines import (
    AWARD_STATUS_OPEN,
    AWARD_STATUS_POOL_PREPARED,
    AWARD_STATUS_UNDER_EVALUATION,
    AWARD_STATUS_RESULT_RECORDED,
    AWARD_STATUS_READY_PUBLICATION,
    AWARD_STATUS_PUBLISHED,
    can_transition_award_cycle,
)
from modules.spacs.models import (
    AwardCycle,
    AwardCandidate,
    AwardCycleTransition,
    CataloguePolicyVersion,
    SpacsTask,
)
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import enqueue as enqueue_notification


def open_award_cycle(
    policy_version: CataloguePolicyVersion,
    convocation_year: int,
    actor_user_id: int,
) -> AwardCycle:
    """Opens a new convocation award cycle (UC-SPACS-017, CW-SPACS-03).

    The cycle is created in the initial AWARD_STATUS_OPEN state; subsequent
    transitions (pool preparation, evaluation, approval, publication) are
    handled by their respective services.
    """
    with transaction.atomic():
        cycle = AwardCycle.objects.create(
            policy_version=policy_version,
            convocation_year=convocation_year,
            status=AWARD_STATUS_OPEN,
        )
        record_audit_event(
            action="award_cycle.opened",
            entity_type="AwardCycle",
            entity_id=cycle.id,
            actor_user_id=actor_user_id,
            actor_role="spacs_convener",
            details={
                "convocation_year": convocation_year,
                "policy_version_id": policy_version.pk,
            },
        )
        return cycle


def prepare_candidate_pool(
    cycle_id: int,
    convener_user_id: int,
    candidate_user_ids: list[int],
    snapshots_by_user: dict[int, dict[str, Any]] | None = None,
) -> AwardCycle:
    """Prepares and finalizes candidate pool for an award cycle (UC-SPACS-017, BW-SPACS-08)."""
    with transaction.atomic():
        cycle = (
            AwardCycle.objects.select_for_update()
            .filter(pk=cycle_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not cycle:
            raise NotFoundError("Award cycle not found.")

        transition = can_transition_award_cycle(
            from_status=cycle.status,
            to_status=AWARD_STATUS_POOL_PREPARED,
            actor_role="spacs_convener",
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        policy = cycle.policy_version
        source_method = policy.candidate_source_method
        snapshots = snapshots_by_user or {}

        # Populate candidates
        for uid in candidate_user_ids:
            AwardCandidate.objects.update_or_create(
                award_cycle=cycle,
                user_id=uid,
                defaults={
                    "source_method": source_method,
                    "academic_snapshot": snapshots.get(uid, {}),
                    "is_eligible": True,
                },
            )

        prev_status = cycle.status
        now = dj_timezone.now()
        cycle.status = AWARD_STATUS_POOL_PREPARED
        cycle.pool_finalized_at = now
        cycle.pool_finalized_by_user_id = convener_user_id
        cycle.save()

        # Create task for evaluation committee
        committee_role = policy.eval_committee_role or "award_eval_committee"
        SpacsTask.objects.create(
            award_cycle=cycle,
            task_type="award_evaluation",
            assigned_role=committee_role,
            policy_version=policy,
            sla_snapshot=policy.sla_config or {},
            status="pending",
        )

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=prev_status,
            to_status=AWARD_STATUS_POOL_PREPARED,
            actor_user_id=convener_user_id,
            actor_role_label="SPACS Convener",
            reason=f"Candidate pool prepared with {len(candidate_user_ids)} candidate(s)",
        )

        record_audit_event(
            action="award.pool_prepared",
            entity_type="AwardCycle",
            entity_id=cycle.id,
            actor_user_id=convener_user_id,
            actor_role="spacs_convener",
            details={"candidates_count": len(candidate_user_ids)},
        )

        return cycle


def record_committee_evaluations(
    cycle_id: int,
    evaluator_user_id: int,
    actor_role: str,
    evaluations: list[dict[str, Any]],  # [{'candidate_id': int, 'score': Decimal, 'recommendation': str, 'remarks': str}]
) -> AwardCycle:
    """Records committee evaluation, scoring, and shortlist (UC-SPACS-018, BW-SPACS-08)."""
    with transaction.atomic():
        cycle = (
            AwardCycle.objects.select_for_update()
            .filter(pk=cycle_id)
            .select_related("policy_version")
            .first()
        )
        if not cycle:
            raise NotFoundError("Award cycle not found.")

        # Update candidate scores
        for ev in evaluations:
            cand = AwardCandidate.objects.filter(pk=ev["candidate_id"], award_cycle=cycle).first()
            if cand:
                if "score" in ev and ev["score"] is not None:
                    cand.evaluation_score = ev["score"]
                if "recommendation" in ev:
                    cand.committee_recommendation = ev["recommendation"]
                if "remarks" in ev:
                    cand.committee_remarks = ev["remarks"]
                cand.save()

        prev_status = cycle.status
        now = dj_timezone.now()
        cycle.status = AWARD_STATUS_RESULT_RECORDED
        cycle.eval_completed_at = now
        cycle.save()

        # Close committee evaluation task
        SpacsTask.objects.filter(
            award_cycle=cycle, task_type="award_evaluation", status="pending"
        ).update(status="completed", completed_at=now, completed_by_user_id=evaluator_user_id)

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=prev_status,
            to_status=AWARD_STATUS_RESULT_RECORDED,
            actor_user_id=evaluator_user_id,
            actor_role_label=actor_role,
            reason="Committee evaluations and recommendations recorded",
        )

        record_audit_event(
            action="award.evaluated",
            entity_type="AwardCycle",
            entity_id=cycle.id,
            actor_user_id=evaluator_user_id,
            actor_role=actor_role,
            details={"evaluations_count": len(evaluations)},
        )

        return cycle


def record_institutional_approval(
    cycle_id: int,
    convener_user_id: int,
    approval_authority: str,
    approval_reference: str,
    winning_candidate_ids: list[int],
) -> AwardCycle:
    """Records final institutional approval outcome and winners (UC-SPACS-019, BW-SPACS-09, BW-SPACS-11)."""
    if not approval_reference.strip() or not approval_authority.strip():
        raise ConflictError("Recording final approval requires both approving authority and formal reference.")

    with transaction.atomic():
        cycle = (
            AwardCycle.objects.select_for_update()
            .filter(pk=cycle_id)
            .select_related("policy_version")
            .first()
        )
        if not cycle:
            raise NotFoundError("Award cycle not found.")

        # Flag winning candidates
        AwardCandidate.objects.filter(award_cycle=cycle).update(is_final_winner=False)
        AwardCandidate.objects.filter(
            award_cycle=cycle, pk__in=winning_candidate_ids
        ).update(is_final_winner=True)

        prev_status = cycle.status
        now = dj_timezone.now()
        cycle.status = AWARD_STATUS_READY_PUBLICATION
        cycle.approval_authority_recorded = approval_authority.strip()
        cycle.approval_reference_recorded = approval_reference.strip()
        cycle.approval_recorded_at = now
        cycle.save()

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=prev_status,
            to_status=AWARD_STATUS_READY_PUBLICATION,
            actor_user_id=convener_user_id,
            actor_role_label="SPACS Convener",
            reason=f"Approved by {approval_authority} (Ref: {approval_reference})",
        )

        record_audit_event(
            action="award.approval_recorded",
            entity_type="AwardCycle",
            entity_id=cycle.id,
            actor_user_id=convener_user_id,
            actor_role="spacs_convener",
            details={
                "authority": approval_authority,
                "reference": approval_reference,
                "winners": winning_candidate_ids,
            },
        )

        return cycle


def publish_award_results(
    cycle_id: int,
    convener_user_id: int,
) -> AwardCycle:
    """Publishes approved convocation award results officially (UC-SPACS-020, AFR-SPACS-046)."""
    with transaction.atomic():
        cycle = (
            AwardCycle.objects.select_for_update()
            .filter(pk=cycle_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not cycle:
            raise NotFoundError("Award cycle not found.")

        if not cycle.approval_reference_recorded:
            raise ConflictError("Award results cannot be published without recorded institutional approval.")

        transition = can_transition_award_cycle(
            from_status=cycle.status,
            to_status=AWARD_STATUS_PUBLISHED,
            actor_role="spacs_convener",
            approval_evidence_available=True,
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        prev_status = cycle.status
        now = dj_timezone.now()
        cycle.status = AWARD_STATUS_PUBLISHED
        cycle.published_at = now
        cycle.published_by_user_id = convener_user_id
        cycle.save()

        AwardCycleTransition.objects.create(
            award_cycle=cycle,
            from_status=prev_status,
            to_status=AWARD_STATUS_PUBLISHED,
            actor_user_id=convener_user_id,
            actor_role_label="SPACS Convener",
            reason="Official award publication confirmed",
        )

        record_audit_event(
            action="award.published",
            entity_type="AwardCycle",
            entity_id=cycle.id,
            actor_user_id=convener_user_id,
            actor_role="spacs_convener",
            details={
                "year": cycle.convocation_year,
                "scheme": cycle.policy_version.catalogue_entry.title,
            },
        )

        # Notify winners
        winners = AwardCandidate.objects.filter(award_cycle=cycle, is_final_winner=True)
        for w in winners:
            enqueue_notification(
                topic="award.published",
                dedupe_key=f"spacs.award.winner.{cycle.id}.{w.user_id}",
                subject=f"Convocation Award Announcement: {cycle.policy_version.catalogue_entry.title}",
                body=f"Congratulations! You have been awarded {cycle.policy_version.catalogue_entry.title} for convocation {cycle.convocation_year}.",
                recipient_user_id=w.user_id,
                payload={"award_cycle_id": cycle.id},
            )

        return cycle
