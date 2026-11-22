import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    InventoryItem,
    InventoryRequisition,
    NotificationOutbox,
    PHCAuditEvent,
    RequisitionLine,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id, role, permissions):
    stub_iam(make_session(user_id=user_id, kind="staff", modules=("phc",),
                          permissions=permissions, roles=(role,), active_role=role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-requisition")
    return client


# PHC-BR-10; PHC-BR-11; PHC-UC-10; PHC-UC-14; PHC-UC-16; BW-PHC-03; CW-PHC-02; CFR-PHC-007; AFR-PHC-027; AFR-PHC-028; AFR-PHC-029; AFR-PHC-030; AFR-PHC-031.
def test_phc_br_10_br_11_uc_10_uc_14_uc_16_bw_phc_03_cw_phc_02_requisition_journey(
        stub_iam):
    item = InventoryItem.objects.create(name="Gauze", unit="roll",
                                        reorder_threshold=3)
    compounder = _client(stub_iam, 2001, "Compounder", [
        "phc.requisition.create", "phc.requisition.view",
    ])
    submitted = compounder.post("/api/v1/phc/requisitions", {
        "lines": [{"item_id": item.pk, "quantity": 8}],
    }, format="json")
    assert submitted.status_code == 201
    requisition_id = submitted.json()["id"]
    requisition = InventoryRequisition.objects.get(pk=requisition_id)
    assert requisition.state == InventoryRequisition.State.PENDING
    assert RequisitionLine.objects.filter(requisition=requisition).count() == 1

    registrar = _client(stub_iam, 4001, "Registrar", [
        "phc.requisition.view", "phc.requisition.approve",
    ])
    approved = registrar.post(f"/api/v1/phc/requisitions/{requisition_id}/decision",
                              {"decision": "approve"}, format="json")
    assert approved.status_code == 200
    assert approved.json()["state"] == "approved"
    assert NotificationOutbox.objects.filter(
        event_key=f"requisition:{requisition_id}:approved").exists()

    compounder = _client(stub_iam, 2001, "Compounder", [
        "phc.requisition.view", "phc.requisition.update",
    ])
    fulfilled = compounder.post(f"/api/v1/phc/requisitions/{requisition_id}/fulfill",
                                {}, format="json")
    assert fulfilled.status_code == 200
    assert fulfilled.json()["state"] == "fulfilled"
    assert PHCAuditEvent.objects.filter(
        object_type="inventory_requisition", object_id=requisition_id).count() == 3


def test_phc_br_10_registrar_cannot_decide_own_requisition(stub_iam):
    from modules.phc.models import InventoryRequisition

    req = InventoryRequisition.objects.create(originator_user_id=4001,
        state=InventoryRequisition.State.PENDING,
        submitted_at="2026-11-23T00:00:00Z")
    registrar = _client(stub_iam, 4001, "Registrar", [
        "phc.requisition.view", "phc.requisition.approve",
    ])

    response = registrar.post(f"/api/v1/phc/requisitions/{req.pk}/decision",
                              {"decision": "approve"}, format="json")

    assert response.status_code == 404
    req.refresh_from_db()
    assert req.state == InventoryRequisition.State.PENDING


# PHC-BR-10; PHC-BR-11; PHC-UC-16; BW-PHC-04; CFR-PHC-007; AFR-PHC-029; AFR-PHC-030.
def test_phc_br_10_br_11_uc_16_bw_phc_04_rejected_requisition_is_terminal(stub_iam):
    item = InventoryItem.objects.create(name="Surgical gauze", reorder_threshold=2)
    compounder = _client(stub_iam, 2001, "Compounder", [
        "phc.requisition.create", "phc.requisition.view",
    ])
    submitted = compounder.post("/api/v1/phc/requisitions", {
        "lines": [{"item_id": item.pk, "quantity": 3}],
    }, format="json")
    requisition_id = submitted.json()["id"]
    registrar = _client(stub_iam, 4001, "Registrar", [
        "phc.requisition.view", "phc.requisition.approve",
    ])
    rejected = registrar.post(f"/api/v1/phc/requisitions/{requisition_id}/decision",
                              {"decision": "reject"}, format="json")
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"
    assert NotificationOutbox.objects.filter(
        event_key=f"requisition:{requisition_id}:rejected").exists()
    retry = registrar.post(f"/api/v1/phc/requisitions/{requisition_id}/decision",
                           {"decision": "approve"}, format="json")
    assert retry.status_code == 404
