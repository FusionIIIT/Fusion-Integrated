import datetime as dt

import pytest

from modules.oap.models import (
    NoDuesCase,
    NoDuesResult,
    Notification,
    SupervisorVerification,
)
from modules.oap.tests.spec.conftest import BASE_URL, extract_rows

pytestmark = pytest.mark.django_db


def test_br_001_role_based_access_permitted(stub_iam, spec_login):
    """TEST-BR-001: OA-BR-01 condition-permitted.
    Verify user with authorized role is permitted to perform OAP action.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Academic leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    assert r.status_code == 201


def test_br_002_role_based_access_prohibited(stub_iam, spec_login):
    """TEST-BR-002: OA-BR-01 condition-prohibited.
    Verify user with unauthorized role is refused access to protected OAP function.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Academic leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]

    faculty = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r = faculty.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)


def test_br_003_data_scope_isolation(stub_iam, spec_login):
    """TEST-BR-003: OA-BR-01 data-scope-isolation.
    Verify user cannot view or modify OAP records outside their assigned scope.
    """
    student_a = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student_a.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Private leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    student_b = spec_login(stub_iam, 2002, ["student"], "student")
    r = student_b.get(f"{BASE_URL}/leave-applications/{lid}")
    assert r.status_code in (404, 403)


def test_br_004_notification_channel_rule(stub_iam, spec_login):
    """TEST-BR-004: OA-BR-03 alert-and-email-channels.
    Verify required notifications are generated across alert and email channels, SMS excluded.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    channels = set(Notification.objects.filter(recipient_user_id=1001).values_list("channel", flat=True))
    assert "email" in channels or "alert" in channels
    assert "sms" not in channels


def test_br_005_leave_decision_hod_permitted(stub_iam, spec_login):
    """TEST-BR-005: OA-BR-11 condition-hod-permitted.
    Verify only HoD can approve or reject student leave applications.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_br_006_leave_decision_non_hod_prohibited(stub_iam, spec_login):
    """TEST-BR-006: OA-BR-11 condition-non-hod-prohibited.
    Verify non-HoD actor cannot decide student leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)


def test_br_007_bonafide_authority_acad_admin_permitted(stub_iam, spec_login):
    """TEST-BR-007: OA-BR-21 condition-acad-admin-permitted.
    Verify Academic Administrator is authorized to verify and decide bonafide requests.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Passport"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    v = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    assert v.status_code == 200
    d = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert d.status_code == 200
    assert d.json()["status"] == "approved"


def test_br_008_bonafide_authority_non_acad_admin_prohibited(stub_iam, spec_login):
    """TEST-BR-008: OA-BR-21 condition-non-acad-admin-prohibited.
    Verify non-Academic Administrator actor cannot verify or decide bonafide requests.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Passport"}, format="json").json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)


def test_br_009_bonafide_download_approved_permitted(stub_iam, spec_login):
    """TEST-BR-009: OA-BR-22 condition-approved-download-permitted.
    Verify bonafide certificate download is permitted when request is approved.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Bank"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert r.status_code == 200


def test_br_010_bonafide_download_non_approved_prohibited(stub_iam, spec_login):
    """TEST-BR-010: OA-BR-22 condition-non-approved-download-prohibited.
    Verify bonafide certificate download is prohibited when request is not approved.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Bank"}, format="json").json()["id"]
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert r.status_code in (400, 403, 404, 409, 422)


def test_br_011_nodues_own_domain_permitted(stub_iam, spec_login):
    """TEST-BR-011: OA-BR-31 condition-own-domain-permitted.
    Verify clearance authority records result for its own domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lib = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = lib.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["library"] == "clear"


def test_br_012_nodues_cross_domain_prohibited(stub_iam, spec_login):
    """TEST-BR-012: OA-BR-31 condition-cross-domain-prohibited.
    Verify clearance authority cannot record result for another domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lib = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = lib.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"domain": "mess", "result": "clear"}, format="json")
    assert r.json()["results"].get("mess") != "clear"


def test_br_013_nodues_independent_statuses(stub_iam, spec_login):
    """TEST-BR-013: OA-BR-32 condition-independent-statuses.
    Verify recording result for one domain leaves other six domain statuses unchanged.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    hostel = spec_login(stub_iam, 7002, ["Hostel Warden"], "Hostel Warden", kind="staff")
    hostel.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    res = {r.domain: r.result for r in NoDuesResult.objects.filter(case=case)}
    assert res["hostel"] == "clear"
    assert res["library"] == "pending"
    assert res["lab"] == "pending"


def test_br_014_nodues_finalization_all_clear_permitted(stub_iam, spec_login):
    """TEST-BR-014: OA-BR-33 condition-all-clear-permitted.
    Verify finalization permitted when all seven mandatory clearances are Clear.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).update(result="clear")
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r.status_code == 200
    assert r.json()["finalized"] is True


def test_br_015_nodues_finalization_dues_outstanding_prohibited(stub_iam, spec_login):
    """TEST-BR-015: OA-BR-33 condition-dues-outstanding-prohibited.
    Verify finalization prohibited when at least one authority records dues outstanding.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).update(result="clear")
    NoDuesResult.objects.filter(case=case, domain="library").update(result="outstanding")
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r.status_code in (400, 409, 422)


def test_br_016_nodues_finalization_pending_prohibited(stub_iam, spec_login):
    """TEST-BR-016: OA-BR-33 condition-pending-domain-prohibited.
    Verify finalization prohibited when at least one authority verification is pending.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).exclude(domain="library").update(result="clear")
    # library is still pending
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r.status_code in (400, 409, 422)


def test_br_017_nodues_certificate_finalized_download_permitted(stub_iam, spec_login):
    """TEST-BR-017: OA-BR-34 condition-finalized-download-permitted.
    Verify no-dues certificate download is permitted after finalization.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).update(result="clear")
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    r = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}/certificate")
    assert r.status_code == 200


def test_br_018_nodues_certificate_unfinalized_download_prohibited(stub_iam, spec_login):
    """TEST-BR-018: OA-BR-34 condition-unfinalized-download-prohibited.
    Verify no-dues certificate download is prohibited prior to finalization.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    r = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}/certificate")
    assert r.status_code in (400, 403, 404, 409, 422)


def test_br_019_assistantship_pg_permitted(stub_iam, spec_login, spec_assign):
    """TEST-BR-019: OA-BR-41 condition-pg-permitted.
    Verify PG student is permitted to submit assistantship claims.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/assistantship-claims")
    assert r.status_code == 201


def test_br_020_assistantship_non_pg_prohibited(stub_iam, spec_login, spec_assign):
    """TEST-BR-020: OA-BR-41 condition-non-pg-prohibited.
    Verify non-PG student is prohibited from submitting assistantship claims.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    ug = spec_login(stub_iam, 1001, ["student"], "student")
    r = ug.post(f"{BASE_URL}/assistantship-claims")
    assert r.status_code in (403, 401)


def test_br_021_assistantship_both_supervisors_required(stub_iam, spec_login, spec_assign):
    """TEST-BR-021: OA-BR-42 condition-both-supervisors-required.
    Verify assistantship claim requires verifications in both Thesis and TA supervisor roles.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")

    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward")
    assert r.status_code in (400, 409, 422)


def test_br_022_assistantship_supervisors_order_independent(stub_iam, spec_login, spec_assign):
    """TEST-BR-022: OA-BR-42 condition-order-independent.
    Verify dual supervisor verifications can be recorded in either order (TA before Thesis).
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    r1 = ta.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")
    assert r1.status_code == 200
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r2 = ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    assert r2.status_code == 200
    assert r2.json()["status"] == "awaiting_department_review"


def test_br_023_department_review_prerequisite(stub_iam, spec_login, spec_assign):
    """TEST-BR-023: OA-BR-43 condition-department-review-prerequisite.
    Verify Department Administrator review is prohibited if either supervisor verification is missing.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward")
    assert r.status_code in (400, 409, 422)


def test_br_024_hod_assistantship_decision_permitted(stub_iam, spec_login, spec_assign):
    """TEST-BR-024: OA-BR-44 condition-hod-permitted.
    Verify HoD is authorized to approve or reject assistantship claims.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    ta.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward")

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "approved_awaiting_stipend"


def test_br_025_hod_assistantship_decision_non_hod_prohibited(stub_iam, spec_login, spec_assign):
    """TEST-BR-025: OA-BR-44 condition-non-hod-prohibited.
    Verify non-HoD actor cannot approve or reject assistantship claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    ta.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward")

    unauth = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = unauth.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)


def test_br_026_stipend_processing_approved_permitted(stub_iam, spec_login, spec_assign):
    """TEST-BR-026: OA-BR-45 condition-approved-stipend-permitted.
    Verify stipend disbursement processing is permitted for HoD-approved claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    ta.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward")
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    hod.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json")

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/assistantship-claims/{cid}/stipend")
    assert r.status_code == 200
    assert r.json()["status"] == "stipend_processed"


def test_br_027_stipend_processing_unapproved_prohibited(stub_iam, spec_login, spec_assign):
    """TEST-BR-027: OA-BR-45 condition-unapproved-stipend-prohibited.
    Verify stipend disbursement processing is prohibited for claim that is not HoD-approved.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/assistantship-claims/{cid}/stipend")
    assert r.status_code in (400, 404, 409, 422)


def test_br_028_assistantship_progression_sequence(stub_iam, spec_login, spec_assign):
    """TEST-BR-028: OA-BR-46 progression-sequence-enforcement.
    Verify assistantship claim cannot bypass required stages in sequence.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (400, 404, 409, 422)


def test_br_029_department_assignment_recording_authority(stub_iam, spec_login):
    """TEST-BR-029: OA-BR-51 assignment-recording-authority.
    Verify Department Administrator records thesis supervisor and TA assignments.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r1 = da.post(
        f"{BASE_URL}/thesis-supervisor-assignments",
        {"student_user_id": 1001, "supervisor_user_id": 5001},
        format="json",
    )
    assert r1.status_code == 201
    r2 = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "CS101", "supervisor_user_id": 5001},
        format="json",
    )
    assert r2.status_code == 201


def test_br_030_dual_roles_same_faculty(stub_iam, spec_login, spec_assign):
    """TEST-BR-030: OA-BR-52 dual-roles-same-faculty.
    Verify same faculty member can hold both Thesis and TA supervisor roles with distinct verifications.
    """
    spec_assign(stub_iam, 1001, 5001, 5001)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    fac = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    fac.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    fac.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")

    verifications = SupervisorVerification.objects.filter(claim_id=cid)
    assert verifications.count() == 2
    roles = {v.role for v in verifications}
    assert roles == {"thesis", "ta"}


def test_br_031_pg_seminar_eligibility_permitted(stub_iam, spec_login):
    """TEST-BR-031: OA-BR-61 condition-pg-seminar-permitted.
    Verify PG student is permitted to request graduate seminar scheduling.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/seminar-requests")
    assert r.status_code == 201


def test_br_032_pg_seminar_eligibility_non_pg_prohibited(stub_iam, spec_login):
    """TEST-BR-032: OA-BR-61 condition-non-pg-seminar-prohibited.
    Verify UG student is prohibited from requesting graduate seminar scheduling.
    """
    ug = spec_login(stub_iam, 1001, ["student"], "student")
    r = ug.post(f"{BASE_URL}/seminar-requests")
    assert r.status_code in (403, 401)


def test_br_033_seminar_scheduling_authority(stub_iam, spec_login):
    """TEST-BR-033: OA-BR-62 seminar-scheduling-authority.
    Verify Department Administrator schedules and logs graduate seminars without separate approval stage.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    r = da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Room 101"},
        format="json",
    )
    assert r.status_code == 201


def test_br_034_seminar_visibility_scope(stub_iam, spec_login):
    """TEST-BR-034: OA-BR-63 seminar-visibility-scope.
    Verify graduate seminar schedules are visible to PG students and faculty.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Room 101"},
        format="json",
    )

    fac = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r_fac = fac.get(f"{BASE_URL}/seminar-schedules")
    assert r_fac.status_code == 200
    assert len(extract_rows(r_fac)) >= 1

    r_pg = pg.get(f"{BASE_URL}/seminar-schedules")
    assert r_pg.status_code == 200
    assert len(extract_rows(r_pg)) >= 1
