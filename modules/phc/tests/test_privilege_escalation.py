"""Both gates on every endpoint, separately: module grant, then permission (AFR-PHC-036)."""
import pytest
from rest_framework.test import APIClient

from modules.phc.api.urls import urlpatterns
from modules.phc.tests.factories import (
    ACCOUNTS_ID,
    AUTHORITY_ID,
    EMPLOYEE_ID,
    PHC_STAFF_ID,
    STUDENT_ID,
    client_as,
    item,
)

pytestmark = pytest.mark.django_db

# (method, path, the permission that admits it); ids are irrelevant to the gates.
ENDPOINTS = [
    ("get", "/api/v1/phc/schedules", "phc.schedule.view"),
    ("post", "/api/v1/phc/schedules", "phc.schedule.create"),
    ("put", "/api/v1/phc/schedules/1", "phc.schedule.update"),
    ("post", "/api/v1/phc/schedules/1/publish", "phc.schedule.publish"),
    ("post", "/api/v1/phc/schedules/1/attendance", "phc.attendance.update"),
    ("get", "/api/v1/phc/patients", "phc.patient.view"),
    ("get", "/api/v1/phc/records", "phc.record.view"),
    ("post", "/api/v1/phc/records", "phc.record.create"),
    ("get", "/api/v1/phc/records/1", "phc.record.view"),
    ("get", "/api/v1/phc/records/pdf", "phc.record.view"),
    ("get", "/api/v1/phc/claims", "phc.claim.view"),
    ("post", "/api/v1/phc/claims", "phc.claim.create"),
    ("get", "/api/v1/phc/claims/prescriptions", "phc.claim.create"),
    ("get", "/api/v1/phc/claims/1", "phc.claim.view"),
    ("post", "/api/v1/phc/claims/1/transition", "phc.claim.review"),
    ("get", "/api/v1/phc/inventory", "phc.inventory.view"),
    ("post", "/api/v1/phc/inventory", "phc.inventory.create"),
    ("get", "/api/v1/phc/inventory/alerts", "phc.inventory.view"),
    ("post", "/api/v1/phc/inventory/1/adjust", "phc.inventory.update"),
    ("get", "/api/v1/phc/requisitions", "phc.requisition.view"),
    ("post", "/api/v1/phc/requisitions", "phc.requisition.create"),
    ("post", "/api/v1/phc/requisitions/1/transition", "phc.requisition.approve"),
    ("get", "/api/v1/phc/ambulance", "phc.ambulance.view"),
    ("post", "/api/v1/phc/ambulance", "phc.ambulance.create"),
    ("get", "/api/v1/phc/advisories", "phc.advisory.view"),
    ("post", "/api/v1/phc/advisories", "phc.advisory.publish"),
    ("get", "/api/v1/phc/reports", "phc.report.view"),
    ("get", "/api/v1/phc/notifications", "phc.notification.view"),
]


def test_every_route_is_in_the_table():
    covered = {path.split("/api/v1/phc/")[1].replace("/1", "/<int:pk>")
               for _, path, _ in ENDPOINTS}
    assert {str(p.pattern) for p in urlpatterns} == covered


def _call(client, method, path):
    return getattr(client, method)(path, {}, format="json")


@pytest.mark.parametrize(("method", "path", "permission"), ENDPOINTS)
def test_no_session_is_401(method, path, permission, stub_iam):
    assert _call(APIClient(), method, path).status_code == 401


@pytest.mark.parametrize(("method", "path", "permission"), ENDPOINTS)
def test_permission_without_module_grant_is_403(method, path, permission, stub_iam):
    from conftest import make_session

    stub_iam(make_session(user_id=PHC_STAFF_ID, kind="staff", modules=(),
                          permissions=(permission,)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    r = _call(client, method, path)
    assert r.status_code == 403
    assert r.data["error"]["code"] == "permission_denied"


@pytest.mark.parametrize(("method", "path", "permission"), ENDPOINTS)
def test_module_grant_without_permission_is_403(method, path, permission, stub_iam):
    from conftest import make_session

    stub_iam(make_session(user_id=PHC_STAFF_ID, kind="staff", modules=("phc",),
                          permissions=()))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    assert _call(client, method, path).status_code == 403


# PHC-BR-03, CFR-PHC-011
def test_plain_student_reaches_only_patient_screens_phc_br_03(stub_iam):
    student = client_as(stub_iam, "student", STUDENT_ID)
    for method, path, permission in ENDPOINTS:
        status = _call(student, method, path).status_code
        if permission in ("phc.schedule.view", "phc.record.view", "phc.advisory.view",
                          "phc.notification.view"):
            assert status != 403, path
        else:
            assert status == 403, path


def test_employee_can_claim_but_not_process(stub_iam):
    employee = client_as(stub_iam, "faculty", EMPLOYEE_ID)
    assert employee.get("/api/v1/phc/claims").status_code == 200
    assert employee.get("/api/v1/phc/inventory").status_code == 403
    assert employee.get("/api/v1/phc/reports").status_code == 403


def test_accounts_cannot_touch_clinical_or_stock(stub_iam):
    accounts = client_as(stub_iam, "Accounts & Audit", ACCOUNTS_ID)
    assert accounts.get("/api/v1/phc/records").status_code == 403
    assert accounts.post(f"/api/v1/phc/inventory/{item().pk}/adjust",
                         {"delta": "1"}).status_code == 403


def test_authority_cannot_fulfil_or_raise_requisitions(stub_iam):
    authority = client_as(stub_iam, "Approving Authority", AUTHORITY_ID)
    assert authority.post("/api/v1/phc/requisitions", {"purpose": "x", "lines": []},
                          format="json").status_code == 403


def test_role_switch_gives_only_the_acting_roles_view(stub_iam):
    from conftest import make_session
    from modules.phc.registry import ROLE_GRANTS

    # Holds faculty and Approving Authority; acting as faculty must not approve anything.
    stub_iam(make_session(user_id=AUTHORITY_ID, kind="faculty", modules=("phc",),
                          permissions=ROLE_GRANTS["faculty"],
                          roles=("faculty", "Approving Authority"), active_role="faculty"))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    assert client.get("/api/v1/phc/requisitions").status_code == 403
    assert client.post("/api/v1/phc/requisitions/1/transition",
                       {"event": "approve"}).status_code == 403


def test_cookie_write_without_csrf_header_is_403(stub_iam, settings):
    from conftest import make_session
    from modules.phc.registry import ROLE_GRANTS

    stub_iam(make_session(user_id=PHC_STAFF_ID, kind="staff", modules=("phc",),
                          permissions=ROLE_GRANTS["PHC Staff"]))
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "cookie-token"
    r = client.post("/api/v1/phc/advisories", {"title": "t", "body": "b"}, format="json")
    assert r.status_code == 403


def test_write_endpoints_are_throttled(stub_iam, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES",
                        {**SimpleRateThrottle.THROTTLE_RATES, "phc_write": "2/hour"})
    staff = client_as(stub_iam, "PHC Staff", PHC_STAFF_ID)
    codes = [staff.post("/api/v1/phc/advisories", {"title": "t", "body": "b"}).status_code
             for _ in range(3)]
    assert codes == [201, 201, 429]
    assert staff.get("/api/v1/phc/advisories").status_code == 200
