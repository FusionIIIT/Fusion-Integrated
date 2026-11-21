"""Accountant-only financial-status recording without executing external payments."""

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import (
    AuditEvent,
    ClaimDetail,
    FinancialStatusProjection,
    HRPolicyVersion,
    HRRequest,
    HRRequestTransition,
    Notification,
    OutboxEvent,
)
from modules.hreis.services import finance

pytestmark = pytest.mark.django_db
BASE = "/api/v1/hreis"


def _claim(owner=10, family="ltc", *, subtype="advance", state="approved", verified=True):
    now = timezone.now()
    policy = HRPolicyVersion.objects.create(
        family=family,
        version=1,
        effective_from=now - timedelta(hours=1),
        parameters={"conditions": {"requires_hr_verification": True}},
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    row = HRRequest.objects.create(
        user_id=owner, family=family, subtype=subtype, state=state,
        policy_version=policy,
    )
    ClaimDetail.objects.create(
        request=row, claim_type=family, subtype=subtype,
        prescribed_form_reference="official-form",
        hr_verified_by_user_id=98 if verified else None,
    )
    return row


def _api(stub_iam, user_id, role, permissions=(), kind="staff"):
    stub_iam(
        make_session(
            user_id=user_id,
            roles=(role,),
            active_role=role,
            kind=kind,
            permissions=permissions,
            modules=("hreis",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return c


def _payload():
    return {
        "financial_review_reference": "signed-accountant-check",
        "source_system": "finance",
        "external_status_reference": "finance-record-123",
        "payment_status": "payment_pending",
    }


@pytest.mark.parametrize("family,subtype", [
    ("ltc", "advance"),
    ("ltc", "reimbursement"),
    ("cpda", "advance"),
    ("cpda", "reimbursement"),
])
def test_accountant_records_approved_claim_status_without_payroll_execution(
    stub_iam, family, subtype,
):
    # HR-CFR-005, HR-UC-012, HR-UC-016, HR-AFR-015, HR-AFR-016,
    # HR-AFR-017, HR-AFR-018, HR-AFR-055, HR-AFR-056, HR-AFR-067,
    # HR-AFR-068, HR-AFR-069, BR-HR-022, BR-HR-027, BR-HR-035,
    # BW-HR-06, BW-HR-07, BW-HR-10, BW-HR-11, CW-HR-03, CW-HR-04:
    # externally referenced status is recorded, audited and immutable.
    row = _claim(family=family, subtype=subtype)
    c = _api(
        stub_iam, 200, "Accounts Admin",
        permissions=("hreis.finance.review", "hreis.finance.update", "hreis.request.view"),
    )
    queue = c.get(BASE + "/requests/")
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()["results"]] == [row.id]

    processed = c.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(),
        format="json",
        HTTP_IDEMPOTENCY_KEY=f"fin-{family}-123",
    )
    assert processed.status_code == 200, processed.content
    assert processed.json()["state"] == "financial_processing_recorded"
    claim_summary = processed.json()["claim_summary"]
    assert claim_summary["hr_verified"] is True
    assert claim_summary["financial_verified"] is True
    assert claim_summary["payment_status"] == "payment_pending"

    detail = ClaimDetail.objects.get(request=row)
    assert detail.financial_verified_by_user_id == 200
    assert detail.financial_processing_details == _payload() | {
        "financial_review_reference": "signed-accountant-check"
    }
    assert HRRequestTransition.objects.get(request=row).specification == (
        "CW-HR-03" if family == "ltc" else "CW-HR-04"
    )
    assert AuditEvent.objects.filter(
        resource_kind="hr_request", resource_id=row.id,
        action=f"{family}_record_financial_processing",
    ).exists()
    assert Notification.objects.filter(request=row, recipient_user_id=10).count() == 1
    assert OutboxEvent.objects.filter(
        event_type="hreis.notification",
        payload__request_id=row.pk,
    ).exists()
    again = c.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(),
        format="json",
        HTTP_IDEMPOTENCY_KEY=f"fin-{family}-123",
    )
    assert again.status_code == 409
    updated = c.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        {**_payload(), "payment_status": "paid",
         "external_status_reference": "finance-settled-124"},
        format="json", HTTP_IDEMPOTENCY_KEY=f"fin-{family}-settled",
    )
    assert updated.status_code == 200, updated.content
    assert updated.json()["state"] == "financial_processing_recorded"
    assert updated.json()["claim_summary"]["payment_status"] == "paid"
    assert HRRequestTransition.objects.filter(request=row).count() == 1
    history = list(
        FinancialStatusProjection.objects.filter(claim=detail)
        .order_by("recorded_at", "pk")
    )
    assert [event.payment_status for event in history] == ["payment_pending", "paid"]
    assert [event.external_status_reference for event in history] == [
        "finance-record-123", "finance-settled-124"
    ]
    assert {event.attested_by_user_id for event in history} == {200}
    assert AuditEvent.objects.filter(
        action="financial_status_attested", resource_id=row.pk,
    ).count() == 2
    assert Notification.objects.filter(request=row).count() == 2
    assert OutboxEvent.objects.filter(
        event_type="hreis.notification", payload__request_id=row.pk,
    ).count() == 2
    final_replay = c.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        {**_payload(), "payment_status": "failed"},
        format="json", HTTP_IDEMPOTENCY_KEY=f"fin-{family}-try-regress",
    )
    assert final_replay.status_code == 409
    history_count = FinancialStatusProjection.objects.filter(claim=detail).count()
    assert history_count == 2
    first_event = history[0]
    # BR-HR-026: historical financial attestations cannot be rewritten or deleted.
    with pytest.raises(IntegrityError), transaction.atomic():
        FinancialStatusProjection.objects.filter(pk=first_event.pk).update(
            payment_status="failed"
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        FinancialStatusProjection.objects.filter(pk=first_event.pk).delete()
    assert FinancialStatusProjection.objects.filter(claim=detail).count() == 2


def test_no_recording_for_unapproved_or_unverified_claim(stub_iam):
    # BR-HR-035: verified HR and final approval are mandatory preconditions.
    unapproved = _claim(state="pending_authority")
    accountant = _api(stub_iam, 200, "Accounts Admin", ("hreis.finance.review", "hreis.finance.update"))
    assert accountant.post(
        f"{BASE}/requests/{unapproved.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="bad-state",
    ).status_code == 404

    unverified = _claim(owner=11, family="cpda", verified=False)
    response = accountant.post(
        f"{BASE}/requests/{unverified.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="unverified-claim",
    )
    assert response.status_code == 409
    assert not HRRequestTransition.objects.exists()


def test_recording_requires_external_reference_and_active_accountant_permission(stub_iam):
    # BR-HR-002/030/035: ordinary employees and self-review are forbidden.
    row = _claim()
    staff = _api(stub_iam, 200, "staff", ("hreis.finance.review", "hreis.finance.update"))
    assert staff.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="not-accountant",
    ).status_code == 403
    accountant = _api(stub_iam, 10, "Accounts Admin", ("hreis.finance.review", "hreis.finance.update"))
    assert accountant.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="own-finance",
    ).status_code == 404
    accountant = _api(stub_iam, 200, "Accounts Admin", ("hreis.finance.review", "hreis.finance.update"))
    incomplete = {**_payload(), "external_status_reference": ""}
    assert accountant.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        incomplete, format="json", HTTP_IDEMPOTENCY_KEY="missing-reference",
    ).status_code == 400
    assert row.state == "approved"
    assert not HRRequestTransition.objects.exists()


def test_invalid_financial_service_input_does_not_modify_claim():
    # HR-AFR-017/018: only validated, evidenced status can be recorded.
    from conftest import make_principal
    from core.api.exceptions import BadRequestError

    row = _claim()
    actor = make_principal(
        user_id=200, kind="staff", roles=("Accounts Admin",), active_role="Accounts Admin",
        permissions=("hreis.finance.review", "hreis.finance.update"), modules=("hreis",),
    )
    with pytest.raises(BadRequestError):
        finance.record_financial_processing(
            actor,
            request_id=row.pk,
            financial_review_reference="",
            source_system="finance",
            external_status_reference="other-ref",
            payment_status="paid",
            idempotency_key="no-proof",
        )
    assert ClaimDetail.objects.get(request=row).financial_verified_by_user_id is None


def test_financial_status_requires_verified_review_or_combined_permissions(stub_iam):
    # HR-AFR-017/018 and BR-HR-035: verification and update grants are distinct.
    row = _claim()
    update_only = _api(
        stub_iam, 200, "Accounts Admin", ("hreis.finance.update",)
    )
    denied_review = update_only.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="update-without-review",
    )
    assert denied_review.status_code == 409
    assert not FinancialStatusProjection.objects.exists()

    review_only = _api(
        stub_iam, 200, "Accounts Admin", ("hreis.finance.review",)
    )
    denied_write = review_only.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="review-without-write",
    )
    assert denied_write.status_code == 403
    assert not FinancialStatusProjection.objects.exists()


def test_ltc_external_payroll_reference_is_traceable_without_payment_execution(stub_iam):
    # HR-AFR-057, BR-HR-019: payroll-origin status is linked to a local
    # immutable attestation, not claimed as a real payroll network exchange.
    row = _claim(family="ltc")
    accountant = _api(
        stub_iam, 200, "Accounts Admin",
        ("hreis.finance.review", "hreis.finance.update"),
    )
    response = accountant.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        {
            **_payload(),
            "source_system": "payroll",
            "external_status_reference": "payroll-origin-123",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="ltc-payroll-origin-status",
    )
    assert response.status_code == 200, response.content
    history = FinancialStatusProjection.objects.get(claim__request=row)
    assert history.source_system == "payroll"
    assert history.external_status_reference == "payroll-origin-123"
    assert history.payment_status == "payment_pending"
    assert AuditEvent.objects.get(
        event_key="financial-status:ltc-payroll-origin-status"
    ).data["source_system"] == "payroll"
    # This evidence asserts local status provenance only: no payroll API
    # connection, bank transfer or salary-structure update is simulated.


def test_financial_correctness_review_and_status_update_have_distinct_iam_grants(stub_iam):
    # HR-AFR-017 vs HR-AFR-018: a reviewer may attest the correctness of an
    # approved HR-verified claim without acquiring external status write rights.
    row = _claim()
    reviewer = _api(
        stub_iam, 200, "Accounts Admin",
        ("hreis.finance.review", "hreis.request.view"),
    )
    queue = reviewer.get(BASE + "/requests/")
    assert queue.status_code == 200, queue.content
    assert [item["id"] for item in queue.json()["results"]] == [row.pk]
    review = reviewer.post(
        f"{BASE}/requests/{row.pk}/financial-review/",
        {"financial_review_reference": "independent-finance-review-200"},
        format="json", HTTP_IDEMPOTENCY_KEY="review-only-200",
    )
    assert review.status_code == 200, review.content
    assert review.json()["reviewed_by_user_id"] == 200
    assert review.json()["financial_review_reference"] == "independent-finance-review-200"
    assert HRRequest.objects.get(pk=row.pk).state == "approved"
    assert not FinancialStatusProjection.objects.filter(claim__request=row).exists()
    assert AuditEvent.objects.filter(
        action="financial_correctness_verified",
        resource_kind="hr_request", resource_id=row.pk,
    ).count() == 1
    assert reviewer.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        _payload(), format="json", HTTP_IDEMPOTENCY_KEY="review-only-cannot-pay",
    ).status_code == 403
    assert reviewer.post(
        f"{BASE}/requests/{row.pk}/financial-review/",
        {"financial_review_reference": "independent-finance-review-200"},
        format="json", HTTP_IDEMPOTENCY_KEY="review-only-200",
    ).status_code == 409

    updater = _api(
        stub_iam, 202, "Accounts Admin",
        ("hreis.finance.update", "hreis.request.view"),
    )
    assert [item["id"] for item in updater.get(BASE + "/requests/").json()["results"]] == [
        row.pk
    ]
    blocked = updater.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        {**_payload(), "financial_review_reference": "different-unsigned-review"},
        format="json", HTTP_IDEMPOTENCY_KEY="unreviewed-finance-status",
    )
    assert blocked.status_code == 409
    assert not FinancialStatusProjection.objects.exists()

    processed = updater.post(
        f"{BASE}/requests/{row.pk}/financial-processing/",
        {**_payload(), "financial_review_reference": "independent-finance-review-200"},
        format="json", HTTP_IDEMPOTENCY_KEY="reviewed-finance-status",
    )
    assert processed.status_code == 200, processed.content
    assert processed.json()["state"] == "financial_processing_recorded"
    assert processed.json()["claim_summary"]["payment_status"] == "payment_pending"
    assert FinancialStatusProjection.objects.get(
        claim__request=row
    ).financial_review_reference == "independent-finance-review-200"
