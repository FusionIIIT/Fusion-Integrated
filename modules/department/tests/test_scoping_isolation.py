"""Person A never sees person B's rows, by list, by filter or by id (Step 5.6)."""

import pytest

from modules.department.models import Feedback
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _ece_world(act):
    item = (
        act("ece_admin")
        .post(f"{API}/inventory-items", {"name": "Scope", "quantity": 4}, format="json")
        .json()["id"]
    )
    req = (
        act("ece_faculty")
        .post(f"{API}/stock-requests", {"item": item, "quantity": 1}, format="json")
        .json()["id"]
    )
    fb = (
        act("ece_student")
        .post(f"{API}/feedback", {"subject": "s", "body": "b"}, format="json")
        .json()["id"]
    )
    act("ece_admin").post(f"{API}/feedback/{fb}/review", {}, format="json")
    ann = (
        act("ece_faculty")
        .post(
            f"{API}/announcements",
            {"title": "ECE only", "body": "b", "audience_role": "all"},
            format="json",
        )
        .json()["id"]
    )
    lab = (
        act("ece_admin")
        .post(f"{API}/lab-resources", {"name": "RF Lab"}, format="json")
        .json()["id"]
    )
    slot = (
        act("ece_admin")
        .post(
            f"{API}/timetable-slots",
            {
                "slots": [
                    {
                        "kind": "lab",
                        "course_code": "EC1",
                        "day_of_week": 1,
                        "starts_at": "09:00",
                        "ends_at": "10:00",
                    }
                ]
            },
            format="json",
        )
        .json()[0]["id"]
    )
    prof = (
        act("ece_admin")
        .post(f"{API}/profiles", {"kind": "alumni", "display_name": "E. Alum"}, format="json")
        .json()["id"]
    )
    chg = (
        act("ece_admin")
        .post(f"{API}/official-changes", {"field": "name", "value": "ECE!"}, format="json")
        .json()["id"]
    )
    return {
        "item": item,
        "req": req,
        "fb": fb,
        "ann": ann,
        "lab": lab,
        "slot": slot,
        "prof": prof,
        "chg": chg,
    }


def test_another_departments_office_sees_none_of_its_lists(world, act):
    # BR-DEPT-012, BR-DEPT-017, BR-DEPT-019; scoping is by the actor's department
    _ece_world(act)
    for who in ("hod", "admin"):
        c = act(who)
        for path in (
            "inventory-items",
            "stock-requests",
            "stock-movements",
            "feedback",
            "announcements",
            "lab-resources",
            "profiles",
            "official-changes",
        ):
            r = c.get(f"{API}/{path}")
            if r.status_code == 200:
                assert r.json()["results"] == [], (who, path)
        assert c.get(f"{API}/timetable-slots").json() == []
        assert [d["code"] for d in c.get(f"{API}/departments").json()] == ["CSE"]


def test_another_departments_rows_are_404_by_id(world, act):
    ids = _ece_world(act)
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{ids['req']}/decide", {"approve": True}, format="json")
        .status_code
        == 404
    )
    assert (
        act("hod")
        .post(f"{API}/official-changes/{ids['chg']}/decide", {"approve": True}, format="json")
        .status_code
        == 404
    )
    assert (
        act("hod")
        .patch(f"{API}/announcements/{ids['ann']}", {"title": "x"}, format="json")
        .status_code
        == 404
    )
    assert act("hod").get(f"{API}/feedback/{ids['fb']}").status_code == 404
    assert (
        act("admin")
        .post(f"{API}/inventory-items/{ids['item']}/receipts", {"quantity": 1}, format="json")
        .status_code
        == 404
    )
    assert (
        act("admin")
        .patch(f"{API}/lab-resources/{ids['lab']}", {"name": "x"}, format="json")
        .status_code
        == 404
    )
    assert (
        act("admin")
        .patch(f"{API}/timetable-slots/{ids['slot']}", {"room": "x"}, format="json")
        .status_code
        == 404
    )
    assert (
        act("admin")
        .patch(f"{API}/profiles/{ids['prof']}", {"office": "x"}, format="json")
        .status_code
        == 404
    )
    assert (
        act("admin")
        .patch(f"{API}/departments/ECE", {"description": "x"}, format="json")
        .status_code
        == 404
    )
    assert (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": ids["item"], "quantity": 1}, format="json")
        .status_code
        == 404
    )


def test_feedback_is_visible_only_to_its_submitter_and_the_handling_office(world, act):
    # BR-DEPT-017, AFR-DEPT-018, CFR-DEPT-007
    fb = (
        act("student")
        .post(f"{API}/feedback", {"subject": "private", "body": "b"}, format="json")
        .json()["id"]
    )
    assert act("student2").get(f"{API}/feedback").json()["results"] == []
    assert act("student2").get(f"{API}/feedback/{fb}").status_code == 404
    assert act("faculty").get(f"{API}/feedback/{fb}").status_code == 404
    assert act("hod").get(f"{API}/feedback").json()["results"] == []  # BR-DEPT-018 before review
    assert [f["id"] for f in act("admin").get(f"{API}/feedback").json()["results"]] == [fb]
    assert Feedback.objects.get(pk=fb).submitter_id == uid("student")


def test_status_filter_does_not_widen_scope(world, act):
    act("admin").post(f"{API}/inventory-items", {"name": "Kit", "quantity": 5}, format="json")
    item = act("admin").get(f"{API}/inventory-items").json()["results"][0]["id"]
    act("faculty2").post(f"{API}/stock-requests", {"item": item, "quantity": 1}, format="json")
    assert act("faculty").get(f"{API}/stock-requests?status=pending_hod").json()["results"] == []


def test_students_never_see_alumni_or_inactive_profiles(world, act):
    # BR-DEPT-019, AFR-DEPT-025
    act("admin").post(f"{API}/profiles", {"kind": "alumni", "display_name": "Alum"}, format="json")
    pid = (
        act("admin")
        .post(f"{API}/profiles", {"kind": "faculty", "user_id": uid("faculty")}, format="json")
        .json()["id"]
    )
    act("admin").patch(f"{API}/profiles/{pid}", {"is_active": False}, format="json")
    assert act("student").get(f"{API}/profiles").json()["results"] == []
    assert act("student").get(f"{API}/profiles/{pid}").status_code == 404


def test_hod_tenures_list_is_own_department_and_central_sees_all(world, act):
    assert {
        t["department"] for t in act("hod").get(f"{API}/role-assignments").json()["results"]
    } == {"CSE"}
    assert {
        t["department"] for t in act("central").get(f"{API}/role-assignments").json()["results"]
    } == {"CSE", "ECE"}
