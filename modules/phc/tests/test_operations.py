from datetime import UTC

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import AmbulanceUsage, HealthAdvisory

pytestmark = pytest.mark.django_db


def _client(stub_iam, role, permissions, user_id=2001, kind="staff"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("phc",),
                          permissions=permissions, roles=(role,), active_role=role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-operations")
    return client


# PHC-UC-12; CFR-PHC-009; AFR-PHC-033.
def test_phc_uc_12_advisory_is_published_to_patients(stub_iam):
    HealthAdvisory.objects.create(title="Published", body="Current guidance",
        published_at="2026-11-23T00:00:00Z", published_by_user_id=2001)
    HealthAdvisory.objects.create(title="Draft", body="Unpublished guidance")
    patient = _client(stub_iam, "student", ["phc.advisory.view"], 1001, "student")

    response = patient.get("/api/v1/phc/advisories")

    assert response.status_code == 200
    assert [row["title"] for row in response.json()["results"]] == ["Published"]


# PHC-UC-11; CFR-PHC-008; AFR-PHC-032.
def test_phc_uc_11_records_ambulance_usage_and_phc_uc_13_reports_aggregates(
        stub_iam):
    staff = _client(stub_iam, "Compounder", [
        "phc.ambulance_usage.create", "phc.ambulance_usage.view",
        "phc.report.view",
    ])
    created = staff.post("/api/v1/phc/ambulance-usage", {
        "used_at": "2026-11-23T10:30:00+05:30",
        "patient_name": "Test Patient", "destination": "City Hospital",
    }, format="json")
    assert created.status_code == 201
    assert AmbulanceUsage.objects.count() == 1
    report = staff.get("/api/v1/phc/reports/ambulance")
    assert report.status_code == 200
    assert report.json()["data"]["by_month"][0]["count"] == 1
    assert "Test Patient" not in report.content.decode()


# PHC-BR-12; PHC-UC-13; CFR-PHC-010; AFR-PHC-034; AFR-PHC-035.
def test_phc_br_12_uc_13_all_aggregate_reports_exclude_identifying_fields(stub_iam):
    from datetime import date

    from modules.directory.models import UserRef
    from modules.phc.models import InventoryItem, PatientVisit
    from modules.phc.services.inventory import adjust_stock

    UserRef.objects.create(user_id=1001, username="member", display_name="Member",
                           kind="faculty")
    PatientVisit.objects.create(patient_user_id=1001, visited_on=date.today(),
        notes="private text", recorded_by_user_id=2001)
    item = InventoryItem.objects.create(name="Gauze", reorder_threshold=2)
    adjust_stock(item_id=item.pk, quantity_delta=5, reason="Delivery", actor_user_id=2001)
    adjust_stock(item_id=item.pk, quantity_delta=-2, reason="Dispensed", actor_user_id=2001)
    staff = _client(stub_iam, "Compounder", ["phc.report.view"])
    for name in ("visits", "inventory", "ambulance", "reimbursements", "demographics"):
        response = staff.get(f"/api/v1/phc/reports/{name}")
        assert response.status_code == 200
        content = response.content.decode()
        assert "1001" not in content
        assert "Member" not in content
        assert "private text" not in content


def test_phc_uc_13_rejects_unknown_report_and_lists_only_callers_notifications(
        stub_iam):
    from modules.phc.models import Notification, NotificationOutbox

    outbox = NotificationOutbox.objects.create(
        event_key="claim:90:pending", recipient_user_id=1001,
        event_type="reimbursement_status",
        payload={"target_type": "reimbursement_claim", "target_id": 90},
    )
    Notification.objects.create(
        recipient_user_id=1001, event_type="reimbursement_status",
        message="Your claim is pending.", target_type="reimbursement_claim",
        target_id=90, outbox=outbox,
    )
    other = NotificationOutbox.objects.create(
        event_key="claim:91:pending", recipient_user_id=1002,
        event_type="reimbursement_status",
        payload={"target_type": "reimbursement_claim", "target_id": 91},
    )
    Notification.objects.create(
        recipient_user_id=1002, event_type="reimbursement_status",
        message="Another claim is pending.", target_type="reimbursement_claim",
        target_id=91, outbox=other,
    )
    compounder = _client(stub_iam, "Compounder", [
        "phc.report.view", "phc.notification.view",
    ], user_id=1001)
    invalid = compounder.get("/api/v1/phc/reports/unlisted")
    assert invalid.status_code == 400
    own = compounder.get("/api/v1/phc/notifications")
    assert [row["target_id"] for row in own.json()["results"]] == [90]


def test_phc_uc_11_ambulance_history_is_available_to_compounder(stub_iam):
    from datetime import datetime

    AmbulanceUsage.objects.create(
        used_at=datetime(2026, 11, 23, 10, 0, tzinfo=UTC),
        patient_name="Test Patient", destination="Hospital", recorded_by_user_id=2001,
    )
    compounder = _client(stub_iam, "Compounder", ["phc.ambulance_usage.view"])
    response = compounder.get("/api/v1/phc/ambulance-usage")
    assert response.status_code == 200
    assert response.json()["results"][0]["destination"] == "Hospital"
