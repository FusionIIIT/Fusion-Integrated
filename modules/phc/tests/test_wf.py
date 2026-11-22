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


@pytest.mark.parametrize(
    "status,action,permission,payload",
    [
        ("pending_phc_review", "verify", "phc.claim.verify", None),
        ("pending_phc_review", "decide", "phc.claim.decide", {"approve": True}),
        ("pending_phc_review", "payment", "phc.claim.payment", None),
        ("pending_accounts_verification", "review", "phc.claim.review_phc", None),
        ("pending_accounts_verification", "decide", "phc.claim.decide", {"approve": True}),
        ("pending_accounts_verification", "payment", "phc.claim.payment", None),
        ("pending_sanction", "review", "phc.claim.review_phc", None),
        ("pending_sanction", "verify", "phc.claim.verify", None),
        ("pending_sanction", "payment", "phc.claim.payment", None),
        ("approved_for_payment", "review", "phc.claim.review_phc", None),
        ("approved_for_payment", "verify", "phc.claim.verify", None),
        ("approved_for_payment", "decide", "phc.claim.decide", {"approve": False}),
        ("rejected", "review", "phc.claim.review_phc", None),
        ("rejected", "verify", "phc.claim.verify", None),
        ("rejected", "decide", "phc.claim.decide", {"approve": True}),
        ("rejected", "payment", "phc.claim.payment", None),
    ],
    ids=[
        "skip-phc-review-to-verify", "skip-phc-review-to-decide", "skip-phc-review-to-payment",
        "accounts-cannot-reopen-review", "skip-accounts-to-decide", "skip-accounts-to-payment",
        "authority-stage-cannot-return-to-phc", "authority-stage-cannot-reverify", "skip-authority-to-payment",
        "paid-claim-cannot-return-to-phc", "paid-claim-cannot-return-to-accounts", "paid-claim-cannot-be-decided-again",
        "rejected-claim-cannot-return-to-phc", "rejected-claim-cannot-return-to-accounts", "rejected-claim-cannot-be-decided-again", "rejected-claim-cannot-be-paid",
    ],
)
def test_wf_claim_rejects_out_of_order_or_terminal_state_actions(
    phc_client, prescription, status, action, permission, payload
):
    from modules.phc.models import ReimbursementClaim

    claim = ReimbursementClaim.objects.create(
        user_id=1001, prescription=prescription, amount_claimed=Decimal("10.00"), status=status
    )
    client = phc_client(uid=901, kind="staff", permissions=(permission,))
    path = f"/api/v1/phc/claims/{claim.pk}/{action}/"
    response = client.post(path, payload or {}, format="json")
    assert response.status_code == 409
    claim.refresh_from_db()
    assert claim.status == status


@pytest.mark.parametrize(
    "start_status,action,payload",
    [
        ("pending_approval", "fulfill", None),
        ("rejected", "decide", {"approve": True}),
        ("rejected", "fulfill", None),
        ("fulfilled", "decide", {"approve": False}),
    ],
    ids=["cannot-fulfill-before-approval", "rejection-cannot-be-reversed", "rejection-cannot-be-fulfilled", "fulfilled-is-terminal"],
)
def test_wf_requisition_rejects_invalid_transition_and_preserves_status(
    phc_client, start_status, action, payload
):
    from modules.phc.models import ProcurementRequisition

    req = ProcurementRequisition.objects.create(
        title="Workflow boundary", submitted_by_user_id=900, status=start_status
    )
    if action == "decide":
        client = phc_client(uid=902, kind="staff", permissions=("phc.requisition.decide",))
        response = client.post(
            f"/api/v1/phc/requisitions/{req.pk}/decide/", payload, format="json"
        )
    else:
        client = phc_client(uid=900, kind="staff", permissions=("phc.requisition.fulfill",))
        response = client.post(f"/api/v1/phc/requisitions/{req.pk}/fulfill/")
    assert response.status_code == 409
    req.refresh_from_db()
    assert req.status == start_status


def test_wf_approved_requisition_records_decision_actor_notes_and_fulfillment_time(phc_client):
    from modules.phc.models import ProcurementRequisition

    req = ProcurementRequisition.objects.create(title="Delivery audit", submitted_by_user_id=900)
    authority = phc_client(uid=902, kind="staff", permissions=("phc.requisition.decide",))
    decision = authority.post(
        f"/api/v1/phc/requisitions/{req.pk}/decide/",
        {"approve": True, "notes": "Supplier confirmed stock"},
        format="json",
    )
    assert decision.status_code == 200
    assert decision.json()["decided_by_user_id"] == 902
    assert decision.json()["decision_notes"] == "Supplier confirmed stock"
    staff = phc_client(uid=900, kind="staff", permissions=("phc.requisition.fulfill",))
    fulfilled = staff.post(f"/api/v1/phc/requisitions/{req.pk}/fulfill/")
    assert fulfilled.status_code == 200
    assert fulfilled.json()["fulfilled_at"] is not None
