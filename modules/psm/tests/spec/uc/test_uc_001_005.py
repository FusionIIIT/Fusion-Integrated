"""Executable specifications for indent submission, tracking, and withdrawal."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import DomainError
from modules.psm import registry
from modules.psm.models import Indent, IndentVersion, PsmAuditLog, PsmNotification
from modules.psm.services import indents, policy

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, uid, role="faculty"):
    staff_roles = {"deptadmin_cse", "ps_admin"}
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


def _principal(uid):
    return make_principal(
        user_id=uid,
        kind="faculty",
        active_role="faculty",
        roles=("faculty",),
        modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS["faculty"]),
    )


def _submitted(client, *, item="Microscope", justification="Teaching lab"):
    response = client.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": item,
            "quantity": 2,
            "estimated_cost": "12000.00",
            "justification": justification,
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def test_tc_001_main_psm_uc_001_main_success_scenario(stub_iam):
    """TC-001-MAIN; source_id: PSM-UC-001 Main Success Scenario."""
    policy.seed_default_policy()
    employee = _client(stub_iam, uid=31001)
    result = _submitted(employee)

    indent = Indent.objects.get(pk=result["id"])
    assert result["status"] == "submitted"
    assert result["indent_number"]
    assert indent.submitted_at is not None
    assert Indent.objects.filter(indent_number=result["indent_number"]).count() == 1
    assert IndentVersion.objects.filter(indent=indent, version=1).exists()
    assert PsmAuditLog.objects.filter(target_type="indent", target_id=indent.pk).exists()
    assert PsmNotification.objects.filter(payload__indent_id=indent.pk).exists()


def test_tc_001_a1_psm_uc_001_alternative_a1(stub_iam):
    """TC-001-A1; source_id: PSM-UC-001 Alternative A1."""
    policy.seed_default_policy()
    employee = _principal(31002)
    before = Indent.objects.count()
    with pytest.raises(DomainError) as refused:
        indents.create_indent(actor=employee, department="CSE", item_description="", quantity=2,
            estimated_cost=Decimal("12000.00"), justification="Teaching lab")
    assert refused.value.status_code == 422
    assert "item_description" in str(refused.value.details)
    assert Indent.objects.count() == before


def test_tc_001_a2_psm_uc_001_alternative_a2(stub_iam):
    """TC-001-A2; source_id: PSM-UC-001 Alternative A2."""
    policy.seed_default_policy()
    employee = _client(stub_iam, uid=31003)
    first = _submitted(employee, item="Lab Sensor", justification="Initial request")
    duplicate = _submitted(employee, item="Lab Sensor", justification="Replacement request")

    assert duplicate["id"] != first["id"]
    assert duplicate["is_duplicate_flagged"] is True
    assert Indent.objects.get(pk=duplicate["id"]).status == "submitted"
    assert Indent.objects.filter(pk=first["id"]).exists()


def test_tc_001_a3_psm_uc_001_alternative_a3(stub_iam):
    """TC-001-A3; source_id: PSM-UC-001 Alternative A3."""
    policy.seed_default_policy()
    admin = _client(stub_iam, uid=31004, role="ps_admin")
    item_response = admin.post(
        "/api/v1/psm/stock/items", {"sku": "UC001-A3", "name": "Lab Sensor"}, format="json"
    )
    assert item_response.status_code == 201, item_response.data
    location = admin.post(
        "/api/v1/psm/stock/locations",
        {"code": "UC001-A3", "name": "CSE Store", "department": "CSE"},
        format="json",
    )
    assert location.status_code == 201, location.data
    adjustment = admin.post(
        "/api/v1/psm/stock/adjustments",
        {
            "item_id": item_response.data["id"],
            "location_id": location.data["id"],
            "quantity_delta": 4,
            "reason": "Opening balance",
            "entry_type": "opening",
        },
        format="json",
    )
    assert adjustment.status_code == 201, adjustment.data
    employee = _client(stub_iam, uid=31005)
    response = employee.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_id": item_response.data["id"],
            "item_description": "Lab Sensor",
            "quantity": 1,
            "estimated_cost": "5000.00",
            "justification": "Teaching lab",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    department_admin = _client(stub_iam, uid=31009, role="deptadmin_cse")
    stock_check = department_admin.post(
        f"/api/v1/psm/indents/{response.data['id']}/stock-check", {}, format="json"
    )
    assert stock_check.status_code == 200, stock_check.data
    assert stock_check.data["status"] == "stock_reserved"
    assert PsmNotification.objects.filter(
        recipient_user_id=31005, topic="indent.stock_available"
    ).exists()


def test_tc_003_main_psm_uc_003_main_success_scenario(stub_iam):
    """TC-003-MAIN; source_id: PSM-UC-003 Main Success Scenario."""
    policy.seed_default_policy()
    employee = _client(stub_iam, uid=31006)
    created = _submitted(employee)
    before = Indent.objects.get(pk=created["id"])
    before_state = (before.status, before.version, before.updated_at)

    response = employee.get(f"/api/v1/psm/indents/{created['id']}")
    assert response.status_code == 200, response.data
    assert response.data["status"] == "submitted"
    assert response.data["transitions"]
    after = Indent.objects.get(pk=created["id"])
    assert (after.status, after.version, after.updated_at) == before_state


def test_tc_003_a1_psm_uc_003_alternative_a1(stub_iam):
    """TC-003-A1; source_id: PSM-UC-003 Alternative A1."""
    policy.seed_default_policy()
    employee = _client(stub_iam, uid=31007)
    created = _submitted(employee)
    response = employee.get(f"/api/v1/psm/indents/{created['id']}")
    assert response.status_code == 200, response.data
    assert "bank_account_number" not in response.data
    assert "vendor_compliance_documents" not in response.data


def test_tc_005_main_psm_uc_005_main_success_scenario():
    """TC-005-MAIN; source_id: PSM-UC-005 Main Success Scenario."""
    policy.seed_default_policy()
    actor = _principal(31008)
    created = indents.create_indent(
        actor=actor,
        department="CSE",
        item_description="Pending item",
        quantity=1,
        estimated_cost=Decimal("500.00"),
        justification="Lab use",
    )

    withdrawn = indents.withdraw_indent(actor=actor, indent_id=created.pk, reason="No longer needed")
    withdrawn.refresh_from_db()
    assert withdrawn.status == "withdrawn"
    assert withdrawn.transitions.filter(to_status="withdrawn").exists()
    assert PsmNotification.objects.filter(
        recipient_user_id=actor.user_id, topic="indent.withdrawn"
    ).exists()


def test_tc_005_a1_psm_uc_005_alternative_a1():
    """TC-005-A1; source_id: PSM-UC-005 Alternative A1."""
    from core.api.exceptions import ConflictError

    policy.seed_default_policy()
    actor = _principal(31010)
    created = indents.create_indent(
        actor=actor,
        department="CSE",
        item_description="Pending item",
        quantity=1,
        estimated_cost=Decimal("500.00"),
        justification="Lab use",
    )
    Indent.objects.filter(pk=created.pk).update(status="po_issued")
    created.refresh_from_db()
    prior = (created.status, created.version, created.updated_at)

    with pytest.raises(ConflictError) as refused:
        indents.withdraw_indent(actor=actor, indent_id=created.pk, reason="Withdraw")
    assert refused.value.status_code == 409

    created.refresh_from_db()
    assert (created.status, created.version, created.updated_at) == prior

