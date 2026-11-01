"""Tests for LTC and CPDA claim lifecycles (submission, HR verification, approval, settlement)."""
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import EmployeeServiceRecord, LtcRequest, CpdaRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def claims_employee():
    return EmployeeServiceRecord.objects.create(
        user_id=501,
        employee_id="PF-501",
        category="faculty",
        designation="Associate Professor",
        department="Mechanical",
        appointment_date="2018-07-01",
        leave_balances={"casual": 8.0, "earned": 30.0},
        cpda_balance=Decimal("300000.00"),
        ltc_eligible_block="2026-2029",
    )


def test_ltc_lifecycle(stub_iam, user_ref, claims_employee):
    # 1. Employee submits LTC Advance request
    stub_iam(
        make_session(
            user_id=501,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.ltc.apply", "hr_eis.ltc.view_self"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            601: user_ref(601, name="HR Officer", kind="staff"),
            701: user_ref(701, name="HOD ME", kind="faculty"),
            801: user_ref(801, name="Accountant", kind="staff"),
        },
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    sub_resp = client.post(
        "/api/v1/hreis/ltc/",
        {
            "request_type": "advance",
            "block_year": "2026-2029",
            "travel_from": "Jabalpur",
            "travel_to": "Goa",
            "travel_start_date": "2026-05-10",
            "travel_end_date": "2026-05-20",
            "estimated_amount": 35000.0,
            "supporting_documents": [{"name": "Estimate", "url": "https://example.com/est.pdf"}],
        },
        format="json",
    )
    assert sub_resp.status_code == 201
    ltc_id = sub_resp.json()["id"]
    assert sub_resp.json()["status"] == "submitted"

    # 2. HR Admin verifies claim documents & eligibility
    stub_iam(
        make_session(
            user_id=601,
            kind="staff",
            roles=("hr_admin",),
            modules=("hr_eis",),
            permissions=("hr_eis.ltc.verify", "hr_eis.ltc.view_all"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            601: user_ref(601, name="HR Officer", kind="staff"),
            701: user_ref(701, name="HOD ME", kind="faculty"),
            801: user_ref(801, name="Accountant", kind="staff"),
        },
    )

    hr_client = APIClient()
    hr_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    verify_resp = hr_client.post(
        f"/api/v1/hreis/ltc/{ltc_id}/verify/",
        {"verdict": "verified", "remarks": "Block year and entitlement checked. Eligible."},
        format="json",
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verification_status"] == "verified"

    # 3. Approving Authority (HOD) approves
    stub_iam(
        make_session(
            user_id=701,
            kind="faculty",
            roles=("hod",),
            modules=("hr_eis",),
            permissions=("hr_eis.ltc.approve", "hr_eis.ltc.view_all"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            701: user_ref(701, name="HOD ME", kind="faculty"),
        },
    )

    hod_client = APIClient()
    hod_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    approve_resp = hod_client.post(
        f"/api/v1/hreis/ltc/{ltc_id}/decide/",
        {"outcome": "approved", "remarks": "Approved advance as per rules."},
        format="json",
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # 4. Accountant records financial settlement
    stub_iam(
        make_session(
            user_id=801,
            kind="staff",
            roles=("accountant",),
            modules=("hr_eis",),
            permissions=("hr_eis.ltc.settle", "hr_eis.ltc.view_all"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            801: user_ref(801, name="Accountant", kind="staff"),
        },
    )

    acct_client = APIClient()
    acct_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    settle_resp = acct_client.post(
        f"/api/v1/hreis/ltc/{ltc_id}/settle/",
        {"passed_amount": 35000.0, "reference_id": "REF-998811", "remarks": "Transferred via NEFT Ref 998811"},
        format="json",
    )
    assert settle_resp.status_code == 200
    assert settle_resp.json()["payment_status"] == "paid"
    assert settle_resp.json()["status"] == "settled"


def test_cpda_lifecycle(stub_iam, user_ref, claims_employee):
    # 1. Employee submits CPDA claim
    stub_iam(
        make_session(
            user_id=501,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.cpda.apply", "hr_eis.cpda.view_self"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            601: user_ref(601, name="HR Officer", kind="staff"),
            701: user_ref(701, name="HOD ME", kind="faculty"),
            801: user_ref(801, name="Accountant", kind="staff"),
        },
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    sub_resp = client.post(
        "/api/v1/hreis/cpda/",
        {
            "request_type": "reimbursement",
            "purpose": "International Conference Registration & Travel",
            "amount": 45000.0,
            "supporting_documents": ["https://drive.example.com/receipt1.pdf"],
        },
        format="json",
    )
    assert sub_resp.status_code == 201
    cpda_id = sub_resp.json()["id"]

    # 2. HR Admin verifies CPDA
    stub_iam(
        make_session(
            user_id=601,
            kind="staff",
            roles=("hr_admin",),
            modules=("hr_eis",),
            permissions=("hr_eis.cpda.verify", "hr_eis.cpda.view_all"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            601: user_ref(601, name="HR Officer", kind="staff"),
        },
    )

    hr_client = APIClient()
    hr_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    verify_resp = hr_client.post(
        f"/api/v1/hreis/cpda/{cpda_id}/verify/",
        {"verdict": "verified", "remarks": "Conference paper accepted and receipts verified."},
        format="json",
    )
    assert verify_resp.status_code == 200

    # 3. HOD approves CPDA
    stub_iam(
        make_session(
            user_id=701,
            kind="faculty",
            roles=("hod",),
            modules=("hr_eis",),
            permissions=("hr_eis.cpda.approve", "hr_eis.cpda.view_all"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            701: user_ref(701, name="HOD ME", kind="faculty"),
        },
    )

    hod_client = APIClient()
    hod_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    approve_resp = hod_client.post(
        f"/api/v1/hreis/cpda/{cpda_id}/decide/",
        {"outcome": "approved", "remarks": "Recommended and approved."},
        format="json",
    )
    assert approve_resp.status_code == 200

    # 4. Accountant settles and disburses CPDA funds
    stub_iam(
        make_session(
            user_id=801,
            kind="staff",
            roles=("accountant",),
            modules=("hr_eis",),
            permissions=("hr_eis.cpda.settle", "hr_eis.cpda.view_all"),
        ),
        users={
            501: user_ref(501, name="Dr. Raman", kind="faculty"),
            801: user_ref(801, name="Accountant", kind="staff"),
        },
    )

    acct_client = APIClient()
    acct_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    settle_resp = acct_client.post(
        f"/api/v1/hreis/cpda/{cpda_id}/settle/",
        {"passed_amount": 45000.0, "voucher_no": "VOUCH-1002", "remarks": "Disbursed via bank transfer"},
        format="json",
    )
    assert settle_resp.status_code == 200
    assert settle_resp.json()["disbursement_status"] == "paid"

    # 5. Check CPDA balance deduction on EmployeeServiceRecord: 300000 - 45000 = 255000
    claims_employee.refresh_from_db()
    assert Decimal(str(claims_employee.cpda_balance)) == Decimal("255000.00")
