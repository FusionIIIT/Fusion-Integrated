"""SPACS Convocation Awards and Prizes Service (CFR-SPACS-013, CFR-SPACS-014)."""

from django.utils import timezone

from ..domain.rules import (
    filter_eligible_candidates,
    validate_award_criteria_version,
    validate_award_publication_allowed,
)
from ..domain.state_machine import (
    AWAITING_INSTITUTIONAL_APPROVAL,
    AWARD_CYCLE_OPEN,
    CANDIDATE_POOL_PREPARED,
    COMMITTEE_RESULT_RECORDED,
    PUBLISHED,
    READY_FOR_PUBLICATION,
    UNDER_COMMITTEE_EVALUATION,
    resolve_award_transition,
)
from ..models import (
    SpacsAwardCandidate,
    SpacsAwardCycle,
    SpacsCatalogueEntry,
)
from .audit import log_action, notify_user


def open_award_cycle(
    scheme_code: str,
    academic_cycle: str,
    convener_user_id: int,
) -> SpacsAwardCycle:
    """Open an award cycle for candidate preparation (AFR-SPACS-042)."""
    catalogue = SpacsCatalogueEntry.objects.get(scheme_code=scheme_code)
    cycle = SpacsAwardCycle.objects.create(
        catalogue_entry=catalogue,
        academic_cycle=academic_cycle,
        state=AWARD_CYCLE_OPEN,
        criteria_version=catalogue.version,
        prepared_by_user_id=convener_user_id,
    )
    log_action(
        event_type="award_cycle_opened",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=convener_user_id,
        details={"scheme": scheme_code, "cycle": academic_cycle},
    )
    return cycle


def prepare_candidate_pool(
    award_cycle_id: int,
    convener_user_id: int,
    candidate_records: list[dict],
) -> SpacsAwardCycle:
    """Prepare and finalize the candidate pool using configured method (AFR-SPACS-043, BR-SPACS-023, BW-SPACS-08)."""
    cycle = SpacsAwardCycle.objects.get(id=award_cycle_id)
    catalogue = cycle.catalogue_entry

    eligible_records = filter_eligible_candidates(
        candidates=candidate_records,
        source_method=catalogue.candidate_source_method,
        min_cpi=float(catalogue.min_cpi),
    )

    for rec in eligible_records:
        SpacsAwardCandidate.objects.update_or_create(
            award_cycle=cycle,
            student_user_id=rec["student_user_id"],
            defaults={
                "cpi": rec.get("cpi", 0.0),
                "academic_standing": rec.get("academic_standing", "good"),
                "shortlisted": rec.get("shortlisted", True),
            },
        )

    transition = resolve_award_transition(cycle.state, "prepare_pool", "spacs_convener")
    cycle.state = transition.target
    cycle.save()

    log_action(
        event_type="award_candidate_pool_prepared",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=convener_user_id,
        details={"candidate_count": len(eligible_records)},
    )
    return cycle


def begin_committee_evaluation(
    award_cycle_id: int,
    evaluator_user_id: int,
) -> SpacsAwardCycle:
    """Award Evaluation Committee begins evaluating shortlisted candidates (BW-SPACS-08)."""
    cycle = SpacsAwardCycle.objects.get(id=award_cycle_id)
    transition = resolve_award_transition(
        cycle.state, "begin_evaluation", "award_evaluation_committee"
    )
    cycle.state = transition.target
    cycle.save()

    log_action(
        event_type="committee_evaluation_started",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=evaluator_user_id,
    )
    return cycle


def record_committee_results(
    award_cycle_id: int,
    evaluator_user_id: int,
    candidate_scores: dict[int, dict],
) -> SpacsAwardCycle:
    """Record scores, shortlists and recommendations (AFR-SPACS-044, BW-SPACS-08)."""
    cycle = SpacsAwardCycle.objects.get(id=award_cycle_id)

    for student_id, score_info in candidate_scores.items():
        candidate = SpacsAwardCandidate.objects.get(award_cycle=cycle, student_user_id=student_id)
        if "score" in score_info:
            candidate.evaluation_score = score_info["score"]
        if "recommendation" in score_info:
            candidate.committee_recommendation = score_info["recommendation"]
        if "remarks" in score_info:
            candidate.remarks = score_info["remarks"]
        candidate.save()

    transition = resolve_award_transition(
        cycle.state, "record_committee_result", "award_evaluation_committee"
    )
    cycle.state = transition.target
    cycle.save()

    log_action(
        event_type="committee_results_recorded",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=evaluator_user_id,
        details={"evaluated_count": len(candidate_scores)},
    )
    return cycle


def record_final_award_outcome(
    award_cycle_id: int,
    convener_user_id: int,
    approval_evidence: str | None = None,
) -> SpacsAwardCycle:
    """Record approval reference; route to ready or awaiting approval (AFR-SPACS-045, BW-SPACS-09, BW-SPACS-11)."""
    cycle = SpacsAwardCycle.objects.get(id=award_cycle_id)

    if approval_evidence and approval_evidence.strip():
        # Approval available immediately -> BW-SPACS-09
        transition = resolve_award_transition(
            cycle.state, "record_approved_outcome", "spacs_convener"
        )
        cycle.state = transition.target
        cycle.approval_evidence = approval_evidence
    else:
        # Approval pending -> BW-SPACS-11
        transition = resolve_award_transition(cycle.state, "await_approval", "spacs_convener")
        cycle.state = transition.target

    cycle.save()

    log_action(
        event_type="award_outcome_recorded",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=convener_user_id,
        details={"state": cycle.state, "approval_evidence": approval_evidence},
    )
    return cycle


def record_institutional_approval_received(
    award_cycle_id: int,
    convener_user_id: int,
    approval_evidence: str,
) -> SpacsAwardCycle:
    """Record institutional approval when previously pending (BW-SPACS-11)."""
    cycle = SpacsAwardCycle.objects.get(id=award_cycle_id)
    transition = resolve_award_transition(
        cycle.state, "record_approval_received", "spacs_convener"
    )
    cycle.state = transition.target
    cycle.approval_evidence = approval_evidence
    cycle.save()

    log_action(
        event_type="institutional_approval_received",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=convener_user_id,
        details={"approval_evidence": approval_evidence},
    )
    return cycle


def publish_award_results(
    award_cycle_id: int,
    convener_user_id: int,
) -> SpacsAwardCycle:
    """Publish award results after approval confirmed (AFR-SPACS-046, BR-SPACS-019, BW-SPACS-09)."""
    cycle = SpacsAwardCycle.objects.get(id=award_cycle_id)
    validate_award_publication_allowed(cycle.state, cycle.approval_evidence)

    transition = resolve_award_transition(cycle.state, "publish_results", "spacs_convener")
    cycle.state = transition.target
    cycle.published_at = timezone.now()
    cycle.save()

    # Notify recommended winners
    winners = cycle.candidates.filter(committee_recommendation="winner")
    for w in winners:
        notify_user(
            recipient_user_id=w.student_user_id,
            event_type="award_published",
            title="Convocation Award Announced",
            message=f"Congratulations! You have been awarded the {cycle.catalogue_entry.name} for academic cycle {cycle.academic_cycle}.",
        )

    log_action(
        event_type="award_results_published",
        entity_type="award_cycle",
        entity_id=str(cycle.id),
        actor_user_id=convener_user_id,
        details={"winners_count": winners.count()},
    )
    return cycle
