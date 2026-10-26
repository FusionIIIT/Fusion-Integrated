"""Year-end, annual credit, SLA thresholds and notification delivery — each run as beat would run it."""
from decimal import Decimal as D

import pytest
from django.core import mail
from freezegun import freeze_time

from config.celery import app
from fusion_auth.client import IamUnavailable
from modules.leave.models import LeaveRequest, LedgerEntry, Outbox, SlaEvent, Task, YearEndRun
from modules.leave.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.leave.services import configuration, notifications, sla, yearend
from modules.leave.tests.conftest import FACULTY_CSE, HOD_CSE, HRADMIN, STAFF_RO, apply_payload

pytestmark = pytest.mark.django_db


def test_every_leave_beat_entry_is_merged_and_registered():
    app.loader.import_default_modules()
    for name, entry in BEAT_SCHEDULE.items():
        assert app.conf.beat_schedule[name] == entry
        assert entry["task"] in app.tasks, entry["task"]
        assert entry["options"]["expires"] > 0
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "leave.deliver_notifications", "leave.process_sla", "leave.year_boundary"}
    assert all(r["queue"] in {"default", "notifications", "reports", "ingest"}
               for r in TASK_ROUTES.values())


def _balances(uid, year):
    out = {}
    for e in LedgerEntry.objects.filter(user_id=uid, leave_year=year):
        out[e.category] = out.get(e.category, D(0)) + e.delta
    return out


def test_year_end_closes_converts_and_carries(configured):
    yearend.credit_year(2026)
    yearend.credit_year(2026)
    fac = _balances(FACULTY_CSE, 2026)
    assert fac == {"CL": D(8), "RH": D(2), "SCL": D(15), "COL": D(20), "VL": D(60)}
    run = yearend.run(2026)
    assert run.status == "completed"
    assert all(v == 0 for v in _balances(FACULTY_CSE, 2026).values())
    nxt = _balances(FACULTY_CSE, 2027)
    assert nxt == {"COL": D(20), "EL": D(30)}
    staff = _balances(STAFF_RO, 2027)
    assert staff == {"COL": D(20), "EL": D(30)}
    again = yearend.run(2026)
    assert again.pk == run.pk and _balances(FACULTY_CSE, 2027) == nxt


def test_year_end_reports_an_account_with_requests_in_flight(configured, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    yearend.credit_year(2026)
    run = yearend.run(2026)
    assert run.status == "completed_with_exceptions"
    assert [e["user_id"] for e in run.exceptions] == [FACULTY_CSE]
    assert _balances(FACULTY_CSE, 2026)["CL"] == D(8)
    LeaveRequest.objects.filter(user_id=FACULTY_CSE).update(status="withdrawn")
    assert yearend.run(2026).status == "completed"
    assert YearEndRun.objects.count() == 1


def test_year_boundary_task_runs_both_halves(configured):
    from modules.leave.tasks import year_boundary

    with freeze_time("2027-01-01 00:30:00+05:30"):
        out = year_boundary()
    assert "closed=2026:completed" in out
    assert _balances(FACULTY_CSE, 2027)["CL"] == D(8)


@pytest.fixture
def sla_rules(configured, actor):
    configuration.save_sla(actor=actor(HRADMIN), rules=[
        {"step": "unit_head", "reminder_hours": 24, "escalation_hours": 72,
         "action": "reassign", "escalate_to": "Director"}])


def test_sla_reminds_then_escalates_only_while_pending(sla_rules, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    task = Task.objects.get(status="open")
    with freeze_time("2026-03-02 09:00:00+05:30"):
        assert str(sla.process()) == "reminded=0 escalated=0 reassigned=0"
    with freeze_time("2026-03-03 11:00:00+05:30"):
        assert sla.process().reminded == 1
        assert sla.process().reminded == 0
    with freeze_time("2026-03-05 11:00:00+05:30"):
        report = sla.process()
    assert (report.escalated, report.reassigned) == (1, 1)
    task.refresh_from_db()
    assert task.assignee_designation == "Director" and task.status == "open"
    assert set(SlaEvent.objects.values_list("kind", flat=True)) == {"remind", "escalate"}
    assert not client_for(HOD_CSE).get("/api/v1/leave/queue").json()


def test_sla_issues_nothing_for_a_decided_task(sla_rules, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    hod = client_for(HOD_CSE)
    [t] = hod.get("/api/v1/leave/queue").json()
    hod.post(f"/api/v1/leave/tasks/{t['id']}/decide", {"action": "approve"}, format="json")
    with freeze_time("2026-03-10 11:00:00+05:30"):
        report = sla.process()
    assert (report.reminded, report.escalated) == (0, 0)
    assert not SlaEvent.objects.exists()


def test_delivery_expands_a_designation_to_its_holders(configured, client_for, stub_iam):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    report = notifications.deliver_pending()
    assert report.sent >= 1
    assigned = Outbox.objects.get(topic="task.assigned")
    assert assigned.status == "sent"
    assert any(f"u{HOD_CSE}@iiitdmj.test" in m.to for m in mail.outbox)
    assert notifications.deliver_pending().sent == 0


def test_delivery_defers_when_the_iam_cannot_answer(configured, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    from fusion_auth import client as iam

    iam.get_client().holders_error = IamUnavailable("down")
    report = notifications.deliver_pending()
    assert report.deferred >= 1
    assert Outbox.objects.get(topic="task.assigned").status == "pending"


def test_an_unheld_post_is_marked_undeliverable(configured, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(), format="json")
    from fusion_auth import client as iam

    iam.get_client().holders = {}
    notifications.deliver_pending()
    assert Outbox.objects.get(topic="task.assigned").status == "undeliverable"


def test_reminder_dedupes(configured):
    assert notifications.enqueue(topic="sla.reminder", dedupe_key="k", subject="s", body="b",
                                 user_id=1) is not None
    assert notifications.enqueue(topic="sla.reminder", dedupe_key="k", subject="s", body="b",
                                 user_id=1) is None
    with pytest.raises(ValueError):
        notifications.enqueue(topic="nope", dedupe_key="z", subject="s", body="b", user_id=1)


def test_manual_run_commands(configured):
    from io import StringIO

    from django.core.management import call_command

    for job in ("notifications", "sla", "credit"):
        out = StringIO()
        call_command("leave_run", job, stdout=out)
        assert out.getvalue()
    out = StringIO()
    call_command("leave_run", "year-end", "--year", "2025", stdout=out)
    assert "2025" in out.getvalue()
    out = StringIO()
    call_command("leave_readiness", stdout=out)
    assert "ready" in out.getvalue()
