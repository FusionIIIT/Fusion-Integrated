"""Error paths and the adversarial pass (Step 5.11): 400, 404, 409, 422, 429."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.department.models import (
    Department,
    InventoryItem,
    RoleTenure,
    StockMovement,
    StockRequest,
)
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _approved(act, qty=4, stock=5):
    item = (
        act("admin")
        .post(
            f"{API}/inventory-items", {"name": f"Kit{qty}{stock}", "quantity": stock}, format="json"
        )
        .json()["id"]
    )
    req = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item, "quantity": qty}, format="json")
        .json()["id"]
    )
    act("hod").post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
    return item, req


def test_unparseable_filter_is_400_not_500(world, act):
    for path in ("stock-requests?status=lost", "feedback?status=x", "official-changes?status=y"):
        r = act("admin").get(f"{API}/{path}")
        assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_filter"


def test_bad_cursor_and_non_numeric_id_are_not_500(world, act):
    assert act("admin").get(f"{API}/inventory-items?cursor=%%%").status_code < 500
    assert act("admin").get(f"{API}/feedback/abc").status_code == 404


def test_same_decision_sent_twice_takes_effect_once(world, act):
    _, req = _approved(act)
    r = act("hod").post(f"{API}/stock-requests/{req}/decide", {"approve": False}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"
    assert StockRequest.objects.get(pk=req).status == "approved"


def test_issuing_twice_issues_once(world, act):
    item, req = _approved(act)
    assert act("admin").post(f"{API}/stock-requests/{req}/issue").status_code == 200
    assert act("admin").post(f"{API}/stock-requests/{req}/issue").status_code == 409
    assert InventoryItem.objects.get(pk=item).current_quantity == 1
    assert StockMovement.objects.filter(kind="issue").count() == 1


def test_q13_issuance_never_drives_stock_negative(world, act):
    # Q13: no business re-check at issuance, but the ledger refuses a negative balance
    item = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Wire", "quantity": 5}, format="json")
        .json()["id"]
    )
    reqs = [
        act(w)
        .post(f"{API}/stock-requests", {"item": item, "quantity": 4}, format="json")
        .json()["id"]
        for w in ("faculty", "faculty2")
    ]
    for req in reqs:
        act("hod").post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
    assert act("admin").post(f"{API}/stock-requests/{reqs[0]}/issue").status_code == 200
    r = act("admin").post(f"{API}/stock-requests/{reqs[1]}/issue")
    assert r.status_code == 409 and r.json()["error"]["code"] == "stock_exhausted"
    assert InventoryItem.objects.get(pk=item).current_quantity == 1
    assert StockRequest.objects.get(pk=reqs[1]).status == "approved"


def test_stock_movements_cannot_be_altered(world, act):
    # BR-DEPT-016
    _approved(act)
    move = StockMovement.objects.first()
    move.quantity = 99
    with pytest.raises(TypeError):
        move.save()
    with pytest.raises(TypeError):
        move.delete()
    with pytest.raises(TypeError):
        StockMovement.objects.all().update(quantity=1)
    with pytest.raises(TypeError):
        StockMovement.objects.all().delete()


def test_duplicate_item_is_409(world, act):
    act("admin").post(f"{API}/inventory-items", {"name": "Kit", "quantity": 1}, format="json")
    r = act("admin").post(f"{API}/inventory-items", {"name": "KIT", "quantity": 1}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "item_exists"


def test_closed_feedback_cannot_be_reopened_or_reviewed(world, act):
    fb = (
        act("student")
        .post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json")
        .json()["id"]
    )
    act("admin").post(f"{API}/feedback/{fb}/review", {"disposition": "closed"}, format="json")
    assert act("admin").post(f"{API}/feedback/{fb}/review", {}, format="json").status_code == 409
    assert (
        act("hod")
        .post(f"{API}/feedback/{fb}/dispose", {"outcome": "resolved"}, format="json")
        .status_code
        == 409
    )


def test_new_feedback_cannot_skip_initial_review(world, act):
    # BR-DEPT-018: no path from New straight to a disposition
    fb = (
        act("student")
        .post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json")
        .json()["id"]
    )
    r = act("admin").post(f"{API}/feedback/{fb}/dispose", {"outcome": "resolved"}, format="json")
    assert r.status_code == 409
    assert (
        act("admin").post(f"{API}/feedback/{fb}/notes", {"body": "n"}, format="json").status_code
        == 409
    )


def test_note_and_review_validation(world, act):
    fb = (
        act("student")
        .post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json")
        .json()["id"]
    )
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb}/review", {"category": "rant"}, format="json")
        .status_code
        == 400
    )
    act("admin").post(f"{API}/feedback/{fb}/review", {}, format="json")
    assert (
        act("hod").post(f"{API}/feedback/{fb}/notes", {"body": " "}, format="json").status_code
        == 422
    )


def test_hidden_or_deleted_announcement_cannot_be_changed(world, act):
    aid = (
        act("hod")
        .post(
            f"{API}/announcements",
            {"title": "t", "body": "b", "audience_role": "all"},
            format="json",
        )
        .json()["id"]
    )
    act("hod").post(f"{API}/announcements/{aid}/hide")
    r = act("hod").patch(f"{API}/announcements/{aid}", {"title": "x"}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "announcement_not_active"
    assert act("hod").delete(f"{API}/announcements/{aid}").status_code == 409


def test_official_change_cannot_carry_headship_or_be_decided_twice(world, act):
    # AFR-DEPT-053, BR-DEPT-011
    r = act("admin").post(
        f"{API}/official-changes", {"field": "headship", "value": "Me"}, format="json"
    )
    assert r.status_code == 400
    cid = (
        act("admin")
        .post(f"{API}/official-changes", {"field": "name", "value": "N"}, format="json")
        .json()["id"]
    )
    dup = act("admin").post(
        f"{API}/official-changes", {"field": "name", "value": "M"}, format="json"
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "change_pending"
    act("hod").post(f"{API}/official-changes/{cid}/decide", {"approve": False}, format="json")
    assert (
        act("hod")
        .post(f"{API}/official-changes/{cid}/decide", {"approve": True}, format="json")
        .status_code
        == 409
    )
    assert Department.objects.get(code="CSE").name == "Computer Science and Engineering"


def test_general_update_cannot_smuggle_an_official_field(world, act):
    r = act("admin").patch(f"{API}/departments/CSE", {"name": "Mine"}, format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "official_field"


def test_tenure_refusals(world, act):
    # BR-DEPT-021, BR-DEPT-022, BR-DEPT-023, AFR-DEPT-047, Q1
    now = timezone.now()
    base = {
        "department": "CSE",
        "role": "hod",
        "user_id": uid("faculty"),
        "valid_from": (now + timedelta(days=400)).isoformat(),
        "valid_to": (now + timedelta(days=500)).isoformat(),
    }
    c = act("central")
    assert (
        c.post(
            f"{API}/role-assignments", {**base, "user_id": uid("student")}, format="json"
        ).json()["error"]["code"]
        == "not_employee"
    )
    assert (
        c.post(f"{API}/role-assignments", {**base, "user_id": 999999}, format="json").status_code
        == 422
    )
    back = {**base, "valid_from": (now - timedelta(days=3)).isoformat()}
    assert (
        c.post(f"{API}/role-assignments", back, format="json").json()["error"]["code"]
        == "backdated_tenure"
    )
    inverted = {**base, "valid_to": base["valid_from"]}
    assert (
        c.post(f"{API}/role-assignments", inverted, format="json").json()["error"]["code"]
        == "invalid_interval"
    )
    assert (
        c.post(f"{API}/role-assignments", {**base, "department": "XX"}, format="json").status_code
        == 404
    )
    current = RoleTenure.objects.get(user_id=uid("hod"))
    early = c.patch(
        f"{API}/role-assignments/{current.pk}",
        {"valid_to": (now + timedelta(days=2)).isoformat()},
        format="json",
    )
    assert early.status_code == 422 and early.json()["error"]["code"] == "would_leave_gap"
    past = c.patch(
        f"{API}/role-assignments/{current.pk}",
        {"valid_to": (now - timedelta(days=2)).isoformat()},
        format="json",
    )
    assert past.status_code == 422


def test_ended_tenure_cannot_be_changed_and_extension_cannot_overlap(world, act):
    now = timezone.now()
    ended = RoleTenure.objects.create(
        department=world["CSE"],
        role="dept_admin",
        user_id=uid("central"),
        valid_from=now - timedelta(days=30),
        valid_to=now - timedelta(days=20),
        assigned_by=1,
    )
    c = act("central")
    r = c.patch(
        f"{API}/role-assignments/{ended.pk}",
        {"valid_to": (now + timedelta(days=1)).isoformat()},
        format="json",
    )
    assert r.status_code == 409
    nxt = c.post(
        f"{API}/role-assignments",
        {
            "department": "ECE",
            "role": "hod",
            "user_id": uid("faculty2"),
            "valid_from": (now + timedelta(days=400)).isoformat(),
            "valid_to": (now + timedelta(days=500)).isoformat(),
        },
        format="json",
    )
    assert nxt.status_code == 201
    ece_current = RoleTenure.objects.get(user_id=uid("ece_hod"))
    r = c.patch(
        f"{API}/role-assignments/{ece_current.pk}",
        {"valid_to": (now + timedelta(days=450)).isoformat()},
        format="json",
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "tenure_overlap"


def test_profile_refusals(world, act):
    c = act("admin")
    assert (
        c.post(f"{API}/profiles", {"kind": "faculty"}, format="json").json()["error"]["code"]
        == "profile_needs_user"
    )
    assert (
        c.post(f"{API}/profiles", {"kind": "alumni"}, format="json").json()["error"]["code"]
        == "profile_incomplete"
    )
    c.post(f"{API}/profiles", {"kind": "faculty", "user_id": uid("faculty")}, format="json")
    dup = c.post(f"{API}/profiles", {"kind": "faculty", "user_id": uid("faculty")}, format="json")
    assert dup.status_code == 409
    pid = dup.json()["error"] and c.get(f"{API}/profiles").json()["results"][0]["id"]
    assert c.patch(f"{API}/profiles/{pid}", {"display_name": ""}, format="json").status_code == 422


def test_lab_name_clash_is_409(world, act):
    act("admin").post(f"{API}/lab-resources", {"name": "IoT Lab"}, format="json")
    assert (
        act("admin").post(f"{API}/lab-resources", {"name": "iot lab"}, format="json").status_code
        == 409
    )


def test_timetable_refusals(world, act):
    slot = {
        "kind": "class",
        "course_code": "C",
        "day_of_week": 0,
        "starts_at": "10:00",
        "ends_at": "09:00",
    }
    assert (
        act("admin").post(f"{API}/timetable-slots", {"slots": [slot]}, format="json").status_code
        == 422
    )
    good = (
        act("admin")
        .post(
            f"{API}/timetable-slots",
            {"slots": [{**slot, "ends_at": "11:00", "room": "R1"}]},
            format="json",
        )
        .json()[0]["id"]
    )
    other = (
        act("admin")
        .post(
            f"{API}/timetable-slots",
            {"slots": [{**slot, "starts_at": "12:00", "ends_at": "13:00", "room": "R1"}]},
            format="json",
        )
        .json()[0]["id"]
    )
    r = act("admin").patch(f"{API}/timetable-slots/{other}", {"starts_at": "10:30"}, format="json")
    assert r.status_code == 422
    assert act("admin").delete(f"{API}/timetable-slots/{good}").status_code == 204
    assert (
        act("admin")
        .patch(f"{API}/timetable-slots/{other}", {"starts_at": "10:30"}, format="json")
        .status_code
        == 200
    )


def test_writes_are_throttled_and_reads_are_not(world, act, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    rates = {**SimpleRateThrottle.THROTTLE_RATES, "department_write": "2/min"}
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
    c = act("student")
    codes = [
        c.post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json").status_code
        for _ in range(3)
    ]
    assert codes == [201, 201, 429]
    assert c.get(f"{API}/feedback").status_code == 200


def test_actor_without_a_department_is_told_how_to_get_one(world, act, stub_iam):
    # A student whose discipline has no department (MT) is refused plainly, not with a 500
    from modules.department.tests.conftest import PEOPLE, Person, session_for, user_refs

    PEOPLE["mt_student"] = Person(2999, "student", "student", discipline="MT")
    try:
        c = act("mt_student")
        r = c.post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json")
        assert r.status_code == 422 and r.json()["error"]["code"] == "no_department"
        assert c.get(f"{API}/announcements").json()["results"] == []
    finally:
        PEOPLE.pop("mt_student")
    assert session_for and user_refs


def test_a_pending_request_cannot_be_issued_before_the_hod_decides(world, act):
    # BR-DEPT-007, AFR-DEPT-012: issue only after HOD approval
    item = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Fuse", "quantity": 5}, format="json")
        .json()["id"]
    )
    req = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item, "quantity": 1}, format="json")
        .json()["id"]
    )
    r = act("admin").post(f"{API}/stock-requests/{req}/issue")
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"
    assert InventoryItem.objects.get(pk=item).current_quantity == 5


HUGE = 10**12


@pytest.mark.parametrize(
    ("who", "path", "body"),
    [
        ("admin", "inventory-items", {"name": "Big", "quantity": HUGE}),
        ("admin", "lab-resources", {"name": "Big", "capacity": HUGE}),
        (
            "admin",
            "timetable-slots",
            {
                "slots": [
                    {
                        "kind": "class",
                        "course_code": "C",
                        "day_of_week": 0,
                        "starts_at": "09:00",
                        "ends_at": "10:00",
                        "batch_year": HUGE,
                    }
                ]
            },
        ),
        ("faculty", "stock-requests", {"item": HUGE, "quantity": 1}),
        (
            "faculty",
            "announcements",
            {"title": "t", "body": "b", "audience_role": "all", "batch_year": HUGE},
        ),
        ("admin", "profiles", {"kind": "faculty", "user_id": HUGE}),
        (
            "central",
            "role-assignments",
            {
                "department": "CSE",
                "role": "hod",
                "user_id": HUGE,
                "valid_from": "2030-01-01T00:00:00Z",
                "valid_to": "2031-01-01T00:00:00Z",
            },
        ),
    ],
)
def test_out_of_range_numbers_are_400_not_500(world, act, who, path, body):
    # R1-02: every integer input is bounded to fit its column
    r = act(who).post(f"{API}/{path}", body, format="json")
    assert r.status_code == 400, r.content


def test_huge_receipt_and_huge_row_id_are_not_500(world, act):
    item = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Kit", "quantity": 1}, format="json")
        .json()["id"]
    )
    assert (
        act("admin")
        .post(f"{API}/inventory-items/{item}/receipts", {"quantity": HUGE}, format="json")
        .status_code
        == 400
    )
    assert act("admin").get(f"{API}/feedback/{HUGE * 10**8}").status_code == 404
    assert (
        act("admin").patch(f"{API}/profiles/{HUGE}", {"office": "x"}, format="json").status_code
        == 404
    )
