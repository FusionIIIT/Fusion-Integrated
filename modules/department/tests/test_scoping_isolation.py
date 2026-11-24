"""Person A never sees person B's rows, by list, by filter or by id (Step 5.6)."""

import pytest

from modules.department.models import Feedback
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _new(act, who, path, body):
    data = act(who).post(f"{API}/{path}", body, format="json").json()
    return data[0]["id"] if isinstance(data, list) else data["id"]


ECE_SLOT = {
    "kind": "lab",
    "course_code": "EC1",
    "day_of_week": 1,
    "starts_at": "09:00",
    "ends_at": "10:00",
}


def _ece_world(act):
    item = _new(act, "ece_admin", "inventory-items", {"name": "Scope", "quantity": 4})
    fb = _new(act, "ece_student", "feedback", {"subject": "s", "body": "b"})
    act("ece_admin").post(f"{API}/feedback/{fb}/review", {}, format="json")
    ann_body = {"title": "ECE only", "body": "b", "audience_role": "all"}
    return {
        "item": item,
        "req": _new(act, "ece_faculty", "stock-requests", {"item": item, "quantity": 1}),
        "fb": fb,
        "ann": _new(act, "ece_faculty", "announcements", ann_body),
        "lab": _new(act, "ece_admin", "lab-resources", {"name": "RF Lab"}),
        "slot": _new(act, "ece_admin", "timetable-slots", {"slots": [ECE_SLOT]}),
        "prof": _new(act, "ece_admin", "profiles", {"kind": "alumni", "display_name": "E. Alum"}),
        "chg": _new(act, "ece_admin", "official-changes", {"field": "name", "value": "ECE!"}),
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
    probes = [
        ("hod", "post", f"stock-requests/{ids['req']}/decide", {"approve": True}),
        ("hod", "post", f"official-changes/{ids['chg']}/decide", {"approve": True}),
        ("hod", "patch", f"announcements/{ids['ann']}", {"title": "x"}),
        ("hod", "get", f"feedback/{ids['fb']}", None),
        ("admin", "post", f"inventory-items/{ids['item']}/receipts", {"quantity": 1}),
        ("admin", "patch", f"lab-resources/{ids['lab']}", {"name": "x"}),
        ("admin", "patch", f"timetable-slots/{ids['slot']}", {"room": "x"}),
        ("admin", "patch", f"profiles/{ids['prof']}", {"office": "x"}),
        ("admin", "patch", "departments/ECE", {"description": "x"}),
        ("faculty", "post", "stock-requests", {"item": ids["item"], "quantity": 1}),
    ]
    for who, method, path, body in probes:
        r = getattr(act(who), method)(f"{API}/{path}", body, format="json")
        assert r.status_code == 404, (who, method, path)


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


def test_vacancies_are_scoped_to_the_viewers_departments(world, act):
    # Q1: the HOD sees their own department's warnings; the central authority sees all
    hod_view = act("hod").get(f"{API}/role-assignments/vacancies").json()
    assert hod_view == []
    central_view = act("central").get(f"{API}/role-assignments/vacancies").json()
    assert {w["department"] for w in central_view} == {"Design", "LA", "ME", "NS", "SM"}


def _office_rows(act):
    item = (
        act("admin")
        .post(f"{API}/inventory-items", {"name": "Dual", "quantity": 3}, format="json")
        .json()["id"]
    )
    act("faculty").post(f"{API}/stock-requests", {"item": item, "quantity": 1}, format="json")
    act("admin").post(f"{API}/lab-resources", {"name": "Dual Lab"}, format="json")
    act("admin").post(f"{API}/official-changes", {"field": "name", "value": "CS&E"}, format="json")


OFFICE_HELD = ("faculty", "HOD (CSE)", "deptadmin_cse")
OFFICE_ONLY = {
    "student": (
        "official-changes",
        "inventory-items",
        "stock-movements",
        "stock-requests",
        "lab-resources",
        "role-assignments",
    ),
    "faculty": ("official-changes", "stock-movements", "role-assignments"),
}


@pytest.mark.parametrize(
    "who,path", [(who, path) for who, paths in OFFICE_ONLY.items() for path in paths]
)
def test_r4_02_a_dual_designation_principal_lists_only_the_acting_roles_rows(world, act, who, path):
    # The session holds every office permission; only the acting role may decide what is listed.
    _office_rows(act)
    assert act("admin").get(f"{API}/{path}").json()["results"], "the office must see rows here"
    res = act(who, also_holds=OFFICE_HELD).get(f"{API}/{path}")
    assert res.status_code == 200 and res.json()["results"] == []


def test_r6_02_a_deleted_announcement_is_gone_from_the_hods_list_and_detail(world, act):
    # AFR-DEPT-006 with Q7: kept for audit, gone from every view
    ann = _new(
        act, "faculty", "announcements", {"title": "Gone", "body": "b", "audience_role": "all"}
    )
    hidden = _new(
        act, "faculty", "announcements", {"title": "Hid", "body": "b", "audience_role": "all"}
    )
    hod = act("hod")
    assert hod.delete(f"{API}/announcements/{ann}").status_code == 204
    assert hod.post(f"{API}/announcements/{hidden}/hide").status_code == 200
    assert [a["title"] for a in hod.get(f"{API}/announcements").json()["results"]] == ["Hid"]
    assert hod.patch(f"{API}/announcements/{ann}", {"title": "x"}, format="json").status_code == 404


def test_r6_02_faculty_never_see_a_deactivated_profile(world, act):
    # Q8: a record is deactivated, never deleted; only the office still sees it
    prof = _new(act, "admin", "profiles", {"kind": "alumni", "display_name": "Old Alum"})
    assert (
        act("admin")
        .patch(f"{API}/profiles/{prof}", {"is_active": False}, format="json")
        .status_code
        == 200
    )
    assert act("faculty").get(f"{API}/profiles").json()["results"] == []
    assert act("faculty").get(f"{API}/profiles/{prof}").status_code == 404
    assert [p["id"] for p in act("admin").get(f"{API}/profiles").json()["results"]] == [prof]
