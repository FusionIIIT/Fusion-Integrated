"""The ordinary case first: a person applies, and the path decides it.

One test per composite workflow, driven through the API so the two permission
gates, the guards and the ledger effects are all exercised together.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveLedgerEntry, LeavePolicy, LeaveRequest

pytestmark = pytest.mark.django_db

BASE = "/api/v1/leave"


def weekdays(count=3, *, offset=2):
    """The next `count` weekday dates, so a fixture never lands on a weekend."""
    day = timezone.localdate() + timedelta(days=offset)
    days = []
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


def apply_leave(client, *, category="CL", days=None, **extra):
    days = days or weekdays()
    payload = {"category": category, "start_date": days[0].isoformat(),
               "end_date": days[-1].isoformat(), "purpose": "Family matter"}
    payload.update(extra)
    return client.post(f"{BASE}/requests", payload, format="json")


def approve(client, request_id, *, event=sm.APPROVE, reason="", recommendation=""):
    payload = {"event": event, "reason": reason, "recommendation": recommendation}
    return client.post(f"{BASE}/requests/{request_id}/decision", payload,
                       format="json")


# -- CW-EL-01, the CL/RH path ------------------------------------------------
def test_a_plain_employee_gets_cl_approved_by_their_unit_head(configured, employee,
                                                              unit_head):
    submitted = apply_leave(employee())
    assert submitted.status_code == 201, submitted.content
    row = submitted.json()
    assert row["status"] == sm.AWAITING_UNIT_HEAD
    assert row["current_step_designation"] == "HOD (CSE)"
    assert Decimal(str(row["days_requested"])) > 0

    decided = approve(unit_head(), row["id"])
    assert decided.status_code == 200, decided.content
    assert decided.json()["status"] == sm.APPROVED

    posted = LeaveLedgerEntry.objects.filter(reference=f"request:{row['id']}")
    assert posted.count() == 1
    assert posted.first().entry_type == "debit"


def test_rejecting_needs_a_reason(configured, employee, unit_head):
    row = apply_leave(employee()).json()
    refused = approve(unit_head(), row["id"], event=sm.REJECT)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "reason_required"

    decided = approve(unit_head(), row["id"], event=sm.REJECT, reason="No cover")
    assert decided.json()["status"] == sm.REJECTED


def test_a_unit_head_may_not_approve_their_own_request(configured, employee,
                                                       unit_head):
    client = employee(user_id=9001)
    row = apply_leave(client).json()
    refused = approve(client, row["id"])
    assert refused.status_code in (403, 409)


# -- BR-EL-017..019, the higher-sanction path --------------------------------
def test_el_walks_unit_head_then_establishment_then_the_registrar(
        configured, employee, unit_head, establishment, authority):
    row = apply_leave(employee(), category="EL").json()
    assert row["status"] == sm.AWAITING_UNIT_HEAD

    recommended = approve(unit_head(), row["id"], event=sm.RECOMMEND,
                          recommendation="recommended")
    assert recommended.json()["status"] == sm.AWAITING_ESTABLISHMENT
    assert recommended.json()["current_step_designation"] == "Deputy Registrar (Estt.)"

    forwarded = establishment().post(f"{BASE}/requests/{row['id']}/decision",
                                    {"event": sm.FORWARD}, format="json")
    assert forwarded.status_code == 200, forwarded.content
    assert forwarded.json()["status"] == sm.AWAITING_FINAL_SANCTION

    decided = approve(authority(), row["id"])
    assert decided.json()["status"] == sm.APPROVED


def test_not_recommended_is_not_a_rejection(configured, employee, unit_head,
                                            establishment, authority):
    row = apply_leave(employee(), category="SCL").json()
    moved = approve(unit_head(), row["id"], event=sm.RECOMMEND,
                    recommendation="not_recommended")
    assert moved.json()["status"] == sm.AWAITING_ESTABLISHMENT
    assert moved.json()["status"] != sm.REJECTED


def test_a_unit_head_cannot_decide_a_higher_sanction_case(configured, employee,
                                                          unit_head):
    row = apply_leave(employee(), category="EL").json()
    refused = approve(unit_head(), row["id"])
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "not_unit_head_final"


# -- BR-EL-020, the Director's own leave -------------------------------------
def test_the_director_self_sanctions(configured, employee):
    client = employee(user_id=9500, active_role="Director")
    row = apply_leave(client, category="EL").json()
    assert row["status"] == sm.AWAITING_DIRECTOR_SELF_SANCTION
    decided = approve(client, row["id"])
    assert decided.status_code == 200, decided.content
    assert decided.json()["status"] == sm.APPROVED


# -- EL-UC-007, withdrawal ---------------------------------------------------
def test_withdrawal_is_immediate_and_ends_the_decision(configured, employee,
                                                       unit_head):
    row = apply_leave(employee()).json()
    withdrawn = employee().post(f"{BASE}/requests/{row['id']}/withdraw",
                                {"reason": "Plans changed"}, format="json")
    assert withdrawn.json()["status"] == sm.WITHDRAWN

    late = approve(unit_head(), row["id"], reason="too late")
    assert late.status_code == 409


# -- EL-UC-008 and EL-UC-009, cancellation and extension ---------------------
def test_an_approved_leave_can_be_cancelled_before_it_starts(configured, employee,
                                                             unit_head):
    row = apply_leave(employee()).json()
    approve(unit_head(), row["id"])
    parent = LeaveRequest.objects.get(pk=row["id"])

    requested = employee().post(f"{BASE}/requests/{row['id']}/cancellation",
                                {"reason": "Change of plan"}, format="json")
    assert requested.status_code == 200, requested.content
    assert requested.json()["status"] == sm.CANCELLATION_AWAITING_UNIT_HEAD

    child = requested.json()["id"]
    decided = approve(unit_head(), child, reason="Agreed")
    assert decided.json()["status"] == sm.CANCELLED

    parent.refresh_from_db()
    assert parent.status == sm.CANCELLED
    assert LeaveLedgerEntry.objects.filter(
        reference=f"cancelled:{parent.pk}").exists()


def test_a_started_leave_cannot_be_cancelled(configured, employee):
    today = timezone.localdate()
    row = LeaveRequest.objects.create(
        user_id=1001, kind="new", category="CL", start_date=today,
        end_date=today + timedelta(days=1), purpose="On leave",
        status=sm.APPROVED, applicant_role="staff", days_approved=Decimal(2),
        days_requested=Decimal(2))
    refused = employee().post(f"{BASE}/requests/{row.pk}/cancellation",
                              {"reason": "too late"}, format="json")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "leave_started"


def test_an_ongoing_el_can_be_extended_and_posts_only_the_extra_days(
        configured, employee, unit_head, establishment, authority):
    today = timezone.localdate()
    parent = LeaveRequest.objects.create(
        user_id=1001, kind="new", category="EL", start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=2), purpose="Medical",
        status=sm.APPROVED, applicant_role="staff", applicant_is_faculty=True,
        days_requested=Decimal(4), days_approved=Decimal(4))
    extra = today + timedelta(days=3)

    requested = employee().post(
        f"{BASE}/requests/{parent.pk}/extension",
        {"start_date": (today + timedelta(days=3)).isoformat(),
         "end_date": (today + timedelta(days=4)).isoformat(),
         "purpose": "Recovery"}, format="json")
    assert requested.status_code == 201, requested.content
    child = requested.json()
    assert child["status"] == sm.EXTENSION_AWAITING_UNIT_HEAD

    approve(unit_head(), child["id"], event=sm.RECOMMEND,
            recommendation="recommended")
    establishment().post(f"{BASE}/requests/{child['id']}/decision",
                         {"event": sm.FORWARD}, format="json")
    decided = approve(authority(), child["id"])
    assert decided.json()["status"] == sm.APPROVED

    parent.refresh_from_db()
    assert parent.status == sm.APPROVED, "an extension never rewrites the original"
    assert extra > parent.end_date
    assert LeaveLedgerEntry.objects.filter(reference=f"request:{child['id']}").exists()


def test_an_extension_is_refused_for_a_cl(configured, employee):
    today = timezone.localdate()
    parent = LeaveRequest.objects.create(
        user_id=1001, kind="new", category="CL", start_date=today,
        end_date=today + timedelta(days=2), purpose="Rest", status=sm.APPROVED,
        applicant_role="staff", days_requested=Decimal(3), days_approved=Decimal(3))
    refused = employee().post(
        f"{BASE}/requests/{parent.pk}/extension",
        {"start_date": (today + timedelta(days=1)).isoformat(),
         "end_date": (today + timedelta(days=2)).isoformat(),
         "purpose": "More"}, format="json")
    assert refused.status_code == 409


# -- EL-UC-010 and EL-UC-011, resumption ------------------------------------
def test_resumption_review_matches_the_actual_return_date(configured, employee,
                                                          authority):
    today = timezone.localdate()
    row = LeaveRequest.objects.create(
        user_id=1001, kind="new", category="EL", start_date=today - timedelta(days=10),
        end_date=today - timedelta(days=2), purpose="Medical", status=sm.APPROVED,
        applicant_role="staff", days_requested=Decimal(8), days_approved=Decimal(8))

    submitted = employee().post(
        f"{BASE}/requests/{row.pk}/resumption",
        {"actual_date": (today - timedelta(days=2)).isoformat()}, format="json")
    assert submitted.status_code == 200, submitted.content
    assert submitted.json()["status"] == sm.RESUMPTION_REVIEW_PENDING

    reviewed = authority().post(
        f"{BASE}/requests/{row.pk}/resumption/review",
        {"actual_date": (today - timedelta(days=3)).isoformat()}, format="json")
    assert reviewed.status_code == 200, reviewed.content
    assert reviewed.json()["status"] == sm.RESUMPTION_EARLY


def test_resumption_is_refused_for_a_category_that_has_none(configured, employee):
    today = timezone.localdate()
    row = LeaveRequest.objects.create(
        user_id=1001, kind="new", category="CL", start_date=today - timedelta(days=5),
        end_date=today - timedelta(days=4), purpose="Rest", status=sm.APPROVED,
        applicant_role="staff", days_requested=Decimal(2), days_approved=Decimal(2))
    refused = employee().post(f"{BASE}/requests/{row.pk}/resumption",
                              {"actual_date": today.isoformat()}, format="json")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "resumption_not_applicable"


# -- EL-UC-002 and EL-UC-019, the consent gate ------------------------------
def test_a_required_substitute_holds_the_gate_until_they_accept(
        configured, employee, unit_head):
    policy = LeavePolicy.objects.get(is_active=True)
    policy.substitute_required_categories = [cat.CL]
    policy.save(update_fields=["substitute_required_categories"])

    row = apply_leave(employee(), substitute_user_id=1002).json()
    assert row["status"] == sm.AWAITING_SUBSTITUTE

    substitute = employee(user_id=1002)
    accepted = substitute.post(
        f"{BASE}/substitute-requests/{row['id']}/respond", {"accept": True},
        format="json")
    assert accepted.status_code == 200, accepted.content
    assert accepted.json()["status"] == sm.AWAITING_UNIT_HEAD


def test_a_declined_substitute_opens_the_replacement_route(configured, employee):
    policy = LeavePolicy.objects.get(is_active=True)
    policy.substitute_required_categories = [cat.CL]
    policy.save(update_fields=["substitute_required_categories"])

    row = apply_leave(employee(), substitute_user_id=1002).json()
    declined = employee(user_id=1002).post(
        f"{BASE}/substitute-requests/{row['id']}/respond",
        {"accept": False, "reason": "Away myself"}, format="json")
    assert declined.json()["status"] == sm.APPLICANT_ACTION_REQUIRED

    replaced = employee().post(f"{BASE}/requests/{row['id']}/substitute",
                               {"substitute_user_id": 1003}, format="json")
    assert replaced.status_code == 200, replaced.content
    assert replaced.json()["status"] == sm.AWAITING_SUBSTITUTE


def test_nominating_yourself_is_refused(configured, employee):
    policy = LeavePolicy.objects.get(is_active=True)
    policy.substitute_required_categories = [cat.CL]
    policy.save(update_fields=["substitute_required_categories"])
    refused = apply_leave(employee(), substitute_user_id=1001)
    assert refused.status_code in (403, 409)
