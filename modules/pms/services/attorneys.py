"""Attorney panel assignments, patentability opinions and legal advice (BW-PMS-06, 07)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.constants import (
    ACTOR_ATTORNEY,
    ACTOR_PCC_ADMIN,
    ATTORNEY_RECOMMENDATIONS,
    ATTORNEY_STATUS_ACCEPTED,
    ATTORNEY_STATUS_DECLINED,
    ATTORNEY_STATUS_OFFERED,
    STATUS_APPROVED,
    STATUS_ASSIGNMENT_OFFERED,
    STATUS_ATTORNEY_ASSIGNED,
    STATUS_BUDGET_APPROVED,
)
from modules.pms.domain.exceptions import ConflictOfInterestError, ValidationError
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import (
    AttorneyAssignment,
    AttorneyPanel,
    PatentabilityAssessment,
    PatentApplication,
    PatentLegalAdvice,
)
from modules.pms.services.audit import record_audit_event


@transaction.atomic
def assign_attorney_to_application(
    application: PatentApplication,
    attorney_user_id: int,
    assigned_by_user_id: int,
) -> AttorneyAssignment:
    """Assign an Attorney from approved panel to an Approved application (UC-PMS-010, BW-PMS-06)."""
    # 1. Attorney assignment must not occur before Director approval (BR-PMS-127)
    if application.status not in (STATUS_APPROVED, STATUS_BUDGET_APPROVED):
        msg = f"Cannot assign attorney: Status is {application.status!r}, must be 'approved'."
        raise ValidationError(msg, rule_id="BR-PMS-127")

    # 2. Must be selected from approved panel (BR-PMS-041)
    panel_entry = AttorneyPanel.objects.filter(user_id=attorney_user_id, is_active=True).first()
    if not panel_entry:
        raise ValidationError(
            f"User {attorney_user_id} is not in the approved active attorney panel.",
            rule_id="BR-PMS-041",
        )

    # 3. Workload check (BR-PMS-043)
    if panel_entry.current_workload >= panel_entry.max_workload:
        msg = f"Attorney {panel_entry.name} reached maximum workload ({panel_entry.max_workload})."
        raise ValidationError(msg, rule_id="BR-PMS-043")

    # 4. Conflict of interest check (BR-PMS-044)
    inventor_ids = list(application.inventors.values_list("user_id", flat=True))
    if attorney_user_id in inventor_ids or attorney_user_id == application.user_id:
        raise ConflictOfInterestError(
            f"Conflict of interest: Attorney {attorney_user_id} is an inventor or applicant.",
            rule_id="BR-PMS-044",
        )

    # 5. Transition to assignment_offered
    validate_transition(application.status, STATUS_ASSIGNMENT_OFFERED, ACTOR_PCC_ADMIN)
    prev_status = application.status
    application.status = STATUS_ASSIGNMENT_OFFERED
    application.save()

    # 6. Create AttorneyAssignment
    assignment = AttorneyAssignment.objects.create(
        application=application,
        attorney_user_id=attorney_user_id,
        assigned_by_user_id=assigned_by_user_id,
        status=ATTORNEY_STATUS_OFFERED,
    )

    record_audit_event(
        application=application,
        user_id=assigned_by_user_id,
        actor_role=ACTOR_PCC_ADMIN,
        action_type="assign_attorney",
        previous_state=prev_status,
        new_state=STATUS_ASSIGNMENT_OFFERED,
        details={"attorney_user_id": attorney_user_id, "panel_firm": panel_entry.firm_name},
    )

    return assignment


@transaction.atomic
def respond_to_attorney_assignment(
    assignment: AttorneyAssignment,
    attorney_user_id: int,
    accept: bool,
    remarks: str = "",
) -> AttorneyAssignment:
    """Attorney accepts or declines assignment (UC-PMS-011, BW-PMS-06, 07)."""
    if assignment.attorney_user_id != attorney_user_id:
        raise ValidationError("Only the assigned attorney can accept or decline this assignment.")

    if assignment.status != ATTORNEY_STATUS_OFFERED:
        raise ValidationError(f"Assignment is in status {assignment.status!r}, not 'offered'.")

    application = assignment.application
    prev_status = application.status

    if accept:
        validate_transition(application.status, STATUS_ATTORNEY_ASSIGNED, ACTOR_ATTORNEY)
        assignment.status = ATTORNEY_STATUS_ACCEPTED
        assignment.responded_at = timezone.now()
        assignment.remarks = remarks.strip()
        assignment.save()

        application.status = STATUS_ATTORNEY_ASSIGNED
        application.save()

        # Increment attorney workload
        AttorneyPanel.objects.filter(user_id=attorney_user_id).update(
            current_workload=models_f_increment()
        )

        record_audit_event(
            application=application,
            user_id=attorney_user_id,
            actor_role=ACTOR_ATTORNEY,
            action_type="accept_attorney_assignment",
            previous_state=prev_status,
            new_state=STATUS_ATTORNEY_ASSIGNED,
            details={"remarks": remarks},
        )
    else:
        # Decline: application returns to approved status for reassignment (BW-PMS-07)
        validate_transition(application.status, STATUS_APPROVED, ACTOR_ATTORNEY)
        assignment.status = ATTORNEY_STATUS_DECLINED
        assignment.responded_at = timezone.now()
        assignment.remarks = remarks.strip()
        assignment.save()

        application.status = STATUS_APPROVED
        application.save()

        record_audit_event(
            application=application,
            user_id=attorney_user_id,
            actor_role=ACTOR_ATTORNEY,
            action_type="decline_attorney_assignment",
            previous_state=prev_status,
            new_state=STATUS_APPROVED,
            details={"remarks": remarks},
        )

    return assignment


def models_f_increment():
    from django.db.models import F

    return F("current_workload") + 1


@transaction.atomic
def record_patentability_assessment(
    application: PatentApplication,
    attorney_user_id: int,
    recommendation: str,
    novelty_analysis: str,
    inventive_step_analysis: str,
    utility_analysis: str,
    prior_art_summary: str,
    opinion_text: str,
) -> PatentabilityAssessment:
    """Record attorney legal analysis and patentability opinion (UC-PMS-012, BR-PMS-046)."""
    if recommendation not in ATTORNEY_RECOMMENDATIONS:
        raise ValidationError(
            f"Recommendation must be one of: {', '.join(sorted(ATTORNEY_RECOMMENDATIONS))}.",
            rule_id="BR-PMS-046",
        )

    assessment = PatentabilityAssessment.objects.create(
        application=application,
        attorney_user_id=attorney_user_id,
        recommendation=recommendation,
        novelty_analysis=novelty_analysis.strip(),
        inventive_step_analysis=inventive_step_analysis.strip(),
        utility_analysis=utility_analysis.strip(),
        prior_art_summary=prior_art_summary.strip(),
        opinion_text=opinion_text.strip(),
    )

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="patentability_assessment",
        previous_state=application.status,
        new_state=application.status,
        details={"recommendation": recommendation},
    )

    return assessment


@transaction.atomic
def record_patent_legal_advice(
    application: PatentApplication,
    attorney_user_id: int,
    topic: str,
    advice_text: str,
) -> PatentLegalAdvice:
    """Record legal counsel advice during prosecution (UC-PMS-033, CFR-PMS-004)."""
    advice = PatentLegalAdvice.objects.create(
        application=application,
        attorney_user_id=attorney_user_id,
        topic=topic.strip(),
        advice_text=advice_text.strip(),
    )

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="record_legal_advice",
        details={"topic": topic.strip()},
    )

    return advice
