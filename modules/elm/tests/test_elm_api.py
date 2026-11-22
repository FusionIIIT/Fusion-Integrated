import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication, LeaveStatus, LeaveType

pytestmark = pytest.mark.django_db

ALL_ELM_PERMISSIONS = (
    "elm.leave.view_self",
    "elm.leave.apply",
    "elm.leave.withdraw",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
    "elm.substitute.respond",
    "elm.leave.review_unit_head",
    "elm.leave.sanction_final",
    "elm.admin.record_offline",
    "elm.admin.yearend_process",
    "elm.admin.manage",
)


def _client(stub_iam, user_id=1001, roles=("faculty",), permissions=ALL_ELM_PERMISSIONS):
    stub_iam(make_session(
        user_id=user_id,
        modules=("elm",),
        permissions=permissions,
        roles=roles,
        active_role=roles[0] if roles else "faculty",
    ))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


class TestELMAPIEndpoints:
    def test_get_balances_api(self, stub_iam):
        c = _client(stub_iam, user_id=1001)
        response = c.get("/api/v1/elm/balances")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        types = [b["leave_type"] for b in data]
        assert "CL" in types
        assert "RH" in types

    def test_apply_and_withdraw_api(self, stub_iam):
        c = _client(stub_iam, user_id=1002)
        payload = {
            "leave_type": "CL",
            "start_date": "2026-05-10",
            "end_date": "2026-05-11",
            "reason": "Personal work",
        }
        res = c.post("/api/v1/elm/applications", payload, format="json")
        assert res.status_code == 201
        app_id = res.json()["id"]
        assert res.json()["status"] == LeaveStatus.AWAITING_UNIT_HEAD

        # Withdraw application
        res_with = c.post(f"/api/v1/elm/applications/{app_id}/withdraw", {"reason": "Change of mind"}, format="json")
        assert res_with.status_code == 200
        assert res_with.json()["status"] == LeaveStatus.WITHDRAWN

    def test_unit_head_and_sanction_api(self, stub_iam):
        # 1. Employee applies for SCL
        c_emp = _client(stub_iam, user_id=1003)
        payload = {
            "leave_type": "SCL",
            "start_date": "2026-06-15",
            "end_date": "2026-06-16",
            "reason": "Academic workshop",
        }
        res = c_emp.post("/api/v1/elm/applications", payload, format="json")
        assert res.status_code == 201
        app_id = res.json()["id"]

        # 2. Unit Head reviews & recommends
        c_hod = _client(stub_iam, user_id=2001, roles=("hod",))
        res_rec = c_hod.post(f"/api/v1/elm/approvals/unit-head/{app_id}/review", {"action": "recommend", "remarks": "Looks good"}, format="json")
        assert res_rec.status_code == 200
        assert res_rec.json()["status"] == LeaveStatus.AWAITING_SANCTION

        # 3. Sanctioning authority approves
        c_dean = _client(stub_iam, user_id=3001, roles=("dean",))
        res_sanc = c_dean.post(f"/api/v1/elm/approvals/sanction/{app_id}/review", {"action": "approve", "remarks": "Approved by Dean"}, format="json")
        assert res_sanc.status_code == 200
        assert res_sanc.json()["status"] == LeaveStatus.APPROVED

    def test_admin_offline_and_yearend_api(self, stub_iam):
        c_admin = _client(stub_iam, user_id=9001, roles=("establishment_admin",))

        # Record offline leave
        offline_payload = {
            "employee_id": "emp_offline",
            "is_faculty": False,
            "leave_type": "EL",
            "start_date": "2026-02-01",
            "end_date": "2026-02-03",
            "offline_sanction_ref": "OFF/PAPER/999",
            "reason": "Pre-approved paper leave",
        }
        res = c_admin.post("/api/v1/elm/admin/offline-leave", offline_payload, format="json")
        assert res.status_code == 201
        assert res.json()["status"] == LeaveStatus.APPROVED

        # Year end processing
        res_ye = c_admin.post("/api/v1/elm/admin/year-end-process", {"year": 2026}, format="json")
        assert res_ye.status_code == 200
        assert "lapsed" in res_ye.json()

        # SLA check trigger
        res_sla = c_admin.post("/api/v1/elm/admin/sla-check", {}, format="json")
        assert res_sla.status_code == 200
        assert "reminded" in res_sla.json()
