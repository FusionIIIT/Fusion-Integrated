"""WF strategy: complete and rejected reimbursement/procurement paths."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def test_reimbursement_approved_path_and_terminal_payment(phc_client, prescription):
    from modules.phc.models import PhcNotification, ReimbursementAudit

    employee = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.submit",))
    submit = employee.post(
        "/api/v1/phc/claims/submit/",
        {
            "prescription_id": prescription.pk,
            "amount_claimed": "45.00",
        },
        format="json",
    )
    assert submit.status_code == 201
    claim_id = submit.json()["id"]
    staff = phc_client(uid=900, kind="staff", permissions=("phc.claim.review_phc",))
    assert (
        staff.post(f"/api/v1/phc/claims/{claim_id}/review/").json()["status"]
        == "pending_accounts_verification"
    )
    accounts = phc_client(
        uid=901, kind="staff", permissions=("phc.claim.verify", "phc.claim.payment")
    )
    assert (
        accounts.post(f"/api/v1/phc/claims/{claim_id}/verify/").json()["status"]
        == "pending_sanction"
    )
    authority = phc_client(uid=902, kind="staff", permissions=("phc.claim.decide",))
    assert (
        authority.post(
            f"/api/v1/phc/claims/{claim_id}/decide/", {"approve": True}, format="json"
        ).json()["status"]
        == "approved_for_payment"
    )
    accounts = phc_client(uid=901, kind="staff", permissions=("phc.claim.payment",))
    assert accounts.post(f"/api/v1/phc/claims/{claim_id}/payment/").json()["status"] == "reimbursed"
    assert ReimbursementAudit.objects.filter(claim_id=claim_id).count() == 5
    assert (
        PhcNotification.objects.filter(
            recipient_user_id=1001, event_type="claim_status_changed"
        ).count()
        == 5
    )
    assert accounts.post(f"/api/v1/phc/claims/{claim_id}/payment/").status_code == 409


def test_rejected_claim_cannot_be_reopened_or_paid(phc_client, prescription):
    from modules.phc.models import ReimbursementClaim

    claim = ReimbursementClaim.objects.create(
        user_id=1001,
        prescription=prescription,
        amount_claimed=Decimal("10"),
        status="pending_sanction",
    )
    authority = phc_client(uid=902, kind="staff", permissions=("phc.claim.decide",))
    assert (
        authority.post(
            f"/api/v1/phc/claims/{claim.pk}/decide/", {"approve": False}, format="json"
        ).json()["status"]
        == "rejected"
    )
    accounts = phc_client(uid=901, kind="staff", permissions=("phc.claim.payment",))
    assert accounts.post(f"/api/v1/phc/claims/{claim.pk}/payment/").status_code == 409


def test_requisition_approval_fulfillment_does_not_change_inventory(phc_client):
    from modules.phc.models import InventoryItem, PhcNotification

    item = InventoryItem.objects.create(name="Gloves", stock_quantity=Decimal("8"))
    staff = phc_client(
        uid=900, kind="staff", permissions=("phc.requisition.submit", "phc.requisition.fulfill")
    )
    created = staff.post(
        "/api/v1/phc/requisitions/create/",
        {
            "title": "Gloves",
            "line_items": [{"item_name": "Gloves", "quantity": "10"}],
        },
        format="json",
    )
    assert created.status_code == 201
    req_id = created.json()["id"]
    authority = phc_client(uid=902, kind="staff", permissions=("phc.requisition.decide",))
    assert (
        authority.post(
            f"/api/v1/phc/requisitions/{req_id}/decide/", {"approve": True}, format="json"
        ).json()["status"]
        == "approved"
    )
    assert PhcNotification.objects.filter(
        recipient_user_id=900, event_type="requisition_decided"
    ).exists()
    staff = phc_client(uid=900, kind="staff", permissions=("phc.requisition.fulfill",))
    assert staff.post(f"/api/v1/phc/requisitions/{req_id}/fulfill/").json()["status"] == "fulfilled"
    item.refresh_from_db()
    assert item.stock_quantity == Decimal("8")
    assert staff.post(f"/api/v1/phc/requisitions/{req_id}/fulfill/").status_code == 409


def test_requisition_rejection_is_terminal(phc_client):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.requisition.submit",))
    req = staff.post(
        "/api/v1/phc/requisitions/create/",
        {
            "title": "Masks",
            "line_items": [{"item_name": "Mask", "quantity": "5"}],
        },
        format="json",
    )
    authority = phc_client(uid=902, kind="staff", permissions=("phc.requisition.decide",))
    req_id = req.json()["id"]
    assert (
        authority.post(
            f"/api/v1/phc/requisitions/{req_id}/decide/", {"approve": False}, format="json"
        ).json()["status"]
        == "rejected"
    )
    assert (
        authority.post(
            f"/api/v1/phc/requisitions/{req_id}/decide/", {"approve": True}, format="json"
        ).status_code
        == 409
    )
