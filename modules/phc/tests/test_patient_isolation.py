"""Person A never sees person B's rows, by list, id, filter or download (AFR-PHC-012)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.phc.models import ReimbursementClaim, Requisition
from modules.phc.tests.factories import (
    AUTHORITY_ID,
    EMPLOYEE_ID,
    OTHER_EMPLOYEE_ID,
    OTHER_STAFF_ID,
    PHC_STAFF_ID,
    STUDENT_ID,
    client_as,
    item,
    policy,
    visit_for,
)

pytestmark = pytest.mark.django_db


def _claim(user_id):
    visit = visit_for(user_id, recorded_by=OTHER_STAFF_ID if user_id == PHC_STAFF_ID else PHC_STAFF_ID)
    return ReimbursementClaim.objects.create(
        user_id=user_id, prescription=visit.prescriptions.get(),
        expense_date=timezone.localdate(), amount="100.00", submitted_at=timezone.now())


# PHC-BR-02
def test_patient_cannot_list_or_open_anothers_record_phc_br_02(stub_iam):
    other = visit_for(EMPLOYEE_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    assert student.get("/api/v1/phc/records").data["results"] == []
    assert student.get(f"/api/v1/phc/records/{other.pk}").status_code == 404
    assert student.get("/api/v1/phc/records/pdf", {"ids": str(other.pk)}).status_code == 404


def test_employee_cannot_see_or_act_on_anothers_claim(stub_iam):
    other = _claim(OTHER_EMPLOYEE_ID)
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    assert employee.get("/api/v1/phc/claims").data["results"] == []
    assert employee.get(f"/api/v1/phc/claims/{other.pk}").status_code == 404
    assert employee.get("/api/v1/phc/claims", {"status": "pending_phc_review"}).data[
        "results"] == []
    r = employee.post(f"/api/v1/phc/claims/{other.pk}/transition", {"event": "forward"})
    assert r.status_code == 404


def test_claimant_cannot_move_own_claim(stub_iam):
    mine = _claim(EMPLOYEE_ID)
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    r = employee.post(f"/api/v1/phc/claims/{mine.pk}/transition", {"event": "forward"})
    assert r.status_code == 403
    assert r.data["error"]["code"] == "own_claim"
    assert ReimbursementClaim.objects.get(pk=mine.pk).status == "pending_phc_review"


def test_processing_office_never_sees_its_own_claim_in_the_queue(stub_iam):
    own = _claim(PHC_STAFF_ID)
    other = _claim(EMPLOYEE_ID)
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    assert [c["id"] for c in staff.get("/api/v1/phc/claims").data["results"]] == [other.pk]
    r = staff.post(f"/api/v1/phc/claims/{own.pk}/transition", {"event": "forward"})
    assert r.status_code == 404
    assert ReimbursementClaim.objects.get(pk=own.pk).status == "pending_phc_review"


def test_staff_cannot_see_or_record_their_own_clinical_record(stub_iam, user_ref):
    own = visit_for(PHC_STAFF_ID, recorded_by=OTHER_STAFF_ID)
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID,
                      users={PHC_STAFF_ID: user_ref(PHC_STAFF_ID, kind="staff")})
    assert staff.get(f"/api/v1/phc/records/{own.pk}").status_code == 404
    r = staff.post("/api/v1/phc/records", {
        "patient_user_id": PHC_STAFF_ID, "visit_date": str(timezone.localdate()),
        "complaint": "x", "prescriptions": [{"medicine": "m", "dosage": "d"}]}, format="json")
    assert r.status_code == 409
    assert r.data["error"]["code"] == "self_record"


def test_claim_cannot_use_a_prescription_staff_recorded_for_someone_else(stub_iam):
    policy()
    other = visit_for(OTHER_EMPLOYEE_ID)
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID)
    r = employee.post("/api/v1/phc/claims", {
        "prescription_id": other.prescriptions.get().pk,
        "expense_date": str(timezone.localdate() - timedelta(days=1)), "amount": "1.00"},
        format="json")
    assert r.status_code == 422
    assert employee.get("/api/v1/phc/claims/prescriptions").data == []


def test_authority_cannot_decide_a_requisition_it_raised(stub_iam):
    stock = item()
    req = Requisition.objects.create(originator_user_id=AUTHORITY_ID, purpose="x")
    req.lines.create(item=stock, quantity="1")
    authority = client_as(stub_iam, "Approving Authority", AUTHORITY_ID)
    assert authority.get("/api/v1/phc/requisitions").data["results"] == []
    r = authority.post(f"/api/v1/phc/requisitions/{req.pk}/transition", {"event": "approve"})
    assert r.status_code == 404
    hybrid = client_as(stub_iam, "PHC Staff", AUTHORITY_ID, extra=("phc.requisition.approve",))
    r = hybrid.post(f"/api/v1/phc/requisitions/{req.pk}/transition", {"event": "approve"})
    assert r.status_code == 409
    assert r.data["error"]["code"] == "own_requisition"
    assert Requisition.objects.get(pk=req.pk).status == "pending_approval"


def test_requisitions_are_invisible_to_patients(stub_iam):
    Requisition.objects.create(originator_user_id=PHC_STAFF_ID, purpose="x")
    employee = client_as(stub_iam, "staff", EMPLOYEE_ID, extra=("phc.requisition.view",))
    assert employee.get("/api/v1/phc/requisitions").data["results"] == []


def test_unpublished_schedule_is_hidden_from_patients(stub_iam):
    from modules.phc.models import DoctorSchedule

    DoctorSchedule.objects.create(doctor_name="Draft", created_by_user_id=PHC_STAFF_ID)
    student = client_as(stub_iam, "student", STUDENT_ID)
    assert student.get("/api/v1/phc/schedules").data == []
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    assert len(staff.get("/api/v1/phc/schedules").data) == 1
