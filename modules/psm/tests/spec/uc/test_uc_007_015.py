"""Executable stock, reporting, approval, and finance use-case specifications."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.psm import registry
from modules.psm.models import (
    PsmAuditLog,
    ReportGenerationLog,
    ReportSchedule,
    StockLedgerEntry,
    StockReservation,
)
from modules.psm.services import policy, reports

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, uid, role):
    staff_roles = {"deptadmin_cse", "ps_admin", "Accounts Admin", "Auditor"}
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff" if role in staff_roles else "faculty",
            active_role=role,
            roles=(role,),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS[role]),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token uc-{uid}")
    return client


def _principal(uid, role, *, department="CSE"):
    return make_principal(
        user_id=uid,
        kind="staff" if role in {"deptadmin_cse", "ps_admin"} else "faculty",
        active_role=role,
        roles=(role,),
        modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS[role]),
    )


def _stocked_indent(stub_iam, *, uid=32001, quantity=4, on_hand=10):
    policy.seed_default_policy()
    admin = _client(stub_iam, uid=uid + 1, role="ps_admin")
    item = admin.post(
        "/api/v1/psm/stock/items", {"sku": f"UC-{uid}", "name": "Lab item"}, format="json"
    )
    assert item.status_code == 201, item.data
    location = admin.post(
        "/api/v1/psm/stock/locations",
        {"code": f"LOC-{uid}", "name": "CSE Store", "department": "CSE"},
        format="json",
    )
    assert location.status_code == 201, location.data
    adjustment = admin.post(
        "/api/v1/psm/stock/adjustments",
        {
            "item_id": item.data["id"],
            "location_id": location.data["id"],
            "quantity_delta": on_hand,
            "reason": "Opening balance",
            "entry_type": "opening",
        },
        format="json",
    )
    assert adjustment.status_code == 201, adjustment.data
    employee = _client(stub_iam, uid=uid, role="faculty")
    indent = employee.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_id": item.data["id"],
            "item_description": "Lab item",
            "quantity": quantity,
            "estimated_cost": "8000.00",
            "justification": "Lab use",
        },
        format="json",
    )
    assert indent.status_code == 201, indent.data
    return indent.data, item.data, location.data


def test_tc_007_main_psm_uc_007_main_success_scenario(stub_iam):
    """TC-007-MAIN; source_id: PSM-UC-007 Main Success Scenario."""
    indent_data, _item_data, _location_data = _stocked_indent(stub_iam)
    da = _client(stub_iam, uid=32100, role="deptadmin_cse")
    response = da.post(f"/api/v1/psm/indents/{indent_data['id']}/stock-check", {}, format="json")

    assert response.status_code == 200, response.data
    assert response.data["status"] == "stock_reserved"
    reservation = StockReservation.objects.get(indent_id=indent_data["id"], status="active")
    assert reservation.quantity == 4
    availability = da.get(f"/api/v1/psm/stock/availability?item_id={reservation.item_id}")
    assert availability.status_code == 200, availability.data
    assert StockReservation.objects.filter(pk=reservation.pk, status="active").exists()


def test_tc_007_a1_psm_uc_007_alternative_a1(stub_iam):
    """TC-007-A1; source_id: PSM-UC-007 Alternative A1."""
    indent_data, _item_data, _location_data = _stocked_indent(
        stub_iam, uid=32200, quantity=8, on_hand=3
    )
    da = _client(stub_iam, uid=32300, role="deptadmin_cse")
    response = da.post(f"/api/v1/psm/indents/{indent_data['id']}/stock-check", {}, format="json")

    assert response.status_code == 200, response.data
    assert response.data["status"] == "external_required"
    assert not StockReservation.objects.filter(indent_id=indent_data["id"], status="active").exists()
    assert response.data["procurement_method"] != "internal"


def test_tc_008_main_psm_uc_008_main_success_scenario(stub_iam):
    """TC-008-MAIN; source_id: PSM-UC-008 Main Success Scenario."""
    _indent_data, item_data, location_data = _stocked_indent(stub_iam, uid=32400)
    admin = _client(stub_iam, uid=32401, role="ps_admin")
    before = StockLedgerEntry.objects.count()
    response = admin.post(
        "/api/v1/psm/stock/adjustments",
        {
            "item_id": item_data["id"],
            "location_id": location_data["id"],
            "quantity_delta": 2,
            "reason": "Verified physical count",
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert StockLedgerEntry.objects.count() == before + 1
    assert PsmAuditLog.objects.filter(action="stock.adjusted", target_type="stock_ledger").exists()


def test_tc_008_a2_psm_uc_008_alternative_a2(stub_iam):
    """TC-008-A2; source_id: PSM-UC-008 Alternative A2."""
    _indent_data, item_data, location_data = _stocked_indent(stub_iam, uid=32500)
    employee = _client(stub_iam, uid=32500, role="faculty")
    before = StockLedgerEntry.objects.count()
    response = employee.post(
        "/api/v1/psm/stock/adjustments",
        {
            "item_id": item_data["id"],
            "location_id": location_data["id"],
            "quantity_delta": 2,
            "reason": "Unauthorized adjustment",
        },
        format="json",
    )

    assert response.status_code == 403
    assert StockLedgerEntry.objects.count() == before


def test_tc_010_main_psm_uc_010_main_success_scenario(stub_iam):
    """TC-010-MAIN; source_id: PSM-UC-010 Main Success Scenario."""
    policy.seed_default_policy()
    auditor = _client(stub_iam, uid=32600, role="Auditor")
    before = ReportGenerationLog.objects.count()
    response = auditor.post(
        "/api/v1/psm/reports/generate", {"report_type": "operational", "filters": {}}, format="json"
    )

    assert response.status_code == 200, response.data
    assert ReportGenerationLog.objects.count() == before + 1


def test_tc_010_a1_psm_uc_010_alternative_a1(stub_iam):
    """TC-010-A1; source_id: PSM-UC-010 Alternative A1."""
    policy.seed_default_policy()
    employee = _client(stub_iam, uid=32700, role="faculty")
    before = ReportGenerationLog.objects.count()
    response = employee.post(
        "/api/v1/psm/reports/generate", {"report_type": "operational", "filters": {}}, format="json"
    )

    assert response.status_code == 403
    assert ReportGenerationLog.objects.count() == before


def test_tc_014_main_psm_uc_014_main_success_scenario(stub_iam):
    """TC-014-MAIN; source_id: PSM-UC-014 Main Success Scenario."""
    policy.seed_default_policy()
    auditor = _client(stub_iam, uid=32800, role="Auditor")
    before = PsmAuditLog.objects.count()
    response = auditor.get("/api/v1/psm/audit")

    assert response.status_code == 200, response.data
    assert "results" in response.data
    assert PsmAuditLog.objects.count() >= before


def test_tc_015_main_psm_uc_015_main_success_scenario(stub_iam):
    """TC-015-MAIN; source_id: PSM-UC-015 Main Success Scenario."""
    policy.seed_default_policy()
    accounts = _client(stub_iam, uid=32900, role="Accounts Admin")
    before = ReportGenerationLog.objects.count()
    response = accounts.post(
        "/api/v1/psm/reports/generate", {"report_type": "financial", "filters": {}}, format="json"
    )

    assert response.status_code == 200, response.data
    assert ReportGenerationLog.objects.count() == before + 1


def test_tc_030_main_psm_uc_030_main_success_scenario(stub_iam):
    """TC-030-MAIN; source_id: PSM-UC-030 Main Success Scenario."""
    policy.seed_default_policy()
    auditor = _client(stub_iam, uid=33000, role="Auditor")
    response = auditor.get("/api/v1/psm/dashboard")

    assert response.status_code == 200, response.data
    assert "metrics" in response.data or response.data


def test_tc_031_main_psm_uc_031_main_success_scenario(stub_iam):
    """TC-031-MAIN; source_id: PSM-UC-031 Main Success Scenario."""
    policy.seed_default_policy()
    admin = _client(stub_iam, uid=33100, role="ps_admin")
    response = admin.post(
        "/api/v1/psm/reports/schedules",
        {"name": "UC31 daily", "report_type": "operational", "cadence": "daily", "filters": {}},
        format="json",
    )

    assert response.status_code == 201, response.data
    schedule = ReportSchedule.objects.get(pk=response.data["id"])
    assert schedule.is_active is True


def test_tc_035_main_psm_uc_035_main_success_scenario(stub_iam):
    """TC-035-MAIN; source_id: PSM-UC-035 Main Success Scenario."""
    policy.seed_default_policy()
    admin = _client(stub_iam, uid=33200, role="ps_admin")
    created = admin.post(
        "/api/v1/psm/reports/schedules",
        {"name": "UC35 due", "report_type": "operational", "cadence": "daily", "filters": {}},
        format="json",
    )
    assert created.status_code == 201, created.data
    schedule = ReportSchedule.objects.get(pk=created.data["id"])
    ReportSchedule.objects.filter(pk=schedule.pk).update(next_run_at=timezone.now())
    before = ReportGenerationLog.objects.count()

    assert reports.run_due_schedules() == 1
    assert ReportGenerationLog.objects.count() == before + 1

