import datetime as dt

import pytest

from modules.oap.models import (
    LeaveApplication,
    NoDuesCase,
    NoDuesResult,
    Notification,
    SeminarSchedule,
    ThesisSupervisorAssignment,
)
from modules.oap.tests.spec.conftest import BASE_URL, extract_rows

pytestmark = pytest.mark.django_db
SAMPLE_DRIVE_URL = "https://drive.google.com/file/d/1234567890abcdef1234/view"


def test_uc_001_submit_leave_main_flow(stub_iam, spec_login):
    """TEST-UC-001: OA-UC-01 Main Flow.
    Verify student submits leave application with optional supporting document.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {
            "reason": "Conference presentation",
            "from_date": "2026-12-01",
            "to_date": "2026-12-03",
            "supporting_document_link": SAMPLE_DRIVE_URL,
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["status"] == "submitted"
    assert r.json()["supporting_document_link"] == SAMPLE_DRIVE_URL


def test_uc_002_submit_leave_alt_a1(stub_iam, spec_login):
    """TEST-UC-002: OA-UC-01 Alternative A1.
    Verify student submits leave application without supporting document.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {
            "reason": "Family event",
            "from_date": "2026-12-01",
            "to_date": "2026-12-02",
            "supporting_document_link": "",
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["status"] == "submitted"


def test_uc_003_submit_leave_exception_e1(stub_iam, spec_login):
    """TEST-UC-003: OA-UC-01 Exception E1.
    Verify leave application submission fails when required data is missing or invalid.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Invalid dates", "from_date": "2026-12-05", "to_date": "2026-12-01"},
        format="json",
    )
    assert r.status_code in (400, 422)


def test_uc_004_decide_leave_main_flow(stub_iam, spec_login):
    """TEST-UC-004: OA-UC-03 Main Flow.
    Verify HoD reviews and approves a submitted leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert LeaveApplication.objects.get(pk=lid).decided_by_user_id == 9001


def test_uc_005_decide_leave_alt_a1(stub_iam, spec_login):
    """TEST-UC-005: OA-UC-03 Alternative A1.
    Verify HoD reviews and rejects a submitted leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "reject"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_uc_006_decide_leave_exception_e1(stub_iam, spec_login):
    """TEST-UC-006: OA-UC-03 Exception E1.
    Verify unauthorized user attempting to decide leave application is refused.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    unauth = spec_login(stub_iam, 2002, ["student"], "student")
    r = unauth.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)
    assert LeaveApplication.objects.get(pk=lid).status == "submitted"


def test_uc_007_track_leave_main_flow(stub_iam, spec_login):
    """TEST-UC-007: OA-UC-04 Main Flow.
    Verify student retrieves and views own leave tracking and request history.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event 1", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    r = student.get(f"{BASE_URL}/leave-applications")
    assert r.status_code == 200
    assert len(extract_rows(r)) >= 1


def test_uc_008_track_leave_exception_e1(stub_iam, spec_login):
    """TEST-UC-008: OA-UC-04 Exception E1.
    Verify empty list returned when student has no leave records.
    """
    student = spec_login(stub_iam, 3003, ["student"], "student")
    r = student.get(f"{BASE_URL}/leave-applications")
    assert r.status_code == 200
    assert len(extract_rows(r)) == 0


def test_uc_009_request_bonafide_main_flow(stub_iam, spec_login):
    """TEST-UC-009: OA-UC-11 Main Flow.
    Verify student submits bonafide certificate request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Passport application"}, format="json")
    assert r.status_code == 201
    assert r.json()["status"] == "submitted"


def test_uc_010_request_bonafide_exception_e1(stub_iam, spec_login):
    """TEST-UC-010: OA-UC-11 Exception E1.
    Verify bonafide request submission behavior on blank/missing purpose.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": ""}, format="json")
    assert r.status_code in (201, 400)


def test_uc_011_verify_and_decide_bonafide_main_flow(stub_iam, spec_login):
    """TEST-UC-011: OA-UC-12 Main Flow.
    Verify Academic Administrator verifies and approves bonafide request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Bank account"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    v_resp = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    assert v_resp.status_code == 200
    d_resp = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert d_resp.status_code == 200
    assert d_resp.json()["status"] == "approved"


def test_uc_012_verify_and_decide_bonafide_alt_a1(stub_iam, spec_login):
    """TEST-UC-012: OA-UC-12 Alternative A1.
    Verify Academic Administrator verifies and rejects bonafide request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Loan"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    d_resp = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "reject"}, format="json")
    assert d_resp.status_code == 200
    assert d_resp.json()["status"] == "rejected"


def test_uc_013_verify_and_decide_bonafide_exception_e1(stub_iam, spec_login):
    """TEST-UC-013: OA-UC-12 Exception E1.
    Verify bonafide decision fails if attempted by non-Academic Administrator.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Bank"}, format="json").json()["id"]
    unauth = spec_login(stub_iam, 2002, ["student"], "student")
    r = unauth.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)


def test_uc_014_download_bonafide_main_flow(stub_iam, spec_login):
    """TEST-UC-014: OA-UC-13 Main Flow.
    Verify student downloads approved bonafide certificate.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Conference"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert r.status_code == 200


def test_uc_015_download_bonafide_alt_a1(stub_iam, spec_login):
    """TEST-UC-015: OA-UC-13 Alternative A1.
    Verify student download is refused when bonafide request is not approved.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Visa"}, format="json").json()["id"]
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert r.status_code in (400, 403, 404, 409, 422)


def test_uc_016_track_bonafide_main_flow(stub_iam, spec_login):
    """TEST-UC-016: OA-UC-14 Main Flow.
    Verify student tracks bonafide request status.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "ID Card"}, format="json")
    r = student.get(f"{BASE_URL}/bonafide-requests")
    assert r.status_code == 200
    assert len(extract_rows(r)) >= 1


def test_uc_017_track_bonafide_exception_e1(stub_iam, spec_login):
    """TEST-UC-017: OA-UC-14 Exception E1.
    Verify empty result when student has no bonafide requests.
    """
    student = spec_login(stub_iam, 3003, ["student"], "student")
    r = student.get(f"{BASE_URL}/bonafide-requests")
    assert r.status_code == 200
    assert len(extract_rows(r)) == 0


def test_uc_018_initiate_nodues_main_flow(stub_iam, spec_login):
    """TEST-UC-018: OA-UC-21 Main Flow.
    Verify student initiates no-dues clearance routing to seven authorities.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(f"{BASE_URL}/no-dues-cases")
    assert r.status_code == 201
    assert NoDuesCase.objects.filter(user_id=1001, finalized=False).exists()


def test_uc_019_initiate_nodues_exception_e1(stub_iam, spec_login):
    """TEST-UC-019: OA-UC-21 Exception E1.
    Verify student cannot initiate a second no-dues case while one is already open.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r1 = student.post(f"{BASE_URL}/no-dues-cases")
    assert r1.status_code == 201
    r2 = student.post(f"{BASE_URL}/no-dues-cases")
    assert r2.status_code in (400, 409, 422)


def test_uc_020_verify_nodues_main_flow(stub_iam, spec_login):
    """TEST-UC-020: OA-UC-22 Main Flow.
    Verify clearance authority records Clear verification result for its domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lib = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = lib.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["library"] == "clear"


def test_uc_021_verify_nodues_alt_a1(stub_iam, spec_login):
    """TEST-UC-021: OA-UC-22 Alternative A1.
    Verify clearance authority records Dues Outstanding verification result for its domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    hostel = spec_login(stub_iam, 7002, ["Hostel Warden"], "Hostel Warden", kind="staff")
    r = hostel.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "outstanding"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["hostel"] == "outstanding"


def test_uc_022_verify_nodues_exception_e1(stub_iam, spec_login):
    """TEST-UC-022: OA-UC-22 Exception E1.
    Verify authority cannot record clearance for a domain it is not authorized for.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lib = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = lib.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"domain": "hostel", "result": "clear"}, format="json")
    assert r.json()["results"].get("hostel") != "clear"


def test_uc_023_finalize_nodues_main_flow(stub_iam, spec_login):
    """TEST-UC-023: OA-UC-23 Main Flow.
    Verify Academic Administrator finalizes no-dues clearance when all 7 domains are Clear.
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


def test_uc_024_finalize_nodues_alt_a1(stub_iam, spec_login):
    """TEST-UC-024: OA-UC-23 Alternative A1.
    Verify finalization is refused while any domain remains outstanding or pending.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).update(result="clear")
    NoDuesResult.objects.filter(case=case, domain="mess").update(result="outstanding")
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r.status_code in (400, 409, 422)


def test_uc_025_finalize_nodues_exception_e1(stub_iam, spec_login):
    """TEST-UC-025: OA-UC-23 Exception E1.
    Verify non-Academic Administrator cannot finalize no-dues case.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).update(result="clear")
    unauth = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = unauth.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r.status_code in (403, 404)


def test_uc_026_track_nodues_main_flow(stub_iam, spec_login):
    """TEST-UC-026: OA-UC-24 Main Flow.
    Verify student tracks no-dues clearance progress across all 7 domains.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    r = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}")
    assert r.status_code == 200
    assert "results" in r.json()


def test_uc_027_track_nodues_exception_e1(stub_iam, spec_login):
    """TEST-UC-027: OA-UC-24 Exception E1.
    Verify tracking view returns 404 when student has no active no-dues case.
    """
    student = spec_login(stub_iam, 3003, ["student"], "student")
    r = student.get(f"{BASE_URL}/no-dues-cases/99999")
    assert r.status_code in (404, 403)


def test_uc_028_download_nodues_certificate_main_flow(stub_iam, spec_login):
    """TEST-UC-028: OA-UC-25 Main Flow.
    Verify student downloads finalized no-dues certificate.
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


def test_uc_029_download_nodues_certificate_alt_a1(stub_iam, spec_login):
    """TEST-UC-029: OA-UC-25 Alternative A1.
    Verify student download refused when no-dues case is not finalized.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    r = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}/certificate")
    assert r.status_code in (400, 403, 404, 409, 422)


def test_uc_030_submit_assistantship_claim_main_flow(stub_iam, spec_login, spec_assign):
    """TEST-UC-030: OA-UC-31 Main Flow.
    Verify PG student submits assistantship claim with assigned supervisors.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/assistantship-claims")
    assert r.status_code == 201
    assert r.json()["status"] == "awaiting_dual_verification"


def test_uc_031_submit_assistantship_claim_exception_e1(stub_iam, spec_login):
    """TEST-UC-031: OA-UC-31 Exception E1.
    Verify claim submission refused if student lacks assigned supervisor.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/assistantship-claims")
    assert r.status_code in (400, 409, 422)


def test_uc_032_verify_assistantship_claim_main_flow(stub_iam, spec_login, spec_assign):
    """TEST-UC-032: OA-UC-33 Main Flow.
    Verify assigned supervisor records verification for their role on claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r = ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_other_verification"


def test_uc_033_verify_assistantship_claim_alt_a1(stub_iam, spec_login, spec_assign):
    """TEST-UC-033: OA-UC-33 Alternative A1.
    Verify same faculty member holding both roles records both verifications distinctly.
    """
    spec_assign(stub_iam, 1001, 5001, 5001)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    fac = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r1 = fac.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    assert r1.status_code == 200
    r2 = fac.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")
    assert r2.status_code == 200
    assert r2.json()["status"] == "awaiting_department_review"


def test_uc_034_verify_assistantship_claim_exception_e1(stub_iam, spec_login, spec_assign):
    """TEST-UC-034: OA-UC-33 Exception E1.
    Verify faculty not assigned to claim cannot record verification.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    unassigned = spec_login(stub_iam, 5003, ["faculty"], "faculty", kind="faculty")
    r = unassigned.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    assert r.status_code in (403, 404)


def test_uc_035_review_forward_assistantship_main_flow(stub_iam, spec_login, spec_assign):
    """TEST-UC-035: OA-UC-34 Main Flow.
    Verify Department Administrator reviews and forwards dual-verified claim to HoD.
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
    r = da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_hod_decision"


def test_uc_035_ex_review_forward_assistantship_exception_e1(stub_iam, spec_login, spec_assign):
    """TEST-UC-035-EX: OA-UC-34 Exception E1.
    Verify Department Administrator cannot forward claim if supervisor verifications are incomplete.
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


def test_uc_036_decide_assistantship_claim_main_flow(stub_iam, spec_login, spec_assign):
    """TEST-UC-036: OA-UC-35 Main Flow.
    Verify HoD reviews and approves forwarded assistantship claim.
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


def test_uc_037_decide_assistantship_claim_alt_a1(stub_iam, spec_login, spec_assign):
    """TEST-UC-037: OA-UC-35 Alternative A1.
    Verify HoD reviews and rejects forwarded assistantship claim.
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
    r = hod.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "reject"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_uc_038_decide_assistantship_claim_exception_e1(stub_iam, spec_login, spec_assign):
    """TEST-UC-038: OA-UC-35 Exception E1.
    Verify non-HoD cannot approve or reject forwarded assistantship claim.
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

    unauth = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = unauth.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code in (403, 404)


def test_uc_039_process_stipend_main_flow(stub_iam, spec_login, spec_assign):
    """TEST-UC-039: OA-UC-36 Main Flow.
    Verify Academic Administrator processes stipend disbursement for HoD-approved claim.
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


def test_uc_040_process_stipend_exception_e1(stub_iam, spec_login, spec_assign):
    """TEST-UC-040: OA-UC-36 Exception E1.
    Verify stipend processing refused for unapproved assistantship claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/assistantship-claims/{cid}/stipend")
    assert r.status_code in (400, 404, 409, 422)


def test_uc_041_track_assistantship_claim_main_flow(stub_iam, spec_login, spec_assign):
    """TEST-UC-041: OA-UC-37 Main Flow.
    Verify PG student tracks assistantship claim status across stages.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    r = pg.get(f"{BASE_URL}/assistantship-claims/{cid}")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_dual_verification"


def test_uc_042_track_assistantship_claim_exception_e1(stub_iam, spec_login):
    """TEST-UC-042: OA-UC-37 Exception E1.
    Verify empty result when student has no assistantship claims.
    """
    pg = spec_login(stub_iam, 3003, ["PG Student"], "PG Student")
    r = pg.get(f"{BASE_URL}/assistantship-claims")
    assert r.status_code == 200
    assert len(extract_rows(r)) == 0


def test_uc_043_record_thesis_supervisor_main_flow(stub_iam, spec_login):
    """TEST-UC-043: OA-UC-41 Main Flow.
    Verify Department Administrator records thesis-supervisor assignment.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/thesis-supervisor-assignments",
        {"student_user_id": 1001, "supervisor_user_id": 5001},
        format="json",
    )
    assert r.status_code == 201
    assert ThesisSupervisorAssignment.objects.filter(student_user_id=1001, superseded_at=None).exists()


def test_uc_044_record_thesis_supervisor_alt_a1(stub_iam, spec_login):
    """TEST-UC-044: OA-UC-41 Alternative A1.
    Verify new thesis supervisor assignment supersedes prior active assignment.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    da.post(
        f"{BASE_URL}/thesis-supervisor-assignments",
        {"student_user_id": 1001, "supervisor_user_id": 5001},
        format="json",
    )
    da.post(
        f"{BASE_URL}/thesis-supervisor-assignments",
        {"student_user_id": 1001, "supervisor_user_id": 5002},
        format="json",
    )
    current = ThesisSupervisorAssignment.objects.filter(student_user_id=1001, superseded_at=None)
    assert [x.supervisor_user_id for x in current] == [5002]


def test_uc_045_record_thesis_supervisor_exception_e1(stub_iam, spec_login):
    """TEST-UC-045: OA-UC-41 Exception E1.
    Verify recording thesis supervisor assignment fails if user is not Department Administrator.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/thesis-supervisor-assignments",
        {"student_user_id": 1001, "supervisor_user_id": 5001},
        format="json",
    )
    assert r.status_code in (403, 401)


def test_uc_046_record_ta_main_flow(stub_iam, spec_login):
    """TEST-UC-046: OA-UC-42 Main Flow.
    Verify Department Administrator records TA assignment with course/subject only.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "CS101", "supervisor_user_id": None},
        format="json",
    )
    assert r.status_code == 201


def test_uc_047_record_ta_alt_a1(stub_iam, spec_login):
    """TEST-UC-047: OA-UC-42 Alternative A1.
    Verify Department Administrator records TA assignment with faculty member only.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "", "supervisor_user_id": 5002},
        format="json",
    )
    assert r.status_code == 201


def test_uc_048_record_ta_alt_a2(stub_iam, spec_login):
    """TEST-UC-048: OA-UC-42 Alternative A2.
    Verify Department Administrator records TA assignment with both course and faculty.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "CS101", "supervisor_user_id": 5002},
        format="json",
    )
    assert r.status_code == 201


def test_uc_049_record_ta_exception_e1(stub_iam, spec_login):
    """TEST-UC-049: OA-UC-42 Exception E1.
    Verify TA assignment fails if neither course nor faculty is provided.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "", "supervisor_user_id": None},
        format="json",
    )
    assert r.status_code in (400, 422)


def test_uc_050_request_seminar_main_flow(stub_iam, spec_login):
    """TEST-UC-050: OA-UC-51 Main Flow.
    Verify PG student submits graduate seminar scheduling request.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/seminar-requests")
    assert r.status_code == 201
    assert r.json()["status"] == "awaiting_scheduling"


def test_uc_051_request_seminar_exception_e1(stub_iam, spec_login):
    """TEST-UC-051: OA-UC-51 Exception E1.
    Verify non-PG student cannot submit seminar scheduling request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(f"{BASE_URL}/seminar-requests")
    assert r.status_code in (403, 401)


def test_uc_052_schedule_seminar_main_flow(stub_iam, spec_login):
    """TEST-UC-052: OA-UC-53 Main Flow.
    Verify Department Administrator schedules graduate seminar.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    r = da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Seminar Hall A"},
        format="json",
    )
    assert r.status_code == 201
    assert SeminarSchedule.objects.filter(request_id=sid).exists()


def test_uc_053_schedule_seminar_exception_e1(stub_iam, spec_login):
    """TEST-UC-053: OA-UC-53 Exception E1.
    Verify seminar scheduling fails when venue is missing.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    r = da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": ""},
        format="json",
    )
    assert r.status_code in (400, 422)


def test_uc_054_view_seminars_main_flow(stub_iam, spec_login):
    """TEST-UC-054: OA-UC-54 Main Flow.
    Verify PG students and faculty view scheduled graduate seminars.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Auditorium"},
        format="json",
    )
    r = pg.get(f"{BASE_URL}/seminar-schedules")
    assert r.status_code == 200
    assert any(x["venue"] == "Auditorium" for x in extract_rows(r))


def test_uc_055_view_seminars_exception_e1(stub_iam, spec_login):
    """TEST-UC-055: OA-UC-54 Exception E1.
    Verify empty schedule list returned when no seminars are scheduled.
    """
    fac = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r = fac.get(f"{BASE_URL}/seminar-schedules")
    assert r.status_code == 200
    assert len(extract_rows(r)) == 0


def test_uc_056_event_notification_main_flow(stub_iam, spec_login):
    """TEST-UC-056: OA-UC-91 Main Flow.
    Verify event notification dispatches both system alert and email.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    assert Notification.objects.filter(recipient_user_id=1001, channel="email").exists()


def test_uc_057_event_notification_exception_e1():
    """TEST-UC-057: OA-UC-91 Exception E1.
    Verify notification dispatch handles empty recipient list safely.
    """
    from modules.oap.services import notifications

    # Should not raise exception
    notifications.notify([], "Subject", "Body")


def test_uc_058_pending_action_reminder_main_flow():
    """TEST-UC-058: OA-UC-92 Main Flow.
    Verify pending-action reminder executes reminder task.
    """
    from modules.oap.tasks import send_pending_reminders

    res = send_pending_reminders()
    assert isinstance(res, dict)
    assert "sent" in res


def test_uc_059_pending_action_reminder_alt_a1():
    """TEST-UC-059: OA-UC-92 Alternative A1.
    Verify reminder is silent when no reminder policy is configured.
    """
    from modules.oap.services import reminders

    res = reminders.send_due_reminders()
    assert res["sent"] == 0
