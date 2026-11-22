"""Timeout escalation, its schedule, and the commands and contracts around it (IAA-BR-401)."""
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone

from config.celery import app
from core.api.exceptions import ConflictError
from modules.iaa import contracts, tasks
from modules.iaa.domain import roles
from modules.iaa.models import ApprovalStep, FinancialRecord, Notification, TrailEntry
from modules.iaa.services import configuration, decisions, observations, records, review
from modules.iaa.tests.helpers import POLICY, new_expense, new_ta

pytestmark = pytest.mark.django_db

LATE = timedelta(hours=49)          # the policy allows 48


def _held_by_hod(people, **kw):
    rec = new_expense(people.creator, **kw)
    review.validate(people.finance, rec.pk)
    return rec


def _steps(rec):
    return [(s.designation, s.status, s.via_escalation)
            for s in ApprovalStep.objects.filter(record=rec).order_by("id")]


def test_an_overdue_approval_is_escalated_to_the_next_authority(people, configured):
    rec = _held_by_hod(people)
    report = decisions.escalate_overdue(at=timezone.now() + LATE)
    assert (report.escalated, report.stuck) == (1, 0)

    rec.refresh_from_db()
    assert rec.status == "escalated" and rec.current_level == 1
    assert _steps(rec) == [(roles.HOD, "escalated", False), (roles.DEAN, "pending", True)]
    entry = TrailEntry.objects.get(entity="record", entity_id=rec.pk, action="escalate")
    assert entry.actor_user_id is None and entry.actor_role == "system"
    assert (entry.from_status, entry.to_status) == ("finance_validated", "escalated")
    assert Notification.objects.filter(recipient_role=roles.DEAN, kind="escalated").exists()
    assert Notification.objects.filter(recipient_user_id=101, kind="escalated").exists()


def test_the_new_authority_resolves_an_escalated_item_by_approval_or_rejection(
        people, configured):
    approve = _held_by_hod(people)
    reject = _held_by_hod(people)
    decisions.escalate_overdue(at=timezone.now() + LATE)
    assert decisions.decide(people.dean, approve.pk, decision="approve",
                            remarks="Handled").status == "approved"
    assert decisions.decide(people.dean, reject.pk, decision="reject",
                            remarks="No").status == "rejected"
    with pytest.raises(ConflictError):                            # the original HoD lost it
        decisions.decide(people.hod, approve.pk, decision="approve", remarks="late")


def test_an_item_inside_its_time_limit_is_not_escalated(people, configured):
    rec = _held_by_hod(people)
    report = decisions.escalate_overdue(at=timezone.now() + timedelta(hours=47))
    assert (report.escalated, report.stuck) == (0, 0)
    assert FinancialRecord.objects.get(pk=rec.pk).status == "finance_validated"


def test_the_limit_comes_from_the_policy_and_a_new_policy_changes_it(people, configured):
    rec = _held_by_hod(people)
    configuration.publish_policy(people.admin, {**POLICY, "approval_timeout_hours": 1})
    assert decisions.escalate_overdue(at=timezone.now() + timedelta(hours=2)).escalated == 1
    assert FinancialRecord.objects.get(pk=rec.pk).status == "escalated"


def test_running_the_sweep_twice_escalates_once(people, configured):
    _held_by_hod(people)
    at = timezone.now() + LATE
    assert decisions.escalate_overdue(at=at).escalated == 1
    assert decisions.escalate_overdue(at=at).escalated == 0
    assert decisions.escalate_overdue(at=at + LATE).escalated == 0     # no re-escalation


def test_an_item_with_no_escalation_authority_is_counted_as_stuck_and_left_alone(
        people, configured):
    configuration.publish_policy(people.admin, {
        **POLICY, "routes": [
            {"kind": "expense", "levels": [roles.HOD], "escalation_designation": ""},
            *[r for r in POLICY["routes"] if r["kind"] == "ta"]]})
    rec = _held_by_hod(people)
    report = decisions.escalate_overdue(at=timezone.now() + LATE)
    assert (report.escalated, report.stuck) == (0, 1)
    assert FinancialRecord.objects.get(pk=rec.pk).status == "finance_validated"


def test_the_second_level_of_a_two_level_route_escalates_to_the_director(people, configured):
    rec = new_expense(people.creator, amount="60000")
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="Level 1")
    ApprovalStep.objects.filter(record=rec, status="pending").update(
        assigned_at=timezone.now() - LATE)
    assert decisions.escalate_overdue().escalated == 1
    assert _steps(rec)[-1] == (roles.DIRECTOR, "pending", True)
    assert decisions.decide(people.director, rec.pk, decision="approve",
                            remarks="Done").status == "approved"


def test_a_high_value_ta_claim_escalates_but_a_verified_one_has_no_step_to_escalate(
        people, configured):
    high = new_ta(people.creator, amount="30000")
    review.validate(people.finance, high.pk)
    low = new_ta(people.creator, amount="100")
    review.validate(people.finance, low.pk)
    assert decisions.escalate_overdue(at=timezone.now() + LATE).escalated == 1
    assert FinancialRecord.objects.get(pk=high.pk).status == "escalated"
    assert FinancialRecord.objects.get(pk=low.pk).status == "verified"


def test_a_decision_that_lands_during_the_sweep_wins(people, configured):
    rec = _held_by_hod(people)
    cutoff = timezone.now() + LATE - timedelta(hours=48)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="In time")
    assert decisions._escalate_one(rec.pk, cutoff) == "skipped"
    assert FinancialRecord.objects.get(pk=rec.pk).status == "approved"
    other = _held_by_hod(people)
    assert decisions._escalate_one(other.pk, timezone.now() - timedelta(days=9)) == "skipped"


def test_nothing_is_escalated_without_a_policy(db):
    assert str(decisions.escalate_overdue()) == "escalated=0 stuck=0"


def test_the_beat_schedule_and_task_are_wired(people, configured):
    entry = app.conf.beat_schedule["iaa.escalate-overdue-approvals"]
    assert entry["task"] == "iaa.escalate_overdue_approvals" and entry["schedule"] == 600.0
    assert entry["options"]["expires"] < entry["schedule"]
    assert tasks.escalate_overdue_approvals.name == "iaa.escalate_overdue_approvals"
    assert tasks.escalate_overdue_approvals.acks_late is True
    assert tasks.escalate_overdue_approvals() == "escalated=0 stuck=0"


def test_the_task_and_the_command_do_the_same_work(people, configured):
    _held_by_hod(people)
    ApprovalStep.objects.update(assigned_at=timezone.now() - LATE)
    out = StringIO()
    call_command("iaa_escalate_overdue", stdout=out)
    assert "escalated=1 stuck=0" in out.getvalue()
    assert tasks.escalate_overdue_approvals() == "escalated=0 stuck=0"        # idempotent


def test_the_readiness_command_names_what_is_missing_then_reports_ready(people):
    out = StringIO()
    call_command("iaa_readiness", stdout=out)
    text = out.getvalue()
    assert "No policy is in effect" in text and "No financial year covers today" in text

    today = timezone.localdate()
    year = configuration.add_financial_year(people.admin, code="Y", starts_on=today,
                                            ends_on=today + timedelta(days=30))
    configuration.publish_policy(people.admin, POLICY)
    out = StringIO()
    call_command("iaa_readiness", stdout=out)
    assert "No budget is entered for Y" in out.getvalue()

    configuration.add_budget_entry(people.admin, financial_year_id=year.pk, department="CSE",
                                   kind="allocation", amount=1)
    out = StringIO()
    call_command("iaa_readiness", stdout=out)
    assert "IAA is ready." in out.getvalue()


def test_the_contract_counts_open_items_per_user_and_ignores_finished_ones(
        people, configured):
    new_expense(people.creator)
    finished = _held_by_hod(people)
    decisions.decide(people.hod, finished.pk, decision="reject", remarks="No")
    observations.raise_observation(people.auditor, title="t", detail="d",
                                   respondent_user_id=101)
    counts = contracts.get_open_item_counts([101, 102, None])
    assert (counts[101].open_records, counts[101].open_observations) == (1, 1)
    assert (counts[102].open_records, counts[102].open_observations) == (0, 0)
    assert contracts.get_open_item_counts([]) == {}


def test_a_financial_year_starting_today_in_india_covers_the_small_hours(people):
    # 00:30 on 1 April in Kolkata is still 31 March in UTC; the institute's "today" is the local one.
    configuration.add_financial_year(people.admin, code="FY", starts_on=date(2026, 4, 1),
                                     ends_on=date(2027, 3, 31))
    small_hours = datetime(2026, 3, 31, 19, 0, tzinfo=UTC)
    out = StringIO()
    record = FinancialRecord()
    with mock.patch("django.utils.timezone.now", return_value=small_hours):
        call_command("iaa_readiness", stdout=out)
        records._attach_financial_year(record)
    assert "No financial year covers today" not in out.getvalue()
    assert record.financial_year.code == "FY"
