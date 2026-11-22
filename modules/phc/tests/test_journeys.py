"""One HTTP-only journey per live use case flow, each actor acting in turn."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.phc.models import (
    AuditRecord,
    ClaimAction,
    DoctorSchedule,
    LowStockAlert,
    Notification,
    PatientVisit,
    ReimbursementClaim,
    Requisition,
)
from modules.phc.tests.factories import (
    ACCOUNTS_ID,
    AUTHORITY_ID,
    EMPLOYEE_ID,
    PHC_STAFF_ID,
    STUDENT_ID,
    client_as,
    item,
    policy,
    visit_for,
)

pytestmark = pytest.mark.django_db

SLOTS = [{"day_of_week": 0, "start_time": "10:00", "end_time": "13:00"}]


def _schedule(stub_iam, published=True):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post("/api/v1/phc/schedules", {"doctor_name": "Dr. Iyer",
                                              "specialization": "General", "slots": SLOTS},
                   format="json")
    assert r.status_code == 201, r.content
    if published:
        assert staff.post(f"/api/v1/phc/schedules/{r.data['id']}/publish").status_code == 200
    return r.data["id"]


# -- Schedules -----------------------------------------------------------------------
# PHC-UC-22, AFR-PHC-004, AFR-PHC-005
def test_phc_uc_22_create_and_publish_schedule(stub_iam):
    sid = _schedule(stub_iam)
    schedule = DoctorSchedule.objects.get(pk=sid)
    assert schedule.is_published and schedule.published_at is not None
    assert list(schedule.slots.values_list("day_of_week", flat=True)) == [0]


# PHC-UC-22 E1
def test_phc_uc_22_e1_invalid_schedule_is_not_saved(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post("/api/v1/phc/schedules", {"doctor_name": "Dr. Iyer", "slots": [
        {"day_of_week": 0, "start_time": "13:00", "end_time": "10:00"}]}, format="json")
    assert r.status_code == 400
    assert not DoctorSchedule.objects.exists()


# PHC-UC-07, AFR-PHC-002
def test_phc_uc_07_maintain_schedule_replaces_the_week(stub_iam):
    sid = _schedule(stub_iam)
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.put(f"/api/v1/phc/schedules/{sid}", {
        "doctor_name": "Dr. Iyer", "specialization": "General",
        "slots": [{"day_of_week": 2, "start_time": "09:00", "end_time": "11:00"},
                  {"day_of_week": 4, "start_time": "14:00", "end_time": "16:00"}]},
        format="json")
    assert r.status_code == 200
    assert [s["day_of_week"] for s in r.data["slots"]] == [2, 4]


# PHC-UC-07 E1
def test_phc_uc_07_e1_invalid_update_leaves_previous_schedule(stub_iam):
    sid = _schedule(stub_iam)
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.put(f"/api/v1/phc/schedules/{sid}", {"doctor_name": "Dr. Iyer", "slots": []},
                  format="json")
    assert r.status_code == 400
    assert DoctorSchedule.objects.get(pk=sid).slots.count() == 1


# PHC-UC-08, PHC-UC-01, CFR-PHC-001, AFR-PHC-001, AFR-PHC-003, PHC-BR-01
def test_phc_uc_08_then_phc_uc_01_patient_sees_schedule_with_live_status(stub_iam):
    sid = _schedule(stub_iam)
    unpublished = _schedule(stub_iam, published=False)
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    assert staff.post(f"/api/v1/phc/schedules/{sid}/attendance",
                      {"status": "available"}).status_code == 200
    student = client_as(stub_iam, "student", STUDENT_ID)
    rows = student.get("/api/v1/phc/schedules").data
    # PHC-BR-01: published schedule only, with today's real-time status.
    assert [(r["id"], r["today_status"]) for r in rows] == [(sid, "available")]
    assert unpublished not in [r["id"] for r in rows]

    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    staff.post(f"/api/v1/phc/schedules/{sid}/attendance", {"status": "departed"})
    student = client_as(stub_iam, "student", STUDENT_ID)
    assert student.get("/api/v1/phc/schedules").data[0]["today_status"] == "departed"


# -- Records -------------------------------------------------------------------------
# PHC-UC-06, CFR-PHC-002, AFR-PHC-007, AFR-PHC-008
def test_phc_uc_06_record_visit_and_prescription(stub_iam, user_ref):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID,
                      users={EMPLOYEE_ID: user_ref(EMPLOYEE_ID, kind="staff")})
    r = staff.post("/api/v1/phc/records", {
        "patient_user_id": EMPLOYEE_ID, "visit_date": str(timezone.localdate()),
        "complaint": "Fever", "diagnosis": "Viral fever",
        "prescriptions": [{"medicine": "Paracetamol 500mg", "dosage": "1-0-1",
                           "duration_days": 3, "instructions": "After food"}]},
        format="json")
    assert r.status_code == 201, r.content
    visit = PatientVisit.objects.get(pk=r.data["id"])
    assert visit.prescriptions.count() == 1
    # PHC-BR-09
    assert AuditRecord.objects.filter(resource_type="patient_visit", resource_id=visit.pk,
                                      action="create").exists()


# PHC-UC-06 E1
def test_phc_uc_06_e1_missing_prescription_saves_nothing(stub_iam, user_ref):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID,
                      users={EMPLOYEE_ID: user_ref(EMPLOYEE_ID, kind="staff")})
    r = staff.post("/api/v1/phc/records", {
        "patient_user_id": EMPLOYEE_ID, "visit_date": str(timezone.localdate()),
        "complaint": "Fever", "prescriptions": []}, format="json")
    assert r.status_code == 400
    assert not PatientVisit.objects.exists()
    assert not AuditRecord.objects.exists()


# AFR-PHC-006
def test_afr_phc_006_staff_search_patients(stub_iam, user_ref):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID,
                      users={EMPLOYEE_ID: user_ref(EMPLOYEE_ID, name="Asha Verma",
                                                   kind="staff")})
    from modules.directory import contracts as directory

    directory.get_users([EMPLOYEE_ID])
    r = staff.get("/api/v1/phc/patients", {"q": "Asha"})
    assert r.status_code == 200
    assert [p["user_id"] for p in r.data] == [EMPLOYEE_ID]
    assert staff.get("/api/v1/phc/patients", {"q": "A"}).status_code == 400


# PHC-UC-02, AFR-PHC-009, AFR-PHC-010
def test_phc_uc_02_patient_reads_own_history(stub_iam):
    mine = visit_for(STUDENT_ID)
    visit_for(EMPLOYEE_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    rows = student.get("/api/v1/phc/records").data["results"]
    assert [r["id"] for r in rows] == [mine.pk]
    assert rows[0]["prescriptions"][0]["medicine"] == "Paracetamol 500mg"


# PHC-UC-02 E1
def test_phc_uc_02_e1_another_patients_record_is_denied(stub_iam):
    other = visit_for(EMPLOYEE_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    assert student.get(f"/api/v1/phc/records/{other.pk}").status_code == 404


# PHC-UC-02, PHC-BR-02
def test_phc_uc_02_patient_access_is_read_only_phc_br_02(stub_iam):
    mine = visit_for(STUDENT_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    assert student.patch(f"/api/v1/phc/records/{mine.pk}", {"diagnosis": "x"},
                         format="json").status_code in (403, 405)
    assert student.post("/api/v1/phc/records", {}, format="json").status_code == 403


# PHC-UC-03
def test_phc_uc_03_download_own_records_as_pdf(stub_iam):
    a, b = visit_for(STUDENT_ID), visit_for(STUDENT_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    r = student.get("/api/v1/phc/records/pdf", {"ids": f"{a.pk},{b.pk}"})
    assert r.status_code == 200
    assert r["Content-Type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


# PHC-UC-03
def test_phc_uc_03_selection_including_anothers_record_gives_no_file(stub_iam):
    mine, other = visit_for(STUDENT_ID), visit_for(EMPLOYEE_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    r = student.get("/api/v1/phc/records/pdf", {"ids": f"{mine.pk},{other.pk}"})
    assert r.status_code == 404
    assert student.get("/api/v1/phc/records/pdf", {"ids": "1,x"}).status_code == 400
    assert student.get("/api/v1/phc/records/pdf", {"ids": ""}).status_code == 400


# -- Reimbursement -------------------------------------------------------------------
def _submit(stub_iam, *, days_ago=1, user_id=EMPLOYEE_ID, role="staff"):
    visit = visit_for(user_id)
    employee = client_as(stub_iam, role, user_id)
    return employee.post("/api/v1/phc/claims", {
        "prescription_id": visit.prescriptions.get().pk,
        "expense_date": str(timezone.localdate() - timedelta(days=days_ago)),
        "amount": "450.00", "description": "Pharmacy bill"}, format="json")


def _act(stub_iam, role, uid, claim_id, event):
    return client_as(stub_iam, role, uid).post(
        f"/api/v1/phc/claims/{claim_id}/transition", {"event": event}, format="json")


# PHC-UC-04, CFR-PHC-003, AFR-PHC-016
def test_phc_uc_04_employee_submits_claim(stub_iam):
    policy()
    r = _submit(stub_iam)
    assert r.status_code == 201, r.content
    claim = ReimbursementClaim.objects.get(pk=r.data["id"])
    assert claim.status == "pending_phc_review"
    assert ClaimAction.objects.filter(claim=claim, event="submit").exists()
    assert AuditRecord.objects.filter(resource_type="reimbursement_claim",
                                      resource_id=claim.pk, action="submit").exists()


# PHC-UC-04 A1, AFR-PHC-013
def test_phc_uc_04_a1_student_is_denied_afr_phc_013(stub_iam):
    policy()
    visit = visit_for(STUDENT_ID)
    student = client_as(stub_iam, "student", STUDENT_ID, extra=("phc.claim.create",))
    r = student.post("/api/v1/phc/claims", {
        "prescription_id": visit.prescriptions.get().pk,
        "expense_date": str(timezone.localdate()), "amount": "10.00"}, format="json")
    assert r.status_code == 403
    assert r.data["error"]["code"] == "not_an_employee"
    assert not ReimbursementClaim.objects.exists()


# PHC-UC-04 A2, AFR-PHC-014, PHC-BR-05
def test_phc_uc_04_a2_someone_elses_prescription_is_denied_afr_phc_014(stub_iam):
    policy()
    other = visit_for(2002)
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    r = employee.post("/api/v1/phc/claims", {
        "prescription_id": other.prescriptions.get().pk,
        "expense_date": str(timezone.localdate()), "amount": "10.00"}, format="json")
    assert r.status_code == 422
    assert r.data["error"]["code"] == "invalid_prescription"
    assert not ReimbursementClaim.objects.exists()


# PHC-UC-04 A3, AFR-PHC-015
def test_phc_uc_04_a3_outside_window_is_denied_afr_phc_015(stub_iam):
    policy(days=30)
    r = _submit(stub_iam, days_ago=31)
    assert r.status_code == 422
    assert r.data["error"]["code"] == "outside_submission_window"
    assert not ReimbursementClaim.objects.exists()


# PHC-UC-04, PHC-BR-06
def test_phc_uc_04_without_a_configured_window_says_so_phc_br_06(stub_iam):
    r = _submit(stub_iam)
    assert r.status_code == 409
    assert r.data["error"]["code"] == "policy_missing"
    assert not ReimbursementClaim.objects.exists()


# BW-PHC-01, PHC-UC-15, PHC-UC-19, PHC-UC-20, PHC-UC-21, CFR-PHC-004, CFR-PHC-005, AFR-PHC-017, AFR-PHC-018, AFR-PHC-019, AFR-PHC-020, AFR-PHC-021
def test_bw_phc_01_claim_approved_and_reimbursed_phc_uc_15_19_20_21(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    steps = [("PHC Staff", PHC_STAFF_ID, "forward", "pending_accounts_verification"),
             ("Accounts & Audit", ACCOUNTS_ID, "verify", "pending_sanction"),
             ("Approving Authority", AUTHORITY_ID, "approve", "approved_for_payment"),
             ("Accounts & Audit", ACCOUNTS_ID, "pay", "reimbursed")]
    for role, uid, event, expected in steps:
        r = _act(stub_iam, role, uid, cid, event)
        assert r.status_code == 200, (event, r.content)
        assert r.data["status"] == expected
    # PHC-BR-13 / AFR-PHC-023: one notification per status change.
    notes = Notification.objects.filter(recipient_user_id=EMPLOYEE_ID).order_by("id")
    assert [n.message.rsplit(" ", 1)[-1] for n in notes] == [
        "verification.", "sanction.", "payment.", "reimbursed."]
    # PHC-BR-09 / AFR-PHC-037
    assert AuditRecord.objects.filter(resource_type="reimbursement_claim",
                                      resource_id=cid).count() == 5
    # PHC-UC-05 / AFR-PHC-022: the claimant sees status and full history.
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    body = employee.get(f"/api/v1/phc/claims/{cid}").data
    assert body["status"] == "reimbursed"
    assert [a["event"] for a in body["actions"]] == ["submit", "forward", "verify", "approve",
                                                     "pay"]


# BW-PHC-02, PHC-BR-14
def test_bw_phc_02_claim_rejected_at_sanction_is_terminal_phc_br_14(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    _act(stub_iam, "PHC Staff", PHC_STAFF_ID, cid, "forward")
    _act(stub_iam, "Accounts & Audit", ACCOUNTS_ID, cid, "verify")
    r = _act(stub_iam, "Approving Authority", AUTHORITY_ID, cid, "reject")
    assert r.data["status"] == "rejected"
    assert Notification.objects.filter(recipient_user_id=EMPLOYEE_ID,
                                       message__endswith="rejected.").exists()
    again = _act(stub_iam, "Approving Authority", AUTHORITY_ID, cid, "approve")
    assert again.status_code == 409
    assert again.data["error"]["code"] == "claim_closed"
    # AFR-PHC-038: the way back is a fresh claim, not a reopened one.
    fresh = _submit(stub_iam)
    assert fresh.status_code == 201
    assert fresh.data["id"] != cid


# PHC-UC-20 E1
def test_phc_uc_20_e1_duplicate_sanction_is_blocked(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    _act(stub_iam, "PHC Staff", PHC_STAFF_ID, cid, "forward")
    _act(stub_iam, "Accounts & Audit", ACCOUNTS_ID, cid, "verify")
    assert _act(stub_iam, "Approving Authority", AUTHORITY_ID, cid, "approve").status_code == 200
    r = _act(stub_iam, "Approving Authority", AUTHORITY_ID, cid, "reject")
    assert r.status_code == 409
    assert ReimbursementClaim.objects.get(pk=cid).status == "approved_for_payment"


# PHC-BR-08
def test_phc_br_08_stages_cannot_be_skipped(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    r = _act(stub_iam, "Accounts & Audit", ACCOUNTS_ID, cid, "verify")
    assert r.status_code == 409
    assert r.data["error"]["code"] == "illegal_transition"
    r = _act(stub_iam, "Approving Authority", AUTHORITY_ID, cid, "approve")
    assert r.status_code == 409
    assert ReimbursementClaim.objects.get(pk=cid).status == "pending_phc_review"


# PHC-UC-15 E1
def test_phc_uc_15_e1_phc_review_has_no_reject(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    r = _act(stub_iam, "PHC Staff", PHC_STAFF_ID, cid, "reject")
    assert r.status_code == 409
    assert ReimbursementClaim.objects.get(pk=cid).status == "pending_phc_review"


# PHC-UC-19 E1
def test_phc_uc_19_e1_verification_has_no_reject(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    _act(stub_iam, "PHC Staff", PHC_STAFF_ID, cid, "forward")
    r = _act(stub_iam, "Accounts & Audit", ACCOUNTS_ID, cid, "reject")
    assert r.status_code == 409


# PHC-UC-21 E1
def test_phc_uc_21_e1_payment_before_sanction_is_refused(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    _act(stub_iam, "PHC Staff", PHC_STAFF_ID, cid, "forward")
    _act(stub_iam, "Accounts & Audit", ACCOUNTS_ID, cid, "verify")
    r = _act(stub_iam, "Accounts & Audit", ACCOUNTS_ID, cid, "pay")
    assert r.status_code == 409
    assert ReimbursementClaim.objects.get(pk=cid).status == "pending_sanction"


# PHC-UC-05
def test_phc_uc_05_employee_lists_only_own_claims(stub_iam):
    policy()
    mine = _submit(stub_iam).data["id"]
    _submit(stub_iam, user_id=2002)
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    rows = employee.get("/api/v1/phc/claims").data["results"]
    assert [r["id"] for r in rows] == [mine]
    assert employee.get("/api/v1/phc/claims", {"status": "bogus"}).status_code == 400
    assert employee.get("/api/v1/phc/claims",
                        {"status": "reimbursed"}).data["results"] == []


def test_claimant_lists_eligible_prescriptions(stub_iam):
    mine = visit_for(EMPLOYEE_ID)
    visit_for(2002)
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    rows = employee.get("/api/v1/phc/claims/prescriptions").data
    assert [r["id"] for r in rows] == [mine.prescriptions.get().pk]


# -- Inventory and requisitions ------------------------------------------------------
# PHC-UC-09, CFR-PHC-006, AFR-PHC-025, AFR-PHC-026
def test_phc_uc_09_deduct_below_threshold_raises_alert(stub_iam):
    stock = item(level="100", threshold="50")
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/inventory/{stock.pk}/adjust", {"delta": "-60",
                                                                "reason": "Dispensed"})
    assert r.status_code == 201
    assert r.data["level_after"] == "40.00" and r.data["low_stock_alert"] is True
    assert LowStockAlert.objects.filter(item=stock).count() == 1
    assert AuditRecord.objects.filter(resource_type="inventory_item", resource_id=stock.pk,
                                      action="adjust").exists()
    alerts = staff.get("/api/v1/phc/inventory/alerts").data["results"]
    assert alerts[0]["item_name"] == stock.name


# PHC-UC-09 A1
def test_phc_uc_09_a1_not_below_threshold_raises_nothing(stub_iam):
    stock = item(level="100", threshold="50")
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/inventory/{stock.pk}/adjust", {"delta": "-50"})
    assert r.data["low_stock_alert"] is False
    assert not LowStockAlert.objects.exists()


# PHC-UC-09 E1
def test_phc_uc_09_e1_invalid_adjustment_is_rejected(stub_iam):
    stock = item(level="10", threshold="5")
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/inventory/{stock.pk}/adjust", {"delta": "-11"})
    assert r.status_code == 422
    assert staff.post(f"/api/v1/phc/inventory/{stock.pk}/adjust",
                      {"delta": "abc"}).status_code == 400
    stock.refresh_from_db()
    assert str(stock.stock_level) == "10.00"


def test_inventory_item_creation_is_audited(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post("/api/v1/phc/inventory", {"name": "ORS", "unit": "sachet",
                                             "stock_level": "20", "reorder_threshold": "10"})
    assert r.status_code == 201
    assert AuditRecord.objects.filter(resource_type="inventory_item",
                                      action="create").count() == 1
    dup = staff.post("/api/v1/phc/inventory", {"name": "ORS", "unit": "sachet",
                                               "stock_level": "1", "reorder_threshold": "1"})
    assert dup.status_code == 409


def _raise_requisition(stub_iam, stock):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    return staff.post("/api/v1/phc/requisitions", {
        "purpose": "Monthly restock", "lines": [{"item_id": stock.pk, "quantity": "200"}]},
        format="json")


# PHC-UC-10, CFR-PHC-007, AFR-PHC-027, AFR-PHC-028
def test_phc_uc_10_submit_requisition_goes_to_authority(stub_iam):
    r = _raise_requisition(stub_iam, item())
    assert r.status_code == 201
    assert r.data["status"] == "pending_approval"
    authority = client_as(stub_iam, "Approving Authority", AUTHORITY_ID)
    rows = authority.get("/api/v1/phc/requisitions").data["results"]
    assert [row["id"] for row in rows] == [r.data["id"]]
    assert rows[0]["allowed_events"] == ["approve", "reject"]


# PHC-UC-10 E1
def test_phc_uc_10_e1_incomplete_requisition_is_blocked(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    assert staff.post("/api/v1/phc/requisitions", {"purpose": "x", "lines": []},
                      format="json").status_code == 400
    assert staff.post("/api/v1/phc/requisitions", {"purpose": "x", "lines": [
        {"item_id": 999, "quantity": "1"}]}, format="json").status_code == 400
    assert not Requisition.objects.exists()


# BW-PHC-03, PHC-UC-16, PHC-UC-14, AFR-PHC-029, AFR-PHC-031
def test_bw_phc_03_approved_then_fulfilled_phc_uc_16_phc_uc_14(stub_iam):
    stock = item(level="10", threshold="5")
    rid = _raise_requisition(stub_iam, stock).data["id"]
    authority = client_as(stub_iam, "Approving Authority", AUTHORITY_ID)
    r = authority.post(f"/api/v1/phc/requisitions/{rid}/transition", {"event": "approve"})
    assert r.data["status"] == "approved"
    # PHC-BR-11 / AFR-PHC-030
    assert Notification.objects.filter(recipient_user_id=PHC_STAFF_ID,
                                       kind="requisition_decision").count() == 1
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/requisitions/{rid}/transition", {"event": "fulfill"})
    assert r.data["status"] == "fulfilled"
    stock.refresh_from_db()
    # PHC-UC-14 note: fulfilment does not touch stock.
    assert str(stock.stock_level) == "10.00"


# BW-PHC-04
def test_bw_phc_04_rejected_requisition_ends(stub_iam):
    rid = _raise_requisition(stub_iam, item()).data["id"]
    authority = client_as(stub_iam, "Approving Authority", AUTHORITY_ID)
    r = authority.post(f"/api/v1/phc/requisitions/{rid}/transition",
                       {"event": "reject", "note": "Budget exhausted"})
    assert r.data["status"] == "rejected"
    assert Notification.objects.filter(recipient_user_id=PHC_STAFF_ID,
                                       message__endswith="rejected.").exists()
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/requisitions/{rid}/transition", {"event": "fulfill"})
    assert r.status_code == 409


# PHC-UC-14 E1, PHC-BR-10
def test_phc_uc_14_e1_unapproved_requisition_cannot_be_fulfilled_phc_br_10(stub_iam):
    rid = _raise_requisition(stub_iam, item()).data["id"]
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/requisitions/{rid}/transition", {"event": "fulfill"})
    assert r.status_code == 409
    assert Requisition.objects.get(pk=rid).status == "pending_approval"


# PHC-UC-16 E1
def test_phc_uc_16_e1_second_decision_is_blocked(stub_iam):
    rid = _raise_requisition(stub_iam, item()).data["id"]
    authority = client_as(stub_iam, "Approving Authority", AUTHORITY_ID)
    authority.post(f"/api/v1/phc/requisitions/{rid}/transition", {"event": "approve"})
    r = authority.post(f"/api/v1/phc/requisitions/{rid}/transition", {"event": "reject"})
    assert r.status_code == 409
    assert Requisition.objects.get(pk=rid).status == "approved"


# -- Ambulance, advisories, reports --------------------------------------------------
# PHC-UC-11, CFR-PHC-008, AFR-PHC-032
def test_phc_uc_11_log_ambulance_use(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post("/api/v1/phc/ambulance", {
        "used_at": (timezone.now() - timedelta(hours=1)).isoformat(),
        "patient_name": "Hostel resident", "destination": "District Hospital"})
    assert r.status_code == 201
    assert staff.get("/api/v1/phc/ambulance").data["results"][0]["destination"] == \
        "District Hospital"


# PHC-UC-11 E1
def test_phc_uc_11_e1_missing_field_saves_nothing(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post("/api/v1/phc/ambulance", {"used_at": timezone.now().isoformat(),
                                             "patient_name": "X"})
    assert r.status_code == 400
    future = staff.post("/api/v1/phc/ambulance", {
        "used_at": (timezone.now() + timedelta(days=1)).isoformat(),
        "patient_name": "X", "destination": "Y"})
    assert future.status_code == 400


# PHC-UC-12, CFR-PHC-009, AFR-PHC-033
def test_phc_uc_12_advisory_visible_to_every_patient(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    r = staff.post("/api/v1/phc/advisories", {"title": "Dengue", "body": "Remove water."})
    assert r.status_code == 201
    for role, uid in (("student", STUDENT_ID), ("faculty", EMPLOYEE_ID)):
        rows = client_as(stub_iam, role, uid).get("/api/v1/phc/advisories").data["results"]
        assert [a["title"] for a in rows] == ["Dengue"]


# PHC-UC-12 E1
def test_phc_uc_12_e1_empty_advisory_is_blocked(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    assert staff.post("/api/v1/phc/advisories", {"title": "", "body": ""}).status_code == 400


# PHC-UC-13, PHC-BR-12, CFR-PHC-010, AFR-PHC-034, AFR-PHC-035
def test_phc_uc_13_reports_are_anonymised_phc_br_12(stub_iam, user_ref):
    for uid in range(6000, 6007):
        visit_for(uid)
    stock = item()
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID,
                      users={uid: user_ref(uid, kind="staff") for uid in range(6000, 6007)})
    staff.post(f"/api/v1/phc/inventory/{stock.pk}/adjust", {"delta": "-5"})
    today = str(timezone.localdate())
    demo = staff.get("/api/v1/phc/reports", {"category": "demographics", "start": today,
                                            "end": today})
    assert demo.status_code == 200
    assert demo.data["data"] == {"distinct_patients": 7, "patients_by_kind": {"staff": 7}}
    util = staff.get("/api/v1/phc/reports", {"category": "utilization", "start": today,
                                            "end": today}).data["data"]
    assert util["visits_by_month"][0]["visits"] == 7
    inv = staff.get("/api/v1/phc/reports", {"category": "inventory", "start": today,
                                           "end": today}).data["data"]
    assert inv["consumption"] == [{"item": stock.name, "unit": "strip", "quantity": "5.00"}]
    for body in (demo.content, ):
        for uid in range(6000, 6007):
            assert str(uid).encode() not in body


# PHC-UC-13 E1
def test_phc_uc_13_e1_invalid_parameters_are_400(stub_iam):
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    assert staff.get("/api/v1/phc/reports", {"category": "x", "start": "2026-01-01",
                                            "end": "2026-01-02"}).status_code == 400
    assert staff.get("/api/v1/phc/reports", {"category": "inventory", "start": "2026-02-01",
                                            "end": "2026-01-01"}).status_code == 400
    assert staff.get("/api/v1/phc/reports", {"category": "inventory", "start": "abc",
                                            "end": "2026-01-01"}).status_code == 400


def test_notifications_list_is_the_callers_own(stub_iam):
    policy()
    cid = _submit(stub_iam).data["id"]
    _act(stub_iam, "PHC Staff", PHC_STAFF_ID, cid, "forward")
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    rows = employee.get("/api/v1/phc/notifications").data["results"]
    assert len(rows) == 1 and rows[0]["resource_id"] == cid
    other = client_as(stub_iam, "staff", 2002)
    assert other.get("/api/v1/phc/notifications").data["results"] == []
