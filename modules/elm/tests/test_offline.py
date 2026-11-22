import pytest

from modules.elm.models import LeaveBalance, LeaveEvent, LeaveRequest
from modules.elm.tests.test_api import api_as
from modules.elm.tests.test_submission import seed

pytestmark = pytest.mark.django_db


def offline_payload(leave_type):
    return {
        "leave_type": leave_type.pk,
        "employee": "101",
        "start_date": "2026-11-02",
        "end_date": "2026-11-02",
        "purpose": "Family",
        "reference": "ORDER-101",
        "evidence": "Signed order attachment",
        "unavailable_context": "ELM outage ticket INC-101",
        "already_sanctioned": True,
        "approved_at": "2026-10-25T12:00:00Z",
    }


def test_offline_debits_once_without_second_sanction(stub_iam):
    leave_type, _applicant = seed()
    client = api_as(stub_iam, 201, ("elm.leave_records.manage",))

    payload = offline_payload(leave_type)
    response = client.post("/api/v1/elm/requests/offline-sync/", payload, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "APPROVED"

    balance = LeaveBalance.objects.get(employee="101", leave_type=leave_type, year=2026)
    assert balance.balance == 7
    assert LeaveRequest.objects.filter(employee="101").count() == 1
    assert LeaveEvent.objects.filter(action="OFFLINE_SYNCHRONIZED").count() == 1

    response = client.post("/api/v1/elm/requests/offline-sync/", payload, format="json")
    assert response.status_code == 400
    balance = LeaveBalance.objects.get(employee="101", leave_type=leave_type, year=2026)
    assert balance.balance == 7


@pytest.mark.parametrize(
    "field,value",
    [
        ("already_sanctioned", False),
        ("evidence", "   "),
        ("unavailable_context", ""),
        ("approved_at", "2027-01-01T00:00:00Z"),
    ],
)
def test_offline_requires_valid_prior_sanction(stub_iam, field, value):
    leave_type, _applicant = seed()
    admin_client = api_as(stub_iam, 201, ("elm.leave_records.manage",))
    payload = offline_payload(leave_type)
    payload[field] = value
    response = admin_client.post("/api/v1/elm/requests/offline-sync/", payload, format="json")
    assert response.status_code == 400
    assert not LeaveRequest.objects.exists()
    assert not LeaveBalance.objects.exists()


def test_offline_requires_record_permission(stub_iam):
    leave_type, _applicant = seed()
    employee_client = api_as(stub_iam, 101, ("elm.leave_requests.apply",))
    payload = offline_payload(leave_type)
    response = employee_client.post("/api/v1/elm/requests/offline-sync/", payload, format="json")
    assert response.status_code == 403
    assert not LeaveRequest.objects.exists()
