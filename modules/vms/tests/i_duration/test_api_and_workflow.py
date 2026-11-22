"""Endpoint auth matrix and the BW-VMS-23 / acceptance scenario."""
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.vms.models import ExtensionRequest, VisitLog
from modules.vms.services import autocheckout
from modules.vms.tests import factories as f

from .conftest import ADMIN, HOST, OTHER, on_site_pass

pytestmark = pytest.mark.django_db
BASE = "/api/v1/vms/extensions"
T0 = "2026-03-02 09:00:00+00:00"

ENDPOINTS = [
    ("post", BASE, "vms.request.decide"),
    ("get", BASE, "vms.request.decide"),
    ("get", BASE + "/1", "vms.request.decide"),
    ("post", BASE + "/1/decision", "vms.extension.decide"),
]


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_anonymous_is_401(api_as, method, path, perm):
    assert getattr(api_as(anonymous=True), method)(path, {}, format="json").status_code == 401


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_wrong_role_is_403(api_as, method, path, perm):
    client = api_as(permissions=["vms.report.view"])
    assert getattr(client, method)(path, {}, format="json").status_code == 403


def test_host_without_decide_permission_is_403_on_decision(api_as):
    assert api_as(user_id=HOST, permissions=["vms.request.decide"]).post(
        BASE + "/1/decision", {"decision": "approve"}, format="json").status_code == 403


@freeze_time(T0)
def test_wrong_owner_is_404(api_as):
    vp = on_site_pass()
    body = {"request_id": vp.visit_request_id,
            "new_end": (timezone.now() + timedelta(hours=3)).isoformat()}
    other = api_as(user_id=OTHER, kind="faculty", permissions=["vms.request.decide"])
    assert other.post(BASE, body, format="json").status_code == 404
    ext = f.make_extension_request(visit_request=vp.visit_request)
    assert other.get(f"{BASE}/{ext.pk}").status_code == 404
    assert other.get(BASE).json() == []


@freeze_time(T0)
def test_bw_vms_23_admin_approved_extension(api_as):
    """Host asks beyond the cap -> Admin approves -> extended validity active ->
    auto check-out at the NEW end; sweep run twice fires once."""
    f.make_role_assignment(user_id=ADMIN, role="admin")
    vp = on_site_pass(hours=2)
    host = api_as(user_id=HOST, kind="faculty", permissions=["vms.request.decide"])
    admin = api_as(user_id=ADMIN, permissions=["vms.extension.decide"])
    new_end = timezone.now() + timedelta(hours=10)             # cap is 8 h

    res = host.post(BASE, {"request_id": vp.visit_request_id, "new_end": new_end.isoformat(),
                           "reason": "Audit ran long"}, format="json")
    assert res.status_code == 201 and res.json()["status"] == "pending"
    ext_id = res.json()["id"]
    assert [r["id"] for r in host.get(BASE + "?status=pending").json()] == [ext_id]
    assert [r["id"] for r in admin.get(BASE).json()] == [ext_id]

    # The Admin decides before the original end (a pending extension does not hold the visitor).
    with freeze_time("2026-03-02 10:00:00+00:00"):
        assert autocheckout.sweep() == 0
        res = admin.post(f"{BASE}/{ext_id}/decision",
                         {"decision": "approve", "note": "ok"}, format="json")
        assert res.status_code == 200 and res.json()["status"] == "approved"
    vp.refresh_from_db()
    vp.visit_request.refresh_from_db()
    assert vp.valid_until == vp.visit_request.scheduled_end == new_end

    with freeze_time("2026-03-02 12:00:00+00:00"):             # old end passed: nothing fires
        assert autocheckout.sweep() == 0
    with freeze_time("2026-03-02 19:00:00+00:00"):             # new end reached
        assert autocheckout.sweep() == 1
        assert autocheckout.sweep() == 0                       # second run: no double fire
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"
    assert VisitLog.objects.filter(visit_pass=vp, event="auto_check_out").count() == 1
    assert ExtensionRequest.objects.get(pk=ext_id).status == "approved"


@freeze_time(T0)
def test_decision_validation_and_double_decision(api_as):
    f.make_role_assignment(user_id=ADMIN, role="admin")
    vp = on_site_pass()
    ext = f.make_extension_request(visit_request=vp.visit_request,
                                   requested_end=timezone.now() + timedelta(hours=10))
    admin = api_as(user_id=ADMIN, permissions=["vms.extension.decide"])
    assert admin.post(f"{BASE}/{ext.pk}/decision", {"decision": "maybe"},
                      format="json").status_code == 400
    assert admin.post(f"{BASE}/{ext.pk}/decision", {"decision": "reject"},
                      format="json").status_code == 200
    assert admin.post(f"{BASE}/{ext.pk}/decision", {"decision": "approve"},
                      format="json").status_code == 409
