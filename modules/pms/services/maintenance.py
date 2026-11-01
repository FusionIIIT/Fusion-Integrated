"""Post-grant patent tracking and maintenance fee renewal services (BW-PMS-14, 15, CW-PMS-04)."""

from __future__ import annotations

import datetime
import decimal

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.constants import (
    ACTOR_ATTORNEY,
    ACTOR_DIRECTOR,
    MAINTENANCE_DECISIONS,
    MAINTENANCE_RENEW,
    STATUS_DO_NOT_RENEW,
    STATUS_GRANTED,
    STATUS_RENEWAL_APPROVED,
    STATUS_RENEWAL_DECISION_REQUESTED,
    STATUS_RENEWED,
)
from modules.pms.domain.exceptions import ValidationError
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import (
    DeadlineTracking,
    MaintenanceSchedule,
    PatentApplication,
    PostGrantPatent,
    RenewalDecision,
)
from modules.pms.services.audit import record_audit_event


@transaction.atomic
def initialize_post_grant_patent(
    application: PatentApplication,
    patent_number: str,
    grant_date: datetime.date,
    attorney_user_id: int,
) -> PostGrantPatent:
    """Initialize post-grant tracking and 20-year maintenance schedule (BR-PMS-059)."""
    validate_transition(application.status, STATUS_GRANTED, ACTOR_ATTORNEY)

    prev_status = application.status
    application.status = STATUS_GRANTED
    application.save()

    expiry_date = grant_date.replace(year=grant_date.year + 20)
    pg = PostGrantPatent.objects.create(
        application=application,
        patent_number=patent_number.strip(),
        grant_date=grant_date,
        term_years=20,
        expiry_date=expiry_date,
        current_cycle=3,  # In India/PCT maintenance begins typically at year 3
    )

    # Generate annual maintenance schedules from year 3 to 20
    base_fee = decimal.Decimal("5000.00")
    for year in range(3, 21):
        due = grant_date.replace(year=grant_date.year + year)
        fee = base_fee + decimal.Decimal(str((year - 3) * 1000))
        MaintenanceSchedule.objects.create(
            post_grant=pg,
            cycle_year=year,
            due_date=due,
            fee_amount=fee,
            status="scheduled",
        )

    # Schedule first maintenance deadline
    first_due = grant_date.replace(year=grant_date.year + 3)
    due_datetime = timezone.make_aware(
        datetime.datetime.combine(first_due, datetime.time(23, 59, 59))
    )
    DeadlineTracking.objects.create(
        application=application,
        deadline_type="maintenance",
        due_date=due_datetime,
    )

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="grant_patent",
        previous_state=prev_status,
        new_state=STATUS_GRANTED,
        details={"patent_number": patent_number, "grant_date": str(grant_date)},
    )

    return pg


@transaction.atomic
def request_maintenance_renewal_decision(
    schedule: MaintenanceSchedule,
    attorney_user_id: int,
) -> MaintenanceSchedule:
    """Attorney initiates renewal decision request from Director (UC-PMS-017, BW-PMS-14, 15)."""
    application = schedule.post_grant.application
    prev_status = application.status

    validate_transition(application.status, STATUS_RENEWAL_DECISION_REQUESTED, ACTOR_ATTORNEY)
    application.status = STATUS_RENEWAL_DECISION_REQUESTED
    application.save()

    schedule.status = "decision_requested"
    schedule.save()

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="request_renewal_decision",
        previous_state=prev_status,
        new_state=STATUS_RENEWAL_DECISION_REQUESTED,
        details={"cycle_year": schedule.cycle_year, "due_date": str(schedule.due_date)},
    )

    return schedule


@transaction.atomic
def record_maintenance_renewal_decision(
    schedule: MaintenanceSchedule,
    director_user_id: int,
    decision: str,  # "renew" or "do_not_renew"
    justification: str = "",
) -> RenewalDecision:
    """Director renewal decision: Renew (BW-PMS-14) or Do Not Renew (BW-PMS-15, BR-PMS-061)."""
    if decision not in MAINTENANCE_DECISIONS:
        raise ValidationError(
            f"Decision must be one of: {', '.join(sorted(MAINTENANCE_DECISIONS))}.",
            rule_id="BR-PMS-061",
        )

    application = schedule.post_grant.application
    prev_status = application.status

    target_status = (
        STATUS_RENEWAL_APPROVED if decision == MAINTENANCE_RENEW else STATUS_DO_NOT_RENEW
    )
    validate_transition(application.status, target_status, ACTOR_DIRECTOR)

    application.status = target_status
    application.save()

    schedule.status = "renewal_approved" if decision == MAINTENANCE_RENEW else "do_not_renew"
    schedule.save()

    renewal_dec = RenewalDecision.objects.create(
        schedule=schedule,
        director_user_id=director_user_id,
        decision=decision,
        justification=justification.strip(),
    )

    record_audit_event(
        application=application,
        user_id=director_user_id,
        actor_role=ACTOR_DIRECTOR,
        action_type=f"renewal_{decision}",
        previous_state=prev_status,
        new_state=target_status,
        details={"justification": justification.strip()},
    )

    return renewal_dec


@transaction.atomic
def record_maintenance_payment(
    schedule: MaintenanceSchedule,
    attorney_user_id: int,
    payment_reference: str,
) -> MaintenanceSchedule:
    """Record payment transaction and schedule next cycle (UC-PMS-017, BW-PMS-14, BR-PMS-060)."""
    if schedule.status != "renewal_approved":
        msg = f"Maintenance action permitted only after renewal approval ({schedule.status!r})."
        raise ValidationError(msg)

    application = schedule.post_grant.application
    prev_status = application.status

    validate_transition(application.status, STATUS_RENEWED, ACTOR_ATTORNEY)
    application.status = STATUS_GRANTED  # returns to active granted post-grant state
    application.save()

    schedule.status = "renewed"
    schedule.payment_record_reference = payment_reference.strip()
    schedule.completed_at = timezone.now()
    schedule.save()

    # Advance post grant current cycle
    pg = schedule.post_grant
    pg.current_cycle = schedule.cycle_year + 1
    pg.save()

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="record_maintenance_payment",
        previous_state=prev_status,
        new_state=STATUS_GRANTED,
        details={
            "cycle_year": schedule.cycle_year,
            "payment_reference": payment_reference.strip(),
        },
    )

    return schedule
