"""One test per use case's main flow and each named alternate, through HTTP only (Step 5.12)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.department.models import (
    Announcement,
    Department,
    DepartmentNotification,
    Feedback,
    InventoryItem,
    OfficialChange,
    ProfileRecord,
    RoleTenure,
    StockMovement,
    StockRequest,
    TimetableSlot,
)
from modules.department.services import roles as role_service
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _topic(topic):
    return set(
        DepartmentNotification.objects.filter(topic=topic).values_list(
            "recipient_user_id", flat=True
        )
    )


def _item(act, qty=10, name="Arduino Uno"):
    r = act("admin").post(
        f"{API}/inventory-items", {"name": name, "unit": "board", "quantity": qty}, format="json"
    )
    assert r.status_code == 201, r.content
    return r.json()["id"]


# -- announcements ---------------------------------------------------------------
def test_uc_dept_002_faculty_publishes_and_relevant_students_are_notified(world, act):
    # UC-DEPT-002 main flow; BR-DEPT-001, BR-DEPT-003, AFR-DEPT-001, AFR-DEPT-046, CFR-DEPT-001
    r = act("faculty").post(
        f"{API}/announcements",
        {
            "title": "Lab closed",
            "body": "Friday maintenance.",
            "audience_role": "student",
            "programme": "B.Tech",
            "batch_year": 2024,
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    ann = Announcement.objects.get(pk=r.json()["id"])
    assert ann.author_id == uid("faculty") and ann.status == "active"
    assert _topic("announcement.published") == {uid("student")}


def test_uc_dept_002_alternate_incomplete_announcement_is_blocked(world, act):
    # UC-DEPT-002 alternate flow; BR-DEPT-003 invalid/missing content
    r = act("admin").post(
        f"{API}/announcements",
        {"title": "", "body": "x", "audience_role": "everyone"},
        format="json",
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "announcement_incomplete"
    assert {d["field"] for d in r.json()["error"]["details"]} == {"title", "audience_role"}
    assert not Announcement.objects.exists()


def test_uc_dept_001_student_sees_only_relevant_announcements(world, act):
    # UC-DEPT-001 main flow; BR-DEPT-002, AFR-DEPT-002, AFR-DEPT-003, CFR-DEPT-002
    for title, role, prog, year in [
        ("mine", "student", "B.Tech", 2024),
        ("all", "all", "", None),
        ("other year", "student", "B.Tech", 2023),
        ("faculty only", "faculty", "", None),
        ("other programme", "student", "M.Tech", None),
    ]:
        act("hod").post(
            f"{API}/announcements",
            {
                "title": title,
                "body": "b",
                "audience_role": role,
                "programme": prog,
                "batch_year": year,
            },
            format="json",
        )
    titles = {a["title"] for a in act("student").get(f"{API}/announcements").json()["results"]}
    assert titles == {"mine", "all"}


def test_uc_dept_001_alternate_no_relevant_announcement_gives_empty_list(world, act):
    # UC-DEPT-001 alternate flow: empty state
    r = act("student").get(f"{API}/announcements")
    assert r.status_code == 200 and r.json()["results"] == []


def test_uc_dept_003_hod_edits_hides_and_deletes_active_announcements(world, act):
    # UC-DEPT-003 main + edit/hide/delete alternates; BR-DEPT-004, AFR-DEPT-004, AFR-DEPT-005, AFR-DEPT-006, CFR-DEPT-003
    ids = [
        act("faculty")
        .post(
            f"{API}/announcements",
            {"title": f"t{i}", "body": "b", "audience_role": "all"},
            format="json",
        )
        .json()["id"]
        for i in range(3)
    ]
    r = act("hod").patch(f"{API}/announcements/{ids[0]}", {"title": "edited"}, format="json")
    assert r.status_code == 200 and r.json()["title"] == "edited"
    bad = act("hod").patch(f"{API}/announcements/{ids[0]}", {"body": ""}, format="json")
    assert bad.status_code == 422  # BR-DEPT-003 re-validated on edit
    assert act("hod").post(f"{API}/announcements/{ids[1]}/hide").json()["status"] == "hidden"
    assert act("hod").delete(f"{API}/announcements/{ids[2]}").status_code == 204
    assert Announcement.objects.get(pk=ids[2]).status == "deleted"  # Q7: kept for audit
    visible = {a["id"] for a in act("student").get(f"{API}/announcements").json()["results"]}
    assert visible == {ids[0]}


# -- stock -------------------------------------------------------------------------
def test_uc_dept_019_dept_admin_inserts_stock_and_it_is_logged(world, act):
    # UC-DEPT-019; AFR-DEPT-007, AFR-DEPT-008, AFR-DEPT-014, BR-DEPT-016, CFR-DEPT-004
    item_id = _item(act, qty=10)
    r = act("admin").post(
        f"{API}/inventory-items/{item_id}/receipts", {"quantity": 5}, format="json"
    )
    assert r.status_code == 201 and r.json()["current_quantity"] == 15
    kinds = list(StockMovement.objects.filter(item_id=item_id).values_list("kind", "quantity"))
    assert sorted(kinds) == [("receipt", 5), ("receipt", 10)]
    listed = act("admin").get(f"{API}/inventory-items").json()["results"]
    assert listed[0]["current_quantity"] == 15


def test_uc_dept_019_alternate_invalid_stock_data_changes_nothing(world, act):
    # UC-DEPT-019 alternate flow
    item_id = _item(act, qty=3)
    r = act("admin").post(
        f"{API}/inventory-items/{item_id}/receipts", {"quantity": 0}, format="json"
    )
    assert r.status_code == 400  # refused with validation feedback
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 3
    assert StockMovement.objects.count() == 1


def test_uc_dept_004_005_006_stock_requested_approved_issued(world, act):
    # UC-DEPT-004, UC-DEPT-005, UC-DEPT-006; BW-DEPT-01, CW-DEPT-01; BR-DEPT-005, BR-DEPT-006, BR-DEPT-007, BR-DEPT-015, BR-DEPT-016; AFR-DEPT-009, AFR-DEPT-010, AFR-DEPT-011, AFR-DEPT-012, AFR-DEPT-013, AFR-DEPT-015, AFR-DEPT-041, AFR-DEPT-042, AFR-DEPT-043; CFR-DEPT-005
    item_id = _item(act, qty=10)
    r = act("faculty").post(
        f"{API}/stock-requests", {"item": item_id, "quantity": 4}, format="json"
    )
    assert r.status_code == 201 and r.json()["status"] == "pending_hod"
    req_id = r.json()["id"]
    assert _topic("stock_request.created") == {uid("admin")}
    assert _topic("stock_request.pending_hod") == {uid("hod")}

    r = act("hod").post(f"{API}/stock-requests/{req_id}/decide", {"approve": True}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert not _topic("stock_request.issued")  # AFR-DEPT-043: not on intermediate approval

    r = act("admin").post(f"{API}/stock-requests/{req_id}/issue")
    assert r.status_code == 200 and r.json()["status"] == "issued"
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 6
    issue = StockMovement.objects.get(stock_request_id=req_id)
    assert issue.kind == "issue" and issue.quantity == 4 and issue.actor_id == uid("admin")
    assert _topic("stock_request.issued") == {uid("faculty")}


def test_uc_dept_005_rejected_outcome_notifies_faculty(world, act):
    # UC-DEPT-005 rejected alternate; BW-DEPT-02; AFR-DEPT-043
    item_id = _item(act)
    req_id = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 2}, format="json")
        .json()["id"]
    )
    r = act("hod").post(
        f"{API}/stock-requests/{req_id}/decide",
        {"approve": False, "reason": "No budget"},
        format="json",
    )
    assert r.json()["status"] == "rejected" and r.json()["reason"] == "No budget"
    assert _topic("stock_request.rejected") == {uid("faculty")}
    assert act("admin").post(f"{API}/stock-requests/{req_id}/issue").status_code == 409
    assert InventoryItem.objects.get(pk=item_id).current_quantity == 10


def test_uc_dept_004_alternate_insufficient_stock_is_not_advanced(world, act):
    # UC-DEPT-004 alternate flow; BR-DEPT-015, AFR-DEPT-010
    item_id = _item(act, qty=3)
    r = act("faculty").post(
        f"{API}/stock-requests", {"item": item_id, "quantity": 4}, format="json"
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "insufficient_stock"
    assert not StockRequest.objects.exists()
    assert not DepartmentNotification.objects.exists()


def test_uc_dept_011_faculty_views_lab_resources_and_own_issued_history(world, act):
    # UC-DEPT-011; BR-DEPT-012, AFR-DEPT-016, AFR-DEPT-035, CFR-DEPT-006, CFR-DEPT-012 (Q12)
    item_id = _item(act)
    for who in ("faculty", "faculty2"):
        req = (
            act(who)
            .post(f"{API}/stock-requests", {"item": item_id, "quantity": 1}, format="json")
            .json()["id"]
        )
        act("hod").post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
        act("admin").post(f"{API}/stock-requests/{req}/issue")
    act("admin").post(f"{API}/lab-resources", {"name": "IoT Lab", "capacity": 30}, format="json")
    mine = act("faculty").get(f"{API}/stock-requests?status=issued").json()["results"]
    assert [r["requester_id"] for r in mine] == [uid("faculty")]
    labs = act("faculty").get(f"{API}/lab-resources").json()["results"]
    assert [lab["name"] for lab in labs] == ["IoT Lab"]


def test_uc_dept_011_alternate_empty_views(world, act):
    # UC-DEPT-011 alternate flow: empty state
    assert act("faculty").get(f"{API}/lab-resources").json()["results"] == []
    assert act("faculty").get(f"{API}/stock-requests?status=issued").json()["results"] == []


# -- feedback ----------------------------------------------------------------------
def _feedback(act, who="student"):
    r = act(who).post(
        f"{API}/feedback", {"subject": "Projector", "body": "Broken in L-104"}, format="json"
    )
    assert r.status_code == 201, r.content
    return r.json()["id"]


def test_uc_dept_007_student_submits_confidential_feedback(world, act):
    # UC-DEPT-007; BR-DEPT-008, BR-DEPT-017, AFR-DEPT-017, AFR-DEPT-018, AFR-DEPT-044, CFR-DEPT-007
    fb_id = _feedback(act)
    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "new" and fb.submitter_id == uid("student")
    assert _topic("feedback.created") == {uid("admin")}
    assert act("faculty").get(f"{API}/feedback/{fb_id}").status_code == 404


def test_uc_dept_007_exception_failed_submission_records_nothing(world, act):
    # UC-DEPT-007 exception flow: a refused submission leaves no record
    r = act("faculty").post(f"{API}/feedback", {"subject": "", "body": ""}, format="json")
    assert r.status_code == 422 and not Feedback.objects.exists()


def test_uc_dept_008_dept_admin_reviews_then_resolves(world, act):
    # UC-DEPT-008 main flow; BW-DEPT-03, CW-DEPT-02; BR-DEPT-009, BR-DEPT-018; AFR-DEPT-019, AFR-DEPT-020, AFR-DEPT-022, AFR-DEPT-045; CFR-DEPT-008
    fb_id = _feedback(act)
    r = act("admin").post(
        f"{API}/feedback/{fb_id}/review", {"category": "facilities"}, format="json"
    )
    assert r.json()["status"] == "under_review" and r.json()["category"] == "facilities"
    r = act("admin").post(
        f"{API}/feedback/{fb_id}/dispose", {"outcome": "resolved", "note": "Fixed"}, format="json"
    )
    assert r.json()["status"] == "resolved"
    assert _topic("feedback.disposed") == {uid("student")}
    assert act("student").get(f"{API}/feedback/{fb_id}").json()["resolution_note"] == "Fixed"


def test_uc_dept_008_alternate_simple_issue_closed_during_initial_review(world, act):
    # UC-DEPT-008 alternate flow; AFR-DEPT-021; category optional (Q11, AFR-DEPT-020)
    fb_id = _feedback(act)
    r = act("admin").post(
        f"{API}/feedback/{fb_id}/review", {"disposition": "closed"}, format="json"
    )
    assert r.json()["status"] == "closed" and r.json()["category"] == ""
    fb = Feedback.objects.get(pk=fb_id)
    assert fb.reviewed_by == uid("admin") and fb.disposed_by == uid("admin")


def test_uc_dept_008_alternate_reviewed_feedback_stays_open_for_hod(world, act):
    # UC-DEPT-008 alternate flow: non-terminal after review, then UC-DEPT-014
    fb_id = _feedback(act)
    act("admin").post(f"{API}/feedback/{fb_id}/review", {}, format="json")
    assert act("hod").get(f"{API}/feedback/{fb_id}").json()["status"] == "under_review"


def test_uc_dept_014_hod_oversight_note_and_closure(world, act):
    # UC-DEPT-014 main + alternate; BW-DEPT-04; AFR-DEPT-023, BR-DEPT-018
    fb_id = _feedback(act, "faculty")
    assert act("hod").get(f"{API}/feedback/{fb_id}").status_code == 404  # before initial review
    act("admin").post(f"{API}/feedback/{fb_id}/review", {"category": "academic"}, format="json")
    note = act("hod").post(
        f"{API}/feedback/{fb_id}/notes", {"body": "Spoke to the lab in-charge."}, format="json"
    )
    assert note.status_code == 201
    assert (
        act("hod").get(f"{API}/feedback/{fb_id}").json()["status"] == "under_review"
    )  # alternate: unchanged
    r = act("hod").post(f"{API}/feedback/{fb_id}/dispose", {"outcome": "closed"}, format="json")
    assert r.json()["status"] == "closed" and len(r.json()["notes"]) == 1
    assert _topic("feedback.disposed") == {uid("faculty")}


# -- timetable, labs, academics ------------------------------------------------------
SLOT = {
    "kind": "class",
    "programme": "B.Tech",
    "batch_year": 2024,
    "course_code": "CS201",
    "day_of_week": 0,
    "starts_at": "09:00",
    "ends_at": "10:00",
    "room": "L-104",
}


def test_uc_dept_009_dept_admin_uploads_and_modifies_timetable(world, act):
    # UC-DEPT-009 main flow; BR-DEPT-010, AFR-DEPT-029, AFR-DEPT-030, AFR-DEPT-031, CFR-DEPT-011
    r = act("admin").post(
        f"{API}/timetable-slots",
        {"slots": [SLOT, {**SLOT, "starts_at": "10:00", "ends_at": "11:00"}]},
        format="json",
    )
    assert r.status_code == 201 and len(r.json()) == 2
    slot_id = r.json()[0]["id"]
    r = act("admin").patch(f"{API}/timetable-slots/{slot_id}", {"room": "L-105"}, format="json")
    assert r.status_code == 200 and r.json()["room"] == "L-105"


def test_uc_dept_009_alternate_conflict_blocks_save(world, act):
    # UC-DEPT-009 alternate flow; BR-DEPT-010 (Q6: same room, overlapping time)
    act("admin").post(f"{API}/timetable-slots", {"slots": [SLOT]}, format="json")
    clash = {
        **SLOT,
        "programme": "M.Tech",
        "batch_year": 2025,
        "starts_at": "09:30",
        "ends_at": "10:30",
    }
    r = act("admin").post(f"{API}/timetable-slots", {"slots": [clash]}, format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "timetable_conflict"
    assert r.json()["error"]["details"]
    assert TimetableSlot.objects.count() == 1


def test_uc_dept_018_student_sees_programme_info_and_own_timetable(world, act):
    # UC-DEPT-018; AFR-DEPT-036, AFR-DEPT-037, CFR-DEPT-013 (Q9)
    act("admin").post(
        f"{API}/timetable-slots",
        {"slots": [SLOT, {**SLOT, "batch_year": 2023, "room": "L-200"}]},
        format="json",
    )
    client = act("student")
    rows = client.get(f"{API}/timetable-slots").json()
    assert [s["batch_year"] for s in rows] == [2024]
    detail = client.get(f"{API}/departments/CSE").json()
    assert detail["code"] == "CSE" and "programmes" in detail


def test_uc_dept_018_alternate_nothing_published_gives_empty(world, act):
    # UC-DEPT-018 alternate flow
    assert act("student").get(f"{API}/timetable-slots").json() == []


def test_uc_dept_017_dept_admin_updates_lab_profile(world, act):
    # UC-DEPT-017 main + alternate; AFR-DEPT-034, CFR-DEPT-012
    lab = act("admin").post(
        f"{API}/lab-resources", {"name": "VLSI Lab", "equipment": "FPGA x8"}, format="json"
    )
    assert lab.status_code == 201
    r = act("admin").patch(
        f"{API}/lab-resources/{lab.json()['id']}", {"status": "maintenance"}, format="json"
    )
    assert r.json()["status"] == "maintenance"
    assert (
        act("admin")
        .patch(f"{API}/lab-resources/{lab.json()['id']}", {"name": ""}, format="json")
        .status_code
        == 422
    )


# -- department details -----------------------------------------------------------------
def test_uc_dept_010_general_details_saved_directly(world, act):
    # UC-DEPT-010 general branch; AFR-DEPT-038, CFR-DEPT-014
    r = act("admin").patch(
        f"{API}/departments/CSE", {"contact_email": "cse@example.test"}, format="json"
    )
    assert r.status_code == 200 and r.json()["contact_email"] == "cse@example.test"


def test_uc_dept_010_alternate_validation_failure_saves_nothing(world, act):
    # UC-DEPT-010 alternate flow
    r = act("admin").patch(
        f"{API}/departments/CSE", {"contact_email": "not-an-email"}, format="json"
    )
    assert r.status_code == 400
    assert Department.objects.get(code="CSE").contact_email == ""


def test_uc_dept_010_012_official_change_approved_becomes_effective(world, act):
    # UC-DEPT-010 official branch, UC-DEPT-012; BW-DEPT-05, CW-DEPT-03; BR-DEPT-011, BR-DEPT-013; AFR-DEPT-039, AFR-DEPT-040, CFR-DEPT-015
    r = act("admin").post(
        f"{API}/official-changes", {"field": "name", "value": "Dept. of CSE"}, format="json"
    )
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert (
        Department.objects.get(code="CSE").name == "Computer Science and Engineering"
    )  # not published yet
    r = act("hod").post(
        f"{API}/official-changes/{r.json()['id']}/decide", {"approve": True}, format="json"
    )
    assert r.json()["status"] == "approved"
    assert Department.objects.get(code="CSE").name == "Dept. of CSE"


def test_uc_dept_012_rejected_official_change_keeps_current_data(world, act):
    # UC-DEPT-012 alternate; BW-DEPT-06
    cid = (
        act("admin")
        .post(f"{API}/official-changes", {"field": "core_policies", "value": "New"}, format="json")
        .json()["id"]
    )
    r = act("hod").post(
        f"{API}/official-changes/{cid}/decide",
        {"approve": False, "reason": "Discuss"},
        format="json",
    )
    assert r.json()["status"] == "rejected"
    assert Department.objects.get(code="CSE").core_policies == ""
    assert OfficialChange.objects.get(pk=cid).decided_by == uid("hod")


# -- profiles ----------------------------------------------------------------------------
def test_uc_dept_016_dept_admin_manages_profiles(world, act):
    # UC-DEPT-016 main + alternate; AFR-DEPT-024, CFR-DEPT-009 (Q8)
    r = act("admin").post(
        f"{API}/profiles",
        {"kind": "faculty", "user_id": uid("faculty"), "office": "C-210"},
        format="json",
    )
    assert r.status_code == 201 and r.json()["tier"] == "full"
    alum = act("admin").post(
        f"{API}/profiles",
        {"kind": "alumni", "display_name": "B. Sen", "graduation_year": 2019},
        format="json",
    )
    assert alum.status_code == 201
    r = act("admin").patch(
        f"{API}/profiles/{alum.json()['id']}", {"is_active": False}, format="json"
    )
    assert r.json()["is_active"] is False
    bad = act("admin").post(
        f"{API}/profiles", {"kind": "student", "user_id": uid("ece_student")}, format="json"
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "not_in_department"
    assert ProfileRecord.objects.count() == 2


def test_uc_dept_015_profile_tiers_by_viewer(world, act):
    # UC-DEPT-015 main + alternates; BR-DEPT-019, AFR-DEPT-025, AFR-DEPT-026, AFR-DEPT-027, AFR-DEPT-028, CFR-DEPT-010 (Q2, Q8)
    for body in (
        {"kind": "faculty", "user_id": uid("faculty"), "office": "C-210"},
        {"kind": "student", "user_id": uid("student2")},
        {"kind": "alumni", "display_name": "B. Sen", "current_position": "Engineer"},
    ):
        act("admin").post(f"{API}/profiles", body, format="json")
    as_student = {p["kind"]: p for p in act("student").get(f"{API}/profiles").json()["results"]}
    assert set(as_student) == {"faculty", "student"}
    assert set(as_student["faculty"]) == {
        "tier",
        "id",
        "kind",
        "display_name",
        "programme",
        "department",
    }
    as_faculty = {p["kind"]: p for p in act("faculty2").get(f"{API}/profiles").json()["results"]}
    assert (
        as_faculty["alumni"]["tier"] == "limited"
        and as_faculty["alumni"]["current_position"] == "Engineer"
    )
    assert as_faculty["student"]["tier"] == "basic"  # Q2: no course roster, never detailed
    as_hod = {p["kind"]: p for p in act("hod").get(f"{API}/profiles").json()["results"]}
    assert as_hod["student"]["tier"] == "full" and as_hod["student"]["batch_year"] == 2023
    for row in as_hod.values():
        assert not {"date_of_birth", "phone", "address", "category", "gender"} & set(row)


# -- role tenures ---------------------------------------------------------------------------
def test_uc_dept_020_022_hod_reassignment_takes_effect_and_headship_follows(world, act):
    # UC-DEPT-020, UC-DEPT-022; BW-DEPT-07, CW-DEPT-04; BR-DEPT-021, BR-DEPT-022, BR-DEPT-023, BR-DEPT-024; AFR-DEPT-047, AFR-DEPT-048, AFR-DEPT-049, AFR-DEPT-050, AFR-DEPT-051, AFR-DEPT-053; CFR-DEPT-016
    start = timezone.now() + timedelta(minutes=1)
    r = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "hod",
            "user_id": uid("next_hod"),
            "valid_from": start.isoformat(),
            "valid_to": (start + timedelta(days=700)).isoformat(),
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    outgoing = RoleTenure.objects.get(user_id=uid("hod"), role="hod")
    assert outgoing.valid_to == start  # no gap, no overlap

    later = start + timedelta(seconds=1)
    assert role_service.apply_transitions(now=later) == 1
    assert _topic("role.effective") == {uid("next_hod")}
    from modules.department.selectors.actors import current_holders

    assert current_holders([world["CSE"].pk], "hod", now=later) == {
        world["CSE"].pk: uid("next_hod")
    }


def test_uc_dept_022_outgoing_holder_loses_access_immediately(world, act):
    # UC-DEPT-022; BR-DEPT-024, AFR-DEPT-049, AFR-DEPT-050
    item_id = _item(act)
    req = (
        act("faculty")
        .post(f"{API}/stock-requests", {"item": item_id, "quantity": 1}, format="json")
        .json()["id"]
    )
    RoleTenure.objects.filter(user_id=uid("hod")).update(
        valid_to=timezone.now() - timedelta(seconds=1)
    )
    RoleTenure.objects.create(
        department=world["CSE"],
        role="hod",
        user_id=uid("next_hod"),
        valid_from=timezone.now() - timedelta(seconds=1),
        valid_to=timezone.now() + timedelta(days=30),
        assigned_by=uid("central"),
    )
    assert (
        act("hod")
        .post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
        .status_code
        == 404
    )
    assert (
        act("next_hod")
        .post(f"{API}/stock-requests/{req}/decide", {"approve": True}, format="json")
        .status_code
        == 200
    )


def test_uc_dept_020_dept_admin_reassignment_bw_dept_08(world, act):
    # BW-DEPT-08, AFR-DEPT-052: the Dept_Admin path, and a change to an end date
    start = timezone.now() + timedelta(minutes=1)
    r = act("central").post(
        f"{API}/role-assignments",
        {
            "department": "CSE",
            "role": "dept_admin",
            "user_id": uid("central"),
            "valid_from": start.isoformat(),
            "valid_to": (start + timedelta(days=30)).isoformat(),
        },
        format="json",
    )
    assert r.status_code == 201
    extend = act("central").patch(
        f"{API}/role-assignments/{r.json()['id']}",
        {"valid_to": (start + timedelta(days=60)).isoformat()},
        format="json",
    )
    assert extend.status_code == 200
    rows = RoleTenure.objects.filter(department=world["CSE"], role="dept_admin").order_by(
        "valid_from"
    )
    assert [t.user_id for t in rows] == [uid("admin"), uid("central")]
    assert rows[0].valid_to == rows[1].valid_from


def test_uc_dept_020_alternate_cardinality_violation_is_blocked(world, act):
    # UC-DEPT-020 alternate flow; BR-DEPT-022
    start = timezone.now() + timedelta(days=10)
    body = {
        "department": "ECE",
        "role": "hod",
        "user_id": uid("faculty2"),
        "valid_from": start.isoformat(),
        "valid_to": (start + timedelta(days=30)).isoformat(),
    }
    assert act("central").post(f"{API}/role-assignments", body, format="json").status_code == 201
    inside = {
        **body,
        "user_id": uid("faculty"),
        "valid_from": (start - timedelta(days=5)).isoformat(),
        "valid_to": (start + timedelta(days=5)).isoformat(),
    }
    r = act("central").post(f"{API}/role-assignments", inside, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "tenure_overlap"
