"""M1: policy and configuration (DEC-7, DEC-8, DEC-9).

Proves the mechanism end to end: only specification-stated values are seeded,
unset values stay unset, deadlines and maintenance follow policy, and nothing
is fabricated when an operator has configured nothing.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from modules.pms.domain.errors import PolicyConfigurationError
from modules.pms.domain.policies import SPECIFIED_DEFAULTS, PmsPolicy
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import PmsNotificationOutbox
from modules.pms.services import (
    add_business_days,
    assign_director,
    calculate_review_deadline,
    calculate_revision_deadline,
    configured_keys,
    decide_budget,
    decide_renewal,
    load_policy,
    monitor_and_process_deadlines,
    record_maintenance_action,
    record_patent_grant,
    request_renewal_decision,
    set_policy_value,
    submit_application,
    submit_director_review,
    submit_or_update_budget,
    unset_policy_value,
)
from modules.pms.tests.support import configure, configure_maintenance_schedule

pytestmark = pytest.mark.django_db


def _approved_application(user_id: int = 1001):
    app = submit_application(
        applicant_user_id=user_id,
        title="Policy",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Novelty and industrial application are adequately demonstrated.",
    )
    app.refresh_from_db()
    return app


def _filed_application(user_id: int = 1001):
    app = submit_application(
        applicant_user_id=user_id,
        title="Granted",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.assigned_director_user_id = 2001
    app.save()
    return app


# --------------------------------------------------------------- seeding


def test_only_specification_stated_values_are_seeded():
    """PS 2.4 / DEC-7: seed the three stated values, invent nothing else."""
    policy = load_policy()
    assert policy.review_business_days == 15
    assert policy.revision_days == 60
    assert policy.alert_offsets == (30, 15, 5)

    assert policy.budget_threshold is None
    assert policy.appeal_period_days is None
    assert policy.escalation_chain is None
    assert policy.maintenance_schedule is None
    assert configured_keys() == sorted(SPECIFIED_DEFAULTS)


def test_unknown_key_is_rejected():
    with pytest.raises(PolicyConfigurationError):
        PmsPolicy.from_mapping({"not_a_policy": 1})
    with pytest.raises(PolicyConfigurationError):
        set_policy_value("not_a_policy", 1)


def test_invalid_value_is_rejected_and_not_stored():
    with pytest.raises(PolicyConfigurationError):
        set_policy_value("revision_days", 0)
    with pytest.raises(PolicyConfigurationError):
        set_policy_value("alert_offsets", [])
    assert load_policy().revision_days == 60
    assert set_policy_value("revision_days", 45) is not None
    assert load_policy().revision_days == 45
    unset_policy_value("revision_days")
    assert load_policy().revision_days == 60


# --------------------------------------------------------------- deadlines


def _next_business_day(day: datetime.date) -> datetime.date:
    nxt = day + datetime.timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += datetime.timedelta(days=1)
    return nxt


def test_holiday_calendar_is_optional_and_pushes_the_deadline():
    """DEC-9: Mon-Fri by default; a configured holiday pushes the window."""
    start = datetime.datetime(2026, 11, 13, 10, 0)
    plain = add_business_days(start, 15)
    assert plain > start

    holiday = plain.date() - datetime.timedelta(days=1)
    while holiday.weekday() >= 5:
        holiday -= datetime.timedelta(days=1)
    configure(holiday_calendar=[holiday.isoformat()])

    shifted = calculate_review_deadline(start)
    assert shifted.date() == _next_business_day(plain.date())


def test_review_deadline_follows_the_configured_business_days():
    start = datetime.datetime(2026, 11, 13, 10, 0)
    assert calculate_review_deadline(start).date() == add_business_days(start, 15).date()

    configure(review_business_days=5)
    assert calculate_review_deadline(start).date() == add_business_days(start, 5).date()


def test_revision_deadline_follows_the_configured_days():
    decided = datetime.datetime(2026, 11, 13, 10, 0)
    assert calculate_revision_deadline(decided) == decided + datetime.timedelta(days=60)

    configure(revision_days=30)
    assert calculate_revision_deadline(decided) == decided + datetime.timedelta(days=30)


def test_alert_offsets_come_from_configuration():
    configure(alert_offsets=[10])
    app = _filed_application()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.review_deadline = datetime.datetime.now() + datetime.timedelta(days=10)
    app.save()

    monitor_and_process_deadlines()
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert_10").exists()


def test_missed_review_deadline_escalates_without_changing_status():
    """DEC-9: a missed deadline escalates; it never moves the application."""
    app = submit_application(
        applicant_user_id=1001,
        title="Overdue review",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    app.refresh_from_db()
    app.review_deadline = datetime.datetime.now() - datetime.timedelta(days=1)
    app.save()

    monitor_and_process_deadlines()

    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.UNDER_REVIEW.value
    assert PmsNotificationOutbox.objects.filter(topic="deadline.escalated").exists()


# ------------------------------------------------------------- maintenance


def test_grant_without_a_schedule_reports_and_creates_no_cycle():
    """DEC-8 / BR-PMS-060: no configured schedule means no fabricated cycle."""
    app = _filed_application()
    record_patent_grant(
        application_id=app.id,
        attorney_user_id=5001,
        patent_number="IN-0001",
        grant_date=datetime.date(2026, 11, 1),
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.GRANTED.value
    assert app.maintenance_records.count() == 0

    audit = app.audit_logs.filter(action_type="patent_granted").first()
    assert audit.details["first_maintenance_due"] == "schedule not configured"


def test_grant_with_a_schedule_uses_the_configured_amounts():
    configure_maintenance_schedule()
    app = _filed_application()
    grant_date = datetime.date(2026, 11, 1)
    record_patent_grant(
        application_id=app.id,
        attorney_user_id=5001,
        patent_number="IN-0002",
        grant_date=grant_date,
    )
    cycle = app.maintenance_records.get(cycle_number=1)
    assert cycle.fee_amount == Decimal("5000.00")
    assert cycle.fee_due_date == grant_date + datetime.timedelta(days=1095)

    request_renewal_decision(maintenance_id=cycle.id, attorney_user_id=5001)
    decide_renewal(maintenance_id=cycle.id, director_user_id=2001, decision="Renew")
    record_maintenance_action(
        maintenance_id=cycle.id, attorney_user_id=5001, transaction_reference="TXN-1"
    )

    next_cycle = app.maintenance_records.get(cycle_number=2)
    assert next_cycle.fee_amount == Decimal("6000.00")
    assert next_cycle.fee_due_date == grant_date + datetime.timedelta(days=1460)


# ------------------------------------------------------------------ budget


def test_budget_without_a_configured_threshold_does_not_escalate():
    """DEC-7: with no threshold configured there is nothing to compare."""
    app = _approved_application()
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("50000.00"),
        attorney_fees=Decimal("80000.00"),
        administrative_costs=Decimal("20000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app.id, director_user_id=3001, decision="Approve"
    )
    assert budget.status == "approved"
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value
    assert app.budget.status == "approved"

    audit = app.audit_logs.filter(action_type="budget_approved").first()
    assert audit.details["threshold"] == "not configured"


def test_budget_with_a_configured_threshold_escalates():
    configure(budget_threshold="100000.00")
    app = _approved_application()
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("50000.00"),
        attorney_fees=Decimal("80000.00"),
        administrative_costs=Decimal("20000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app.id, director_user_id=3001, decision="Approve"
    )
    assert budget.status == "escalated"
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value
