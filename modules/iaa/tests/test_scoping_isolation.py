"""Scoping isolation tests enforcing IAA-BR-501 and IAA-BR-004."""

from decimal import Decimal

import pytest

from conftest import make_principal
from modules.iaa.models import (
    Anomaly,
    AnomalyStatus,
    AuditObservation,
    AuditObservationStatus,
    ExpenseVoucherRequest,
    RequestStatus,
    TAClaim,
    TAClaimStatus,
)
from modules.iaa.selectors.scoping import (
    scope_anomalies,
    scope_audit_observations,
    scope_requests,
    scope_travel_claims,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample_data():
    r1 = ExpenseVoucherRequest.objects.create(
        user_id=1001,
        department="CSE",
        request_type="expense",
        title="U1 Request",
        total_amount=Decimal("100.00"),
        status=RequestStatus.SUBMITTED,
    )
    r2 = ExpenseVoucherRequest.objects.create(
        user_id=2002,
        department="ECE",
        request_type="expense",
        title="U2 Request",
        total_amount=Decimal("200.00"),
        status=RequestStatus.SUBMITTED,
    )
    t1 = TAClaim.objects.create(
        user_id=1001,
        department="CSE",
        purpose="U1 TA",
        departure_date="2026-04-01",
        arrival_date="2026-04-03",
        source_location="Jabalpur",
        destination_location="Delhi",
        claimed_amount=Decimal("3000.00"),
        status=TAClaimStatus.SUBMITTED,
    )
    t2 = TAClaim.objects.create(
        user_id=2002,
        department="ECE",
        purpose="U2 TA",
        departure_date="2026-04-01",
        arrival_date="2026-04-03",
        source_location="Jabalpur",
        destination_location="Mumbai",
        claimed_amount=Decimal("4000.00"),
        status=TAClaimStatus.SUBMITTED,
    )
    a1 = Anomaly.objects.create(
        category="budget",
        description="Overdraft",
        reference_type="request",
        reference_id=r1.id,
        status=AnomalyStatus.OPEN,
        flagged_by_id=3001,
        flagged_by_role="finance_staff",
    )
    o1 = AuditObservation.objects.create(
        auditor_id=6001,
        department="CSE",
        title="Obs 1",
        description="Details",
        status=AuditObservationStatus.OPEN,
        responded_by_id=1001,
    )
    return {"r1": r1, "r2": r2, "t1": t1, "t2": t2, "a1": a1, "o1": o1}


def test_user_sees_only_own_records(sample_data):
    p_u1 = make_principal(user_id=1001, modules=("iaa",), permissions=("iaa.expense_request.view",))
    scoped_r = scope_requests(ExpenseVoucherRequest.objects.all(), p_u1)
    assert list(scoped_r.values_list("id", flat=True)) == [sample_data["r1"].id]

    scoped_t = scope_travel_claims(TAClaim.objects.all(), p_u1)
    assert list(scoped_t.values_list("id", flat=True)) == [sample_data["t1"].id]


def test_finance_staff_with_view_all_sees_everything(sample_data):
    p_fin = make_principal(
        user_id=3001,
        modules=("iaa",),
        permissions=("iaa.request.view_all", "iaa.travel.view_all", "iaa.anomaly.view"),
    )
    scoped_r = scope_requests(ExpenseVoucherRequest.objects.all(), p_fin)
    assert set(scoped_r.values_list("id", flat=True)) == {
        sample_data["r1"].id,
        sample_data["r2"].id,
    }

    scoped_t = scope_travel_claims(TAClaim.objects.all(), p_fin)
    assert set(scoped_t.values_list("id", flat=True)) == {
        sample_data["t1"].id,
        sample_data["t2"].id,
    }

    scoped_a = scope_anomalies(Anomaly.objects.all(), p_fin)
    assert list(scoped_a.values_list("id", flat=True)) == [sample_data["a1"].id]


def test_system_admin_operational_separation(sample_data):
    p_admin = make_principal(
        user_id=9999,
        modules=("iaa",),
        roles=("system_admin",),
        active_role="system_admin",
        permissions=("iaa.request.view_all", "iaa.travel.view_all"),
    )
    assert scope_requests(ExpenseVoucherRequest.objects.all(), p_admin).count() == 0
    assert scope_travel_claims(TAClaim.objects.all(), p_admin).count() == 0
    assert scope_anomalies(Anomaly.objects.all(), p_admin).count() == 0
    assert scope_audit_observations(AuditObservation.objects.all(), p_admin).count() == 0


def test_audit_observation_scoping(sample_data):
    p_u1 = make_principal(user_id=1001, modules=("iaa",), permissions=())
    scoped_o_u1 = scope_audit_observations(AuditObservation.objects.all(), p_u1)
    assert list(scoped_o_u1.values_list("id", flat=True)) == [sample_data["o1"].id]

    p_u2 = make_principal(user_id=2002, modules=("iaa",), permissions=())
    scoped_o_u2 = scope_audit_observations(AuditObservation.objects.all(), p_u2)
    assert scoped_o_u2.count() == 0

    p_auditor = make_principal(user_id=6001, modules=("iaa",), permissions=("iaa.audit.view",))
    scoped_o_aud = scope_audit_observations(AuditObservation.objects.all(), p_auditor)
    assert list(scoped_o_aud.values_list("id", flat=True)) == [sample_data["o1"].id]
