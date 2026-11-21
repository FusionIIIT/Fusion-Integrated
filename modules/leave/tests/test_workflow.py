"""End to end through the API, one basis workflow per test where it matters."""
from datetime import date

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.leave.models import LeaveNotification, LeaveRequest, LedgerEntry, SlaPolicy
from modules.leave.selectors.accounts import balances
from modules.leave.services import periodic
from modules.leave.tests.conftest import (
    ADMIN,
    DEAN_HEAD,
    DIRECTOR,
    EST,
    HEAD,
    OTHER,
    SANCTION,
    STAFF,
    SUB,
)

pytestmark = pytest.mark.django_db


def apply(client, **over):
    body = {"category": "CL", "start_date": "2027-02-01", "end_date": "2027-02-02",
            "purpose": "Family function", **over}
    return client.post("/api/v1/leave/requests/apply", body, format="json")


def act(client, pk, action, **body):
    return client.post(f"/api/v1/leave/requests/{pk}/{action}", body, format="json")


def test_plain_cl_is_decided_by_the_unit_head_and_debited(world, as_user):
    r = apply(as_user(STAFF))
    assert r.status_code == 201, r.json()
    assert r.json()["status"] == "awaiting_unit_head"
    assert r.json()["unit_head_user_id"] == HEAD
    pk = r.json()["id"]
    assert LeaveNotification.objects.filter(user_id=HEAD, kind="assigned").exists()
    r = act(as_user(HEAD), pk, "review", decision="approve")
    assert r.json()["status"] == "approved"
    assert balances(STAFF, 2027)["CL"] == 6
    assert LeaveNotification.objects.filter(user_id=STAFF, kind="decision").exists()


def test_el_with_declined_then_accepted_substitute_goes_all_the_way(world, as_user):
    r = apply(as_user(STAFF), category="EL", start_date="2027-04-05",
              end_date="2027-04-11", substitute_user_id=SUB)
    pk = r.json()["id"]
    assert r.json()["status"] == "awaiting_substitute"
    assert act(as_user(HEAD), pk, "review", decision="recommended").status_code == 409
    assert act(as_user(SUB), pk, "substitute", accept=False).json()["status"] == \
        "applicant_action_required"
    assert act(as_user(STAFF), pk, "renominate",
               substitute_user_id=OTHER).json()["status"] == "awaiting_substitute"
    assert act(as_user(OTHER), pk, "substitute", accept=True).json()["status"] == \
        "awaiting_unit_head"
    r = act(as_user(HEAD), pk, "review", decision="not_recommended")
    assert r.json()["status"] == "awaiting_establishment"
    assert r.json()["recommendation"] == "not_recommended"
    assert act(as_user(EST), pk, "route").json()["status"] == "awaiting_final_decision"
    assert act(as_user(SANCTION), pk, "decide", approve=True).json()["status"] == "approved"
    assert balances(STAFF, 2027)["EL"] == 23


def test_withdrawal_stops_every_later_decision(world, as_user):
    pk = apply(as_user(STAFF)).json()["id"]
    assert act(as_user(STAFF), pk, "withdraw").json()["status"] == "withdrawn"
    assert act(as_user(HEAD), pk, "review", decision="approve").status_code == 409
    assert act(as_user(STAFF), pk, "withdraw").status_code == 409
    assert LeaveNotification.objects.filter(user_id=HEAD, kind="withdrawn").exists()


def test_overlap_is_refused_but_other_cl_half_is_not(world, as_user):
    me = as_user(STAFF)
    assert apply(me, start_date="2027-02-03", end_date="2027-02-03",
                 half="first").status_code == 201
    assert apply(me, start_date="2027-02-03", end_date="2027-02-03",
                 half="second").status_code == 201
    r = apply(me, start_date="2027-02-02", end_date="2027-02-04")
    assert r.status_code == 409 and r.json()["error"]["code"] == "overlap"


def test_balance_counts_pending_requests_too(world, as_user):
    me = as_user(STAFF)
    assert apply(me, start_date="2027-02-01", end_date="2027-02-05").status_code == 201
    r = apply(me, start_date="2027-02-08", end_date="2027-02-12")
    assert r.status_code == 409 and r.json()["error"]["code"] == "insufficient_balance"


@pytest.mark.parametrize(("over", "code"), [
    ({"category": "RH", "start_date": "2027-03-23", "end_date": "2027-03-23"},
     "not_restricted_holiday"),
    ({"category": "VL", "start_date": "2027-05-11", "end_date": "2027-05-12"},
     "category_not_eligible"),
    ({"start_date": "2027-12-31", "end_date": "2028-01-01"}, "crosses_year"),
    ({"station_leave": True}, "station_address_required"),
    ({"substitute_user_id": STAFF}, "self_substitute"),
    ({"substitute_user_id": 50}, "substitute_not_employee"),
    ({"start_date": "2026-03-02", "end_date": "2026-03-02"}, "calendar_missing"),
])
def test_invalid_applications_say_why(world, as_user, over, code):
    r = apply(as_user(STAFF), **over)
    assert r.json()["error"]["code"] == code, r.json()


def test_rh_on_a_listed_date_and_vl_inside_vacation_are_accepted(world, as_user):
    assert apply(as_user(STAFF), category="RH", start_date="2027-03-22",
                 end_date="2027-03-22").status_code == 201
    r = apply(as_user(HEAD), category="VL", start_date="2027-05-11", end_date="2027-05-20")
    assert r.status_code == 201
    assert r.json()["unit_head_user_id"] == DEAN_HEAD
    r = apply(as_user(HEAD), category="VL", start_date="2027-08-02", end_date="2027-08-03")
    assert r.json()["error"]["code"] == "outside_vacation"


def test_substitute_already_on_leave_is_refused(world, as_user):
    apply(as_user(SUB), start_date="2027-02-01", end_date="2027-02-01")
    r = apply(as_user(STAFF), substitute_user_id=SUB)
    assert r.json()["error"]["code"] == "substitute_unavailable"


def test_director_sanctions_own_leave(world, as_user):
    r = apply(as_user(DIRECTOR), category="COL", start_date="2027-02-01",
              end_date="2027-02-03")
    assert r.json()["status"] == "awaiting_final_decision"
    assert r.json()["director_self"] is True
    pk = r.json()["id"]
    assert act(as_user(DIRECTOR), pk, "decide", approve=True).json()["status"] == "approved"


def test_cancellation_before_start_restores_balance(world, as_user):
    pk = apply(as_user(STAFF)).json()["id"]
    act(as_user(HEAD), pk, "review", decision="approve")
    assert balances(STAFF, 2027)["CL"] == 6
    c = act(as_user(STAFF), pk, "cancel", note="Plans changed").json()
    assert c["kind"] == "cancellation" and c["status"] == "awaiting_unit_head"
    assert act(as_user(STAFF), pk, "cancel").json()["error"]["code"] == \
        "cancellation_pending"
    assert act(as_user(STAFF), c["id"], "withdraw").status_code == 409
    act(as_user(HEAD), c["id"], "review", decision="approve")
    assert LeaveRequest.objects.get(pk=pk).status == "cancelled"
    assert balances(STAFF, 2027)["CL"] == 8


def test_rejected_cancellation_leaves_leave_unchanged(world, as_user):
    pk = apply(as_user(STAFF)).json()["id"]
    act(as_user(HEAD), pk, "review", decision="approve")
    c = act(as_user(STAFF), pk, "cancel").json()
    act(as_user(HEAD), c["id"], "review", decision="reject")
    assert LeaveRequest.objects.get(pk=pk).status == "approved"
    assert balances(STAFF, 2027)["CL"] == 6


def _approved_el(as_user, start="2027-04-05", end="2027-04-11"):
    pk = apply(as_user(STAFF), category="EL", start_date=start, end_date=end).json()["id"]
    act(as_user(HEAD), pk, "review", decision="recommended")
    act(as_user(EST), pk, "route")
    act(as_user(SANCTION), pk, "decide", approve=True)
    return pk


def test_extension_posts_only_the_increment(world, as_user):
    pk = _approved_el(as_user)
    with freeze_time("2027-04-08"):
        assert act(as_user(STAFF), pk, "cancel").json()["error"]["code"] == \
            "already_started"
        r = act(as_user(STAFF), pk, "extend", new_end_date="2027-04-14", purpose="Recovery")
        assert r.status_code == 201, r.json()
        ext = r.json()
        assert (ext["start_date"], ext["days"]) == ("2027-04-12", "3.0")
        act(as_user(HEAD), ext["id"], "review", decision="recommended")
        act(as_user(EST), ext["id"], "route")
        act(as_user(SANCTION), ext["id"], "decide", approve=True)
    assert balances(STAFF, 2027)["EL"] == 20
    assert LeaveRequest.objects.get(pk=pk).end_date == date(2027, 4, 11)


def test_early_resumption_is_reviewed_and_restores_days(world, as_user):
    pk = _approved_el(as_user)
    with freeze_time("2027-04-09"):
        r = act(as_user(STAFF), pk, "resumption", actual_date="2027-04-09")
        assert r.status_code == 201, r.json()
        rid = r.json()["id"]
        tasks = as_user(SANCTION).get("/api/v1/leave/tasks").json()
        assert [t["id"] for t in tasks["resumptions"]] == [rid]
        r = as_user(SANCTION).post(f"/api/v1/leave/resumptions/{rid}/review")
        assert r.json()["outcome"] == "early"
    assert balances(STAFF, 2027)["EL"] == 25


def test_year_end_is_idempotent(world, as_user):
    as_user(HEAD).get("/api/v1/leave/me/balances?year=2027")
    first = periodic.run_year_end(2027)
    rows = LedgerEntry.objects.count()
    assert periodic.run_year_end(2027)["postings"] == 0
    assert LedgerEntry.objects.count() == rows and not first["exceptions"]
    assert balances(HEAD, 2027)["VL"] == 0 and balances(HEAD, 2027)["CL"] == 0
    assert balances(HEAD, 2028)["EL"] == 30 and balances(HEAD, 2028)["COL"] == 20


def test_sla_reminds_once_and_only_while_pending(world, as_user):
    SlaPolicy.objects.create(state="awaiting_unit_head", reminder_hours=24,
                             escalation_hours=72, escalate_to_user_id=DEAN_HEAD)
    pk = apply(as_user(STAFF)).json()["id"]
    later = timezone.now() + timezone.timedelta(hours=80)
    assert periodic.process_sla(later) == {"reminders": 1, "escalations": 1}
    assert periodic.process_sla(later) == {"reminders": 0, "escalations": 0}
    act(as_user(HEAD), pk, "review", decision="approve")
    assert periodic.process_sla(later + timezone.timedelta(hours=80)) == \
        {"reminders": 0, "escalations": 0}


def test_offline_record_synchronises_without_a_workflow(world, as_user):
    admin = as_user(OTHER, perms=ADMIN)
    r = admin.post("/api/v1/leave/records/offline", {
        "user_id": STAFF, "category": "CL", "start_date": "2027-02-01",
        "end_date": "2027-02-01", "reference": "Order 12/2027"}, format="json")
    assert r.status_code == 201, r.json()
    assert r.json()["status"] == "approved" and r.json()["source"] == "offline"
    assert balances(STAFF, 2027)["CL"] == 7
    r = admin.post("/api/v1/leave/records/corrections", {
        "user_id": STAFF, "category": "CL", "year": 2027, "days": "-9",
        "note": "x"}, format="json")
    assert r.json()["error"]["code"] == "negative_balance"
    assert not LeaveNotification.objects.filter(user_id=STAFF, kind="assigned").exists()
