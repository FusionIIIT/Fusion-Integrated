import datetime as dt

import pytest

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    LeaveApplication,
    NoDuesCase,
    NoDuesResult,
    Notification,
    SeminarSchedule,
)
from modules.oap.tests.spec.conftest import BASE_URL

pytestmark = pytest.mark.django_db
SAMPLE_DRIVE_URL = "https://drive.google.com/file/d/1234567890abcdef1234/view"


def test_wf_001_leave_approved_basis_workflow(stub_iam, spec_login):
    """TEST-WF-001: BW-OAP-01 normal-path.
    Exercise basis workflow BW-OAP-01: Leave Application - Approved.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r_sub = student.post(
        f"{BASE_URL}/leave-applications",
        {
            "reason": "Conference",
            "from_date": "2026-12-01",
            "to_date": "2026-12-03",
            "supporting_document_link": SAMPLE_DRIVE_URL,
        },
        format="json",
    )
    assert r_sub.status_code == 201
    lid = r_sub.json()["id"]

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r_dec = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "approved"
    assert LeaveApplication.objects.get(pk=lid).status == "approved"
    assert Notification.objects.filter(recipient_user_id=1001, channel="email").exists()


def test_wf_002_leave_rejected_basis_workflow(stub_iam, spec_login):
    """TEST-WF-002: BW-OAP-02 rejection-path.
    Exercise basis workflow BW-OAP-02: Leave Application - Rejected.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r_sub = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Vacation", "from_date": "2026-12-01", "to_date": "2026-12-03"},
        format="json",
    )
    assert r_sub.status_code == 201
    lid = r_sub.json()["id"]

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r_dec = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "reject"}, format="json")
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "rejected"
    assert LeaveApplication.objects.get(pk=lid).status == "rejected"


def test_wf_003_leave_composite_decision_branching(stub_iam, spec_login):
    """TEST-WF-003: CW-OAP-01 composite-decision-branching.
    Exercise composite workflow CW-OAP-01: Leave Application Decision branching.
    """
    s1 = spec_login(stub_iam, 1001, ["student"], "student")
    lid1 = s1.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Leave 1", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    s2 = spec_login(stub_iam, 1002, ["student"], "student")
    lid2 = s2.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Leave 2", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r1 = hod.post(f"{BASE_URL}/leave-applications/{lid1}/decision", {"outcome": "approve"}, format="json")
    assert r1.status_code == 200 and r1.json()["status"] == "approved"

    r2 = hod.post(f"{BASE_URL}/leave-applications/{lid2}/decision", {"outcome": "reject"}, format="json")
    assert r2.status_code == 200 and r2.json()["status"] == "rejected"


def test_wf_004_bonafide_approved_basis_workflow(stub_iam, spec_login):
    """TEST-WF-004: BW-OAP-03 normal-path.
    Exercise basis workflow BW-OAP-03: Bonafide Request - Approved.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Passport"}, format="json").json()["id"]

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    v_resp = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    assert v_resp.status_code == 200
    d_resp = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert d_resp.status_code == 200
    assert d_resp.json()["status"] == "approved"

    c_resp = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert c_resp.status_code == 200
    assert BonafideRequest.objects.get(pk=bid).status == "approved"


def test_wf_005_bonafide_rejected_basis_workflow(stub_iam, spec_login):
    """TEST-WF-005: BW-OAP-04 rejection-path.
    Exercise basis workflow BW-OAP-04: Bonafide Request - Rejected.
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

    c_resp = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert c_resp.status_code in (400, 403, 404, 409, 422)


def test_wf_006_bonafide_composite_decision_branching(stub_iam, spec_login):
    """TEST-WF-006: CW-OAP-02 composite-decision-branching.
    Exercise composite workflow CW-OAP-02: Bonafide Request Decision branching.
    """
    s1 = spec_login(stub_iam, 1001, ["student"], "student")
    bid1 = s1.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Req 1"}, format="json").json()["id"]
    s2 = spec_login(stub_iam, 1002, ["student"], "student")
    bid2 = s2.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Req 2"}, format="json").json()["id"]

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid1}/verify")
    aa.post(f"{BASE_URL}/bonafide-requests/{bid1}/decision", {"outcome": "approve"}, format="json")
    assert s1.get(f"{BASE_URL}/bonafide-requests/{bid1}/certificate").status_code == 200

    aa.post(f"{BASE_URL}/bonafide-requests/{bid2}/verify")
    aa.post(f"{BASE_URL}/bonafide-requests/{bid2}/decision", {"outcome": "reject"}, format="json")
    assert s2.get(f"{BASE_URL}/bonafide-requests/{bid2}/certificate").status_code in (400, 403, 404, 409, 422)


def test_wf_007_nodues_cleared_basis_workflow(stub_iam, spec_login):
    """TEST-WF-007: BW-OAP-05 normal-path.
    Exercise basis workflow BW-OAP-05: No-Dues Clearance - Cleared.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)

    NoDuesResult.objects.filter(case=case).update(result="clear")

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r_fin = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r_fin.status_code == 200
    assert r_fin.json()["finalized"] is True

    r_cert = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}/certificate")
    assert r_cert.status_code == 200


def test_wf_008_nodues_outstanding_basis_workflow(stub_iam, spec_login):
    """TEST-WF-008: BW-OAP-06 dues-outstanding-path.
    Exercise basis workflow BW-OAP-06: No-Dues Clearance - Dues Outstanding.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)

    NoDuesResult.objects.filter(case=case).exclude(domain="library").update(result="clear")
    NoDuesResult.objects.filter(case=case, domain="library").update(result="outstanding")

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r_fin = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r_fin.status_code in (400, 409, 422)
    assert not NoDuesCase.objects.get(pk=case.pk).finalized


def test_wf_009_nodues_composite_branching(stub_iam, spec_login):
    """TEST-WF-009: CW-OAP-03 composite-branching.
    Exercise composite workflow CW-OAP-03: No-Dues Clearance branching.
    """
    s1 = spec_login(stub_iam, 1001, ["student"], "student")
    s1.post(f"{BASE_URL}/no-dues-cases")
    c1 = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=c1).update(result="clear")

    s2 = spec_login(stub_iam, 1002, ["student"], "student")
    s2.post(f"{BASE_URL}/no-dues-cases")
    c2 = NoDuesCase.objects.get(user_id=1002)
    NoDuesResult.objects.filter(case=c2).exclude(domain="hostel").update(result="clear")
    NoDuesResult.objects.filter(case=c2, domain="hostel").update(result="outstanding")

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    assert aa.post(f"{BASE_URL}/no-dues-cases/{c1.pk}/finalize").status_code == 200
    assert aa.post(f"{BASE_URL}/no-dues-cases/{c2.pk}/finalize").status_code in (400, 409, 422)


def test_wf_010_assistantship_approved_processed_basis_workflow(stub_iam, spec_login, spec_assign):
    """TEST-WF-010: BW-OAP-07 normal-path.
    Exercise basis workflow BW-OAP-07: Assistantship Claim - Approved and Processed.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]

    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    assert ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json").status_code == 200
    assert ta.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json").status_code == 200

    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    assert da.post(f"{BASE_URL}/assistantship-claims/{cid}/forward").status_code == 200

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    assert hod.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "approve"}, format="json").status_code == 200

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r_stipend = aa.post(f"{BASE_URL}/assistantship-claims/{cid}/stipend")
    assert r_stipend.status_code == 200
    assert r_stipend.json()["status"] == "stipend_processed"
    assert AssistantshipClaim.objects.get(pk=cid).status == "stipend_processed"


def test_wf_011_assistantship_rejected_basis_workflow(stub_iam, spec_login, spec_assign):
    """TEST-WF-011: BW-OAP-08 rejection-path.
    Exercise basis workflow BW-OAP-08: Assistantship Claim - Rejected by HoD.
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
    r_rej = hod.post(f"{BASE_URL}/assistantship-claims/{cid}/decision", {"outcome": "reject"}, format="json")
    assert r_rej.status_code == 200
    assert r_rej.json()["status"] == "rejected"

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r_stipend = aa.post(f"{BASE_URL}/assistantship-claims/{cid}/stipend")
    assert r_stipend.status_code in (400, 404, 409, 422)


def test_wf_012_assistantship_composite_branching(stub_iam, spec_login, spec_assign):
    """TEST-WF-012: CW-OAP-04 composite-branching.
    Exercise composite workflow CW-OAP-04: Assistantship Claim Processing branching.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    spec_assign(stub_iam, 1002, 5001, 5002)
    p1 = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    c1 = p1.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    p2 = spec_login(stub_iam, 1002, ["PG Student"], "PG Student")
    c2 = p2.post(f"{BASE_URL}/assistantship-claims").json()["id"]

    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    for c in (c1, c2):
        ts.post(f"{BASE_URL}/assistantship-claims/{c}/verifications", {"role": "thesis"}, format="json")
        ta.post(f"{BASE_URL}/assistantship-claims/{c}/verifications", {"role": "ta"}, format="json")

    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    da.post(f"{BASE_URL}/assistantship-claims/{c1}/forward")
    da.post(f"{BASE_URL}/assistantship-claims/{c2}/forward")

    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    hod.post(f"{BASE_URL}/assistantship-claims/{c1}/decision", {"outcome": "approve"}, format="json")
    hod.post(f"{BASE_URL}/assistantship-claims/{c2}/decision", {"outcome": "reject"}, format="json")

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    assert aa.post(f"{BASE_URL}/assistantship-claims/{c1}/stipend").status_code == 200
    assert aa.post(f"{BASE_URL}/assistantship-claims/{c2}/stipend").status_code in (400, 404, 409, 422)


def test_wf_013_graduate_seminar_scheduling_workflow(stub_iam, spec_login):
    """TEST-WF-013: BW-OAP-09 normal-path.
    Exercise basis workflow BW-OAP-09: Graduate Seminar Scheduling.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]

    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    r_sched = da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Seminar Room 1"},
        format="json",
    )
    assert r_sched.status_code == 201
    assert SeminarSchedule.objects.filter(request_id=sid).exists()
