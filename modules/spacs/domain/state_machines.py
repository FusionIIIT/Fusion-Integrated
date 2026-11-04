"""Pure Python state machines for SPACS.

Enforces:
- CW-SPACS-01 (Scholarship Application Lifecycle)
- CW-SPACS-02 (Scholarship Renewal Lifecycle)
- CW-SPACS-03 (Convocation Award Lifecycle)
- BR-SPACS-006 (Assistant verification is not final sanction)
- BR-SPACS-009 (Withdrawal before final decision)
- BR-SPACS-010 (Owner-only modification and withdrawal)
- BR-SPACS-011 (Correction and revalidation)
- BR-SPACS-018 (Scholarship decision authority)
- BR-SPACS-019 (Award evaluation & approval follow award policy)
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Scholarship Lifecycle States (CW-SPACS-01 & CW-SPACS-02) ---
APP_STATUS_DRAFT = "draft"
APP_STATUS_SUBMITTED = "submitted"
APP_STATUS_UNDER_VERIFICATION = "under_verification"
APP_STATUS_CORRECTION_REQUIRED = "correction_required"
APP_STATUS_RESUBMITTED = "resubmitted"
APP_STATUS_VERIFIED_ROUTED = "verified_routed"
APP_STATUS_VERIFICATION_CONCERN = "verification_concern"
APP_STATUS_UNDER_CONVENER_REVIEW = "under_convener_review"
APP_STATUS_APPROVED = "approved"
APP_STATUS_REJECTED = "rejected"
APP_STATUS_WITHDRAWN = "withdrawn"

APPLICATION_STATUSES = (
    (APP_STATUS_DRAFT, "Draft"),
    (APP_STATUS_SUBMITTED, "Submitted"),
    (APP_STATUS_UNDER_VERIFICATION, "Under Verification"),
    (APP_STATUS_CORRECTION_REQUIRED, "Correction Required"),
    (APP_STATUS_RESUBMITTED, "Resubmitted"),
    (APP_STATUS_VERIFIED_ROUTED, "Verified / Routed for Decision"),
    (APP_STATUS_VERIFICATION_CONCERN, "Verification Concern / Routed"),
    (APP_STATUS_UNDER_CONVENER_REVIEW, "Under Convener Review"),
    (APP_STATUS_APPROVED, "Approved"),
    (APP_STATUS_REJECTED, "Rejected"),
    (APP_STATUS_WITHDRAWN, "Withdrawn"),
)

FINAL_APPLICATION_STATUSES = frozenset({
    APP_STATUS_APPROVED,
    APP_STATUS_REJECTED,
    APP_STATUS_WITHDRAWN,
})

# States where an application is actively in flight (BR-SPACS-002 duplicate check)
ACTIVE_APPLICATION_STATUSES = frozenset({
    APP_STATUS_SUBMITTED,
    APP_STATUS_UNDER_VERIFICATION,
    APP_STATUS_CORRECTION_REQUIRED,
    APP_STATUS_RESUBMITTED,
    APP_STATUS_VERIFIED_ROUTED,
    APP_STATUS_VERIFICATION_CONCERN,
    APP_STATUS_UNDER_CONVENER_REVIEW,
})

# States where a student is permitted to edit data/evidence (BR-SPACS-010)
EDITABLE_APPLICATION_STATUSES = frozenset({
    APP_STATUS_DRAFT,
    APP_STATUS_CORRECTION_REQUIRED,
})

# States where withdrawal is permissible before final decision (BR-SPACS-009, BW-SPACS-05)
WITHDRAWABLE_APPLICATION_STATUSES = frozenset({
    APP_STATUS_SUBMITTED,
    APP_STATUS_UNDER_VERIFICATION,
    APP_STATUS_CORRECTION_REQUIRED,
    APP_STATUS_RESUBMITTED,
    APP_STATUS_VERIFIED_ROUTED,
})


# --- Convocation Award Lifecycle States (CW-SPACS-03) ---
AWARD_STATUS_OPEN = "open"
AWARD_STATUS_POOL_PREPARED = "pool_prepared"
AWARD_STATUS_UNDER_EVALUATION = "under_committee_evaluation"
AWARD_STATUS_RESULT_RECORDED = "committee_result_recorded"
AWARD_STATUS_AWAITING_APPROVAL = "awaiting_approval"
AWARD_STATUS_READY_PUBLICATION = "ready_for_publication"
AWARD_STATUS_PUBLISHED = "published"

AWARD_CYCLE_STATUSES = (
    (AWARD_STATUS_OPEN, "Award Cycle Open"),
    (AWARD_STATUS_POOL_PREPARED, "Candidate Pool Prepared"),
    (AWARD_STATUS_UNDER_EVALUATION, "Under Committee Evaluation"),
    (AWARD_STATUS_RESULT_RECORDED, "Committee Result Recorded"),
    (AWARD_STATUS_AWAITING_APPROVAL, "Awaiting Institutional Approval"),
    (AWARD_STATUS_READY_PUBLICATION, "Ready for Publication"),
    (AWARD_STATUS_PUBLISHED, "Published"),
)


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    reason: str = ""


def can_transition_application(
    from_status: str,
    to_status: str,
    actor_role: str,
    is_owner: bool = False,
    is_locked_by_policy: bool = False,
) -> TransitionResult:
    """Enforces authoritative state transitions for CW-SPACS-01 and CW-SPACS-02."""
    if from_status in FINAL_APPLICATION_STATUSES:
        return TransitionResult(False, f"Cannot transition from final status '{from_status}'.")

    # 1. Student Submission from Draft
    if from_status == APP_STATUS_DRAFT and to_status == APP_STATUS_SUBMITTED:
        if not is_owner:
            return TransitionResult(False, "Only the applicant can submit their draft.")
        return TransitionResult(True)

    # 2. Assistant Verification Transitions
    if actor_role in ("spacs_assistant", "spacs_convener"):
        if from_status in (APP_STATUS_SUBMITTED, APP_STATUS_RESUBMITTED):
            if to_status == APP_STATUS_UNDER_VERIFICATION:
                return TransitionResult(True)

        if from_status == APP_STATUS_UNDER_VERIFICATION:
            if to_status == APP_STATUS_CORRECTION_REQUIRED:
                return TransitionResult(True)
            if to_status == APP_STATUS_VERIFIED_ROUTED:
                return TransitionResult(True)
            if to_status == APP_STATUS_VERIFICATION_CONCERN:
                return TransitionResult(True)

    # 3. Student Resubmission after Correction
    if from_status == APP_STATUS_CORRECTION_REQUIRED and to_status == APP_STATUS_RESUBMITTED:
        if not is_owner:
            return TransitionResult(False, "Only the owning student may resubmit after correction.")
        return TransitionResult(True)

    # 4. Convener Decision Opening
    if actor_role == "spacs_convener":
        if from_status in (APP_STATUS_VERIFIED_ROUTED, APP_STATUS_VERIFICATION_CONCERN):
            if to_status == APP_STATUS_UNDER_CONVENER_REVIEW:
                return TransitionResult(True)

        if from_status == APP_STATUS_UNDER_CONVENER_REVIEW:
            if to_status == APP_STATUS_APPROVED:
                return TransitionResult(True)
            if to_status == APP_STATUS_REJECTED:
                return TransitionResult(True)
            if to_status == APP_STATUS_CORRECTION_REQUIRED:
                return TransitionResult(True)

    # 5. Withdrawal (BW-SPACS-05, BR-SPACS-009, BR-SPACS-010)
    if to_status == APP_STATUS_WITHDRAWN:
        if not is_owner:
            return TransitionResult(False, "Only the owning student may withdraw an application.")
        if from_status not in WITHDRAWABLE_APPLICATION_STATUSES:
            return TransitionResult(False, f"Application in '{from_status}' cannot be withdrawn.")
        if is_locked_by_policy:
            return TransitionResult(False, "Withdrawal is locked by active scheme policy.")
        return TransitionResult(True)

    return TransitionResult(False, f"Invalid transition from '{from_status}' to '{to_status}' by role '{actor_role}'.")


def can_transition_award_cycle(
    from_status: str,
    to_status: str,
    actor_role: str,
    approval_evidence_available: bool = False,
) -> TransitionResult:
    """Enforces authoritative state transitions for CW-SPACS-03."""
    # Convener prepares candidate pool
    if from_status == AWARD_STATUS_OPEN and to_status == AWARD_STATUS_POOL_PREPARED:
        if actor_role != "spacs_convener":
            return TransitionResult(False, "Only the SPACS Convener may prepare the candidate pool.")
        return TransitionResult(True)

    # Committee starts evaluation
    if from_status == AWARD_STATUS_POOL_PREPARED and to_status == AWARD_STATUS_UNDER_EVALUATION:
        if actor_role not in ("award_eval_committee", "spacs_convener"):
            return TransitionResult(False, "Only an authorized committee member or Convener may begin evaluation.")
        return TransitionResult(True)

    # Committee records results
    if from_status == AWARD_STATUS_UNDER_EVALUATION and to_status == AWARD_STATUS_RESULT_RECORDED:
        if actor_role not in ("award_eval_committee", "spacs_convener"):
            return TransitionResult(False, "Only an authorized committee member or Convener may record committee results.")
        return TransitionResult(True)

    # Outcome finalization with approval available (BW-SPACS-09)
    if from_status == AWARD_STATUS_RESULT_RECORDED and to_status == AWARD_STATUS_READY_PUBLICATION:
        if actor_role != "spacs_convener":
            return TransitionResult(False, "Only the Convener may record final award approval.")
        if not approval_evidence_available:
            return TransitionResult(False, "Required approval evidence is not yet available.")
        return TransitionResult(True)

    # Outcome finalization with approval pending (BW-SPACS-11)
    if from_status == AWARD_STATUS_RESULT_RECORDED and to_status == AWARD_STATUS_AWAITING_APPROVAL:
        if actor_role != "spacs_convener":
            return TransitionResult(False, "Only the Convener may set cycle to awaiting approval.")
        return TransitionResult(True)

    # Approval recorded from pending
    if from_status == AWARD_STATUS_AWAITING_APPROVAL and to_status == AWARD_STATUS_READY_PUBLICATION:
        if actor_role != "spacs_convener":
            return TransitionResult(False, "Only the Convener may record approval evidence.")
        if not approval_evidence_available:
            return TransitionResult(False, "Required approval evidence is missing.")
        return TransitionResult(True)

    # Official result publication (AFR-SPACS-046)
    if from_status == AWARD_STATUS_READY_PUBLICATION and to_status == AWARD_STATUS_PUBLISHED:
        if actor_role != "spacs_convener":
            return TransitionResult(False, "Only the Convener may publish award results.")
        return TransitionResult(True)

    return TransitionResult(False, f"Invalid award cycle transition from '{from_status}' to '{to_status}'.")
