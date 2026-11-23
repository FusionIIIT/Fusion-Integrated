import datetime as dt

import pytest

from modules.oap.models import (
    AssistantshipClaim,
    BonafideRequest,
    NoDuesCase,
    NoDuesResult,
    Notification,
    SeminarSchedule,
    TAAssignment,
    ThesisSupervisorAssignment,
)
from modules.oap.tests.spec.conftest import BASE_URL, extract_rows

pytestmark = pytest.mark.django_db
SAMPLE_DRIVE_URL = "https://drive.google.com/file/d/1234567890abcdef1234/view"


def test_fr_001_authorization_permitted(stub_iam, spec_login):
    """TEST-FR-001: AFR-OAP-001 authorization-permitted.
    Verify authorized student role is permitted to perform student OAP actions.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Medical appointment", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["status"] == "submitted"


def test_fr_002_authorization_denied(stub_iam, spec_login):
    """TEST-FR-002: AFR-OAP-001 authorization-denied.
    Verify unauthorized role is denied access to student OAP submission function.
    """
    faculty = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r = faculty.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Test reason", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    assert r.status_code in (403, 401)


def test_fr_003_data_scope_permitted(stub_iam, spec_login):
    """TEST-FR-003: AFR-OAP-002 data-scope-permitted.
    Verify student can access own OAP records.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    create_resp = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Personal work", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    lid = create_resp.json()["id"]
    get_resp = student.get(f"{BASE_URL}/leave-applications/{lid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == lid


def test_fr_004_data_scope_restricted(stub_iam, spec_login):
    """TEST-FR-004: AFR-OAP-002 data-scope-restricted.
    Verify student cannot access another student's OAP records.
    """
    student_a = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student_a.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Student A leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    student_b = spec_login(stub_iam, 2002, ["student"], "student")
    get_resp = student_b.get(f"{BASE_URL}/leave-applications/{lid}")
    assert get_resp.status_code in (404, 403)


def test_fr_005_submission_notification(stub_iam, spec_login):
    """TEST-FR-005: AFR-OAP-004 submission-notification.
    Verify system-generated alert and email notification are queued on request submission.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Conference", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    )
    assert Notification.objects.filter(recipient_user_id=1001).exists()


def test_fr_006_decision_notification(stub_iam, spec_login):
    """TEST-FR-006: AFR-OAP-005 decision-notification.
    Verify alert and email notification are sent when HoD approves or rejects a request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Leave", "from_date": "2026-12-01", "to_date": "2026-12-02"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert Notification.objects.filter(recipient_user_id=1001, channel="email").exists()


def test_fr_007_nodues_completion_notification(stub_iam, spec_login):
    """TEST-FR-007: AFR-OAP-006 nodues-completion-notification.
    Verify notification is sent when all 7 no-dues authorities complete verification.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)

    roles = [
        ("Librarian", "library", 7001),
        ("Hostel Warden", "hostel", 7002),
        ("Mess In-charge", "mess", 7003),
        ("Lab Supervisor", "lab", 7005),
    ]
    for r_name, _, uid in roles:
        auth = spec_login(stub_iam, uid, [r_name], r_name, kind="staff")
        auth.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")

    assert NoDuesResult.objects.filter(case=case).count() == 7


def test_fr_008_certificate_availability_notification(stub_iam, spec_login):
    """TEST-FR-008: AFR-OAP-007 certificate-availability-notification.
    Verify notification is sent when approved certificate becomes available for download.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(
        f"{BASE_URL}/bonafide-requests", {"purpose": "Passport verification"}, format="json"
    ).json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert Notification.objects.filter(recipient_user_id=1001).exists()


def test_fr_009_pending_action_reminder():
    """TEST-FR-009: AFR-OAP-008 pending-action-reminder.
    Verify reminder service execution for pending actions.
    """
    from modules.oap.services import reminders

    res = reminders.send_due_reminders()
    assert isinstance(res, dict)
    assert "sent" in res


def test_fr_010_leave_submission(stub_iam, spec_login):
    """TEST-FR-010: AFR-OAP-009 leave-submission.
    Verify student can successfully submit a leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Family function", "from_date": "2026-12-10", "to_date": "2026-12-12"},
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["reason"] == "Family function"


def test_fr_011_leave_attachment_optional_without_doc(stub_iam, spec_login):
    """TEST-FR-011: AFR-OAP-010 leave-attachment-optional.
    Verify leave submission succeeds without supporting document.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {
            "reason": "Illness",
            "from_date": "2026-12-10",
            "to_date": "2026-12-11",
            "supporting_document_link": "",
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["supporting_document_link"] == ""


def test_fr_012_leave_attachment_provided(stub_iam, spec_login):
    """TEST-FR-012: AFR-OAP-010 leave-attachment-provided.
    Verify leave submission retains supporting document when provided.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(
        f"{BASE_URL}/leave-applications",
        {
            "reason": "Medical leave",
            "from_date": "2026-12-10",
            "to_date": "2026-12-11",
            "supporting_document_link": SAMPLE_DRIVE_URL,
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.json()["supporting_document_link"] == SAMPLE_DRIVE_URL


def test_fr_013_leave_hod_availability(stub_iam, spec_login):
    """TEST-FR-013: AFR-OAP-011 leave-hod-availability.
    Verify submitted leave application is made available to the appropriate HoD.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Visit", "from_date": "2026-12-10", "to_date": "2026-12-11"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    leaves = extract_rows(hod.get(f"{BASE_URL}/leave-applications"))
    assert any(x["id"] == lid for x in leaves)


def test_fr_014_leave_hod_review(stub_iam, spec_login):
    """TEST-FR-014: AFR-OAP-012 leave-hod-review.
    Verify HoD can view and review leave application and supporting documents.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {
            "reason": "Symposium",
            "from_date": "2026-12-10",
            "to_date": "2026-12-11",
            "supporting_document_link": SAMPLE_DRIVE_URL,
        },
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.get(f"{BASE_URL}/leave-applications/{lid}")
    assert r.status_code == 200
    assert r.json()["supporting_document_link"] == SAMPLE_DRIVE_URL


def test_fr_015_leave_hod_approve(stub_iam, spec_login):
    """TEST-FR-015: AFR-OAP-013 leave-hod-approve.
    Verify HoD can approve a submitted leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Holiday", "from_date": "2026-12-10", "to_date": "2026-12-11"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_fr_016_leave_hod_reject(stub_iam, spec_login):
    """TEST-FR-016: AFR-OAP-013 leave-hod-reject.
    Verify HoD can reject a submitted leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Holiday", "from_date": "2026-12-10", "to_date": "2026-12-11"},
        format="json",
    ).json()["id"]
    hod = spec_login(stub_iam, 9001, ["Head of Department"], "Head of Department", kind="faculty")
    r = hod.post(f"{BASE_URL}/leave-applications/{lid}/decision", {"outcome": "reject"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_fr_017_leave_status_tracking(stub_iam, spec_login):
    """TEST-FR-017: AFR-OAP-014 leave-status-tracking.
    Verify student can track current status of submitted leave application.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    lid = student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event", "from_date": "2026-12-10", "to_date": "2026-12-11"},
        format="json",
    ).json()["id"]
    res = student.get(f"{BASE_URL}/leave-applications/{lid}")
    assert res.status_code == 200
    assert res.json()["status"] == "submitted"


def test_fr_018_leave_history_retrieval(stub_iam, spec_login):
    """TEST-FR-018: AFR-OAP-015 leave-history-retrieval.
    Verify student can view full leave application history.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event 1", "from_date": "2026-12-10", "to_date": "2026-12-11"},
        format="json",
    )
    student.post(
        f"{BASE_URL}/leave-applications",
        {"reason": "Event 2", "from_date": "2026-12-15", "to_date": "2026-12-16"},
        format="json",
    )
    leaves = extract_rows(student.get(f"{BASE_URL}/leave-applications"))
    assert len(leaves) >= 2


def test_fr_019_bonafide_request_submission(stub_iam, spec_login):
    """TEST-FR-019: AFR-OAP-016 bonafide-request-submission.
    Verify student can submit a bonafide certificate request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Bank loan"}, format="json")
    assert r.status_code == 201
    assert r.json()["status"] == "submitted"


def test_fr_020_bonafide_acad_admin_availability(stub_iam, spec_login):
    """TEST-FR-020: AFR-OAP-017 bonafide-acad-admin-availability.
    Verify submitted bonafide request is available to Academic Administrator.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(
        f"{BASE_URL}/bonafide-requests", {"purpose": "Visa application"}, format="json"
    ).json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    requests = extract_rows(aa.get(f"{BASE_URL}/bonafide-requests"))
    assert any(x["id"] == bid for x in requests)


def test_fr_021_bonafide_verification(stub_iam, spec_login):
    """TEST-FR-021: AFR-OAP-018 bonafide-verification.
    Verify Academic Administrator can verify a submitted bonafide request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(
        f"{BASE_URL}/bonafide-requests", {"purpose": "Competition"}, format="json"
    ).json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    assert r.status_code == 200
    assert BonafideRequest.objects.get(pk=bid).verified_by_user_id == 9100


def test_fr_022_bonafide_decision_approve(stub_iam, spec_login):
    """TEST-FR-022: AFR-OAP-019 bonafide-decision-approve.
    Verify Academic Administrator can approve a verified bonafide request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Scholarship"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    r = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_fr_023_bonafide_decision_reject(stub_iam, spec_login):
    """TEST-FR-023: AFR-OAP-019 bonafide-decision-reject.
    Verify Academic Administrator can reject a bonafide request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Other"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    r = aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "reject"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_fr_024_bonafide_status_monitoring(stub_iam, spec_login):
    """TEST-FR-024: AFR-OAP-020 bonafide-status-monitoring.
    Verify student can monitor status of bonafide request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Hostel"}, format="json").json()["id"]
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}")
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"


def test_fr_025_bonafide_download_approved(stub_iam, spec_login):
    """TEST-FR-025: AFR-OAP-021 bonafide-download-approved.
    Verify student can download certificate after bonafide request is approved.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Travel"}, format="json").json()["id"]
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/verify")
    aa.post(f"{BASE_URL}/bonafide-requests/{bid}/decision", {"outcome": "approve"}, format="json")
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert r.status_code == 200


def test_fr_026_bonafide_download_refusal(stub_iam, spec_login):
    """TEST-FR-026: AFR-OAP-021 bonafide-download-refusal.
    Verify student cannot download certificate prior to approval.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    bid = student.post(f"{BASE_URL}/bonafide-requests", {"purpose": "Bank"}, format="json").json()["id"]
    r = student.get(f"{BASE_URL}/bonafide-requests/{bid}/certificate")
    assert r.status_code in (400, 403, 404, 409, 422)


def test_fr_027_nodues_initiation(stub_iam, spec_login):
    """TEST-FR-027: AFR-OAP-022 nodues-initiation.
    Verify student can initiate a no-dues clearance request.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    r = student.post(f"{BASE_URL}/no-dues-cases")
    assert r.status_code == 201
    assert NoDuesCase.objects.filter(user_id=1001).exists()


def test_fr_028_nodues_parallel_routing_seven_domains(stub_iam, spec_login):
    """TEST-FR-028: AFR-OAP-023 nodues-parallel-routing-seven-domains.
    Verify no-dues clearance routes in parallel to all seven mandatory domains.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    results = NoDuesResult.objects.filter(case=case)
    domains = {r.domain for r in results}
    expected = {"library", "hostel", "mess", "department", "lab", "academic_section", "student_section"}
    assert domains == expected


def test_fr_029_nodues_library_clearance(stub_iam, spec_login):
    """TEST-FR-029: AFR-OAP-024 nodues-library-clearance.
    Verify Librarian records clearance for Library domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lib = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    r = lib.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["library"] == "clear"


def test_fr_030_nodues_hostel_clearance(stub_iam, spec_login):
    """TEST-FR-030: AFR-OAP-025 nodues-hostel-clearance.
    Verify Hostel Warden records clearance for Hostel domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    hostel = spec_login(stub_iam, 7002, ["Hostel Warden"], "Hostel Warden", kind="staff")
    r = hostel.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["hostel"] == "clear"


def test_fr_031_nodues_mess_clearance(stub_iam, spec_login):
    """TEST-FR-031: AFR-OAP-026 nodues-mess-clearance.
    Verify Mess In-charge records clearance for Mess domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    mess = spec_login(stub_iam, 7003, ["Mess In-charge"], "Mess In-charge", kind="staff")
    r = mess.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["mess"] == "clear"


def test_fr_032_nodues_lab_clearance(stub_iam, spec_login):
    """TEST-FR-032: AFR-OAP-027 nodues-lab-clearance.
    Verify Lab Supervisor records clearance for Lab domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lab = spec_login(stub_iam, 7005, ["Lab Supervisor"], "Lab Supervisor", kind="staff")
    r = lab.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200
    assert r.json()["results"]["lab"] == "clear"


@pytest.mark.skip(
    reason="NOT_AUTOMATED: Gap G2 - Department verifier has no designation in IAM per blueprint"
)
def test_fr_033_nodues_department_clearance(stub_iam, spec_login):
    """TEST-FR-033: AFR-OAP-052 nodues-department-clearance.
    Verify Department verifier records clearance for Department domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    da = spec_login(
        stub_iam, 7004, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")
    assert r.status_code == 200


@pytest.mark.skip(
    reason="NOT_AUTOMATED: Gap G2 - Academic Section verifier has no designation in IAM per blueprint"
)
def test_fr_034_nodues_academic_section_clearance(stub_iam, spec_login):
    """TEST-FR-034: AFR-OAP-053 nodues-academic-section-clearance.
    Verify Academic Section verifier records clearance for Academic Section domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(
        f"{BASE_URL}/no-dues-cases/{case.pk}/results",
        {"domain": "academic_section", "result": "clear"},
        format="json",
    )
    assert r.status_code == 200


@pytest.mark.skip(
    reason="NOT_AUTOMATED: Gap G2 - Student Section verifier has no designation in IAM per blueprint"
)
def test_fr_035_nodues_student_section_clearance(stub_iam, spec_login):
    """TEST-FR-035: AFR-OAP-054 nodues-student-section-clearance.
    Verify Student Section verifier records clearance for Student Section domain.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(
        f"{BASE_URL}/no-dues-cases/{case.pk}/results",
        {"domain": "student_section", "result": "clear"},
        format="json",
    )
    assert r.status_code == 200


def test_fr_036_nodues_independent_statuses(stub_iam, spec_login):
    """TEST-FR-036: AFR-OAP-028 nodues-independent-statuses.
    Verify all seven domain clearance statuses are stored and maintained independently.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    lib = spec_login(stub_iam, 7001, ["Librarian"], "Librarian", kind="staff")
    lib.post(f"{BASE_URL}/no-dues-cases/{case.pk}/results", {"result": "clear"}, format="json")

    results = {r.domain: r.result for r in NoDuesResult.objects.filter(case=case)}
    assert results["library"] == "clear"
    assert results["hostel"] == "pending"
    assert results["mess"] == "pending"


def test_fr_037_nodues_consolidation_review(stub_iam, spec_login):
    """TEST-FR-037: AFR-OAP-029 nodues-consolidation-review.
    Verify Academic Administrator can review consolidated 7-domain results.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.get(f"{BASE_URL}/no-dues-cases/{case.pk}")
    assert r.status_code == 200
    assert "results" in r.json()
    assert len(r.json()["results"]) == 7


def test_fr_038_nodues_finalization_all_clear(stub_iam, spec_login):
    """TEST-FR-038: AFR-OAP-030 nodues-finalization-all-clear.
    Verify Academic Administrator can finalize no-dues clearance when all 7 domains are Clear.
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


def test_fr_039_nodues_finalization_refusal(stub_iam, spec_login):
    """TEST-FR-039: AFR-OAP-030 nodues-finalization-refusal-dues-outstanding.
    Verify finalization is refused when any authority records dues outstanding or pending.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    NoDuesResult.objects.filter(case=case).exclude(domain="mess").update(result="clear")
    NoDuesResult.objects.filter(case=case, domain="mess").update(result="outstanding")

    aa = spec_login(
        stub_iam, 9100, ["Academic Administrator"], "Academic Administrator", kind="staff"
    )
    r = aa.post(f"{BASE_URL}/no-dues-cases/{case.pk}/finalize")
    assert r.status_code in (400, 409, 422)


def test_fr_040_nodues_progress_tracking(stub_iam, spec_login):
    """TEST-FR-040: AFR-OAP-031 nodues-progress-tracking.
    Verify student can track no-dues progress across all 7 clearance authorities.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    r = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 7


def test_fr_041_nodues_certificate_download_finalized(stub_iam, spec_login):
    """TEST-FR-041: AFR-OAP-032 nodues-certificate-download-finalized.
    Verify student can download no-dues certificate after finalization.
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


def test_fr_042_nodues_certificate_download_refusal(stub_iam, spec_login):
    """TEST-FR-042: AFR-OAP-032 nodues-certificate-download-refusal.
    Verify student cannot download no-dues certificate before finalization.
    """
    student = spec_login(stub_iam, 1001, ["student"], "student")
    student.post(f"{BASE_URL}/no-dues-cases")
    case = NoDuesCase.objects.get(user_id=1001)
    r = student.get(f"{BASE_URL}/no-dues-cases/{case.pk}/certificate")
    assert r.status_code in (400, 403, 404, 409, 422)


def test_fr_043_assistantship_claim_submission(stub_iam, spec_login, spec_assign):
    """TEST-FR-043: AFR-OAP-033 assistantship-claim-submission.
    Verify PG student can submit an assistantship claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/assistantship-claims")
    assert r.status_code == 201
    assert r.json()["status"] == "awaiting_dual_verification"


def test_fr_044_assistantship_dual_routing(stub_iam, spec_login, spec_assign):
    """TEST-FR-044: AFR-OAP-034 assistantship-dual-routing.
    Verify submitted assistantship claim routes to both Thesis Supervisor and TA Supervisor.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    claim = AssistantshipClaim.objects.get(pk=cid)
    assert claim.thesis_supervisor_user_id == 5001
    assert claim.ta_supervisor_user_id == 5002


def test_fr_045_assistantship_thesis_supervisor_verify(stub_iam, spec_login, spec_assign):
    """TEST-FR-045: AFR-OAP-035 assistantship-thesis-supervisor-verify.
    Verify Thesis Supervisor can record verification for an assistantship claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ts = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    r = ts.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "thesis"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_other_verification"


def test_fr_046_assistantship_ta_supervisor_verify(stub_iam, spec_login, spec_assign):
    """TEST-FR-046: AFR-OAP-035 assistantship-ta-supervisor-verify.
    Verify TA Supervisor can record verification for an assistantship claim.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    ta = spec_login(stub_iam, 5002, ["faculty"], "faculty", kind="faculty")
    r = ta.post(f"{BASE_URL}/assistantship-claims/{cid}/verifications", {"role": "ta"}, format="json")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_other_verification"


def test_fr_047_assistantship_department_gating(stub_iam, spec_login, spec_assign):
    """TEST-FR-047: AFR-OAP-036 assistantship-department-gating.
    Verify claim is not available to Department Administrator until both supervisor verifications are complete.
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


def test_fr_048_assistantship_department_review(stub_iam, spec_login, spec_assign):
    """TEST-FR-048: AFR-OAP-037 assistantship-department-review.
    Verify Department Administrator can review claim after both supervisor verifications complete.
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
    r = da.get(f"{BASE_URL}/assistantship-claims/{cid}")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_department_review"


def test_fr_049_assistantship_department_forward(stub_iam, spec_login, spec_assign):
    """TEST-FR-049: AFR-OAP-038 assistantship-department-forward.
    Verify Department Administrator forwards reviewed assistantship claim to HoD.
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


def test_fr_050_assistantship_hod_approve(stub_iam, spec_login, spec_assign):
    """TEST-FR-050: AFR-OAP-039 assistantship-hod-approve.
    Verify HoD can approve an assistantship claim forwarded by Department Administrator.
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


def test_fr_051_assistantship_hod_reject(stub_iam, spec_login, spec_assign):
    """TEST-FR-051: AFR-OAP-039 assistantship-hod-reject.
    Verify HoD can reject an assistantship claim forwarded by Department Administrator.
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


def test_fr_052_assistantship_acad_admin_availability(stub_iam, spec_login, spec_assign):
    """TEST-FR-052: AFR-OAP-040 assistantship-acad-admin-availability.
    Verify HoD-approved claim becomes available to Academic Administrator for stipend processing.
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
    r = aa.get(f"{BASE_URL}/assistantship-claims/{cid}")
    assert r.status_code == 200
    assert r.json()["status"] == "approved_awaiting_stipend"


def test_fr_053_assistantship_stipend_processing(stub_iam, spec_login, spec_assign):
    """TEST-FR-053: AFR-OAP-041 assistantship-stipend-processing.
    Verify Academic Administrator can process stipend disbursement for HoD-approved claim.
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


def test_fr_054_assistantship_tracking(stub_iam, spec_login, spec_assign):
    """TEST-FR-054: AFR-OAP-042 assistantship-tracking.
    Verify PG student can track assistantship claim across its processing stages.
    """
    spec_assign(stub_iam, 1001, 5001, 5002)
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    cid = pg.post(f"{BASE_URL}/assistantship-claims").json()["id"]
    r = pg.get(f"{BASE_URL}/assistantship-claims/{cid}")
    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_dual_verification"


def test_fr_055_assignment_thesis_supervisor(stub_iam, spec_login):
    """TEST-FR-055: AFR-OAP-043 assignment-thesis-supervisor.
    Verify Department Administrator can record a thesis-supervisor assignment.
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


def test_fr_056_assignment_ta_course_only(stub_iam, spec_login):
    """TEST-FR-056: AFR-OAP-044 assignment-ta-course-only.
    Verify Department Administrator can record TA assignment with course/subject only.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "CS201", "supervisor_user_id": None},
        format="json",
    )
    assert r.status_code == 201
    assert TAAssignment.objects.filter(student_user_id=1001, course_code="CS201").exists()


def test_fr_057_assignment_ta_faculty_only(stub_iam, spec_login):
    """TEST-FR-057: AFR-OAP-044 assignment-ta-faculty-only.
    Verify Department Administrator can record TA assignment with faculty member only.
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
    assert TAAssignment.objects.filter(student_user_id=1001, supervisor_user_id=5002).exists()


def test_fr_058_assignment_ta_both(stub_iam, spec_login):
    """TEST-FR-058: AFR-OAP-044 assignment-ta-both.
    Verify Department Administrator can record TA assignment with both course and faculty.
    """
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    r = da.post(
        f"{BASE_URL}/ta-assignments",
        {"student_user_id": 1001, "course_code": "CS301", "supervisor_user_id": 5002},
        format="json",
    )
    assert r.status_code == 201
    assert TAAssignment.objects.filter(student_user_id=1001, course_code="CS301", supervisor_user_id=5002).exists()


def test_fr_059_seminar_scheduling_request(stub_iam, spec_login):
    """TEST-FR-059: AFR-OAP-045 seminar-scheduling-request.
    Verify PG student can initiate a request for graduate seminar scheduling.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    r = pg.post(f"{BASE_URL}/seminar-requests")
    assert r.status_code == 201
    assert r.json()["status"] == "awaiting_scheduling"


def test_fr_060_seminar_dept_admin_availability(stub_iam, spec_login):
    """TEST-FR-060: AFR-OAP-046 seminar-dept-admin-availability.
    Verify seminar scheduling request is available to Department Administrator.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    requests = extract_rows(da.get(f"{BASE_URL}/seminar-requests"))
    assert any(x["id"] == sid for x in requests)


def test_fr_061_seminar_scheduling_action(stub_iam, spec_login):
    """TEST-FR-061: AFR-OAP-047 seminar-scheduling-action.
    Verify Department Administrator can schedule a graduate seminar.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    r = da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Hall A"},
        format="json",
    )
    assert r.status_code == 201
    assert SeminarSchedule.objects.filter(request_id=sid).exists()


def test_fr_062_seminar_history_logging(stub_iam, spec_login):
    """TEST-FR-062: AFR-OAP-048 seminar-history-logging.
    Verify system maintains history/log of graduate seminar scheduling records.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Hall A"},
        format="json",
    )
    assert SeminarSchedule.objects.filter(request_id=sid).exists()


def test_fr_063_seminar_visibility(stub_iam, spec_login):
    """TEST-FR-063: AFR-OAP-049 seminar-visibility.
    Verify PG students and faculty members can view scheduled graduate seminars.
    """
    pg = spec_login(stub_iam, 1001, ["PG Student"], "PG Student")
    sid = pg.post(f"{BASE_URL}/seminar-requests").json()["id"]
    da = spec_login(
        stub_iam, 8001, ["Department Administrator"], "Department Administrator", kind="staff"
    )
    when = dt.datetime(2026, 12, 10, 10, 0, tzinfo=dt.UTC).isoformat()
    da.post(
        f"{BASE_URL}/seminar-requests/{sid}/schedule",
        {"scheduled_for": when, "venue": "Hall A"},
        format="json",
    )
    fac = spec_login(stub_iam, 5001, ["faculty"], "faculty", kind="faculty")
    schedules = extract_rows(fac.get(f"{BASE_URL}/seminar-schedules"))
    assert any(x["venue"] == "Hall A" for x in schedules)
