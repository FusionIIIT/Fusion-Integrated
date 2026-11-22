"""Public contract plural getter tests."""

from decimal import Decimal

import pytest

from modules.iaa.contracts import (
    RequestStatusDTO,
    TAClaimStatusDTO,
    get_request_statuses,
    get_travel_statuses,
)
from modules.iaa.models import ExpenseVoucherRequest, RequestStatus, TAClaim, TAClaimStatus

pytestmark = pytest.mark.django_db


def test_get_request_statuses_plural():
    r1 = ExpenseVoucherRequest.objects.create(
        user_id=101,
        department="CSE",
        request_type="expense",
        title="R1",
        total_amount=Decimal("150.00"),
        status=RequestStatus.APPROVED,
    )
    r2 = ExpenseVoucherRequest.objects.create(
        user_id=102,
        department="ECE",
        request_type="voucher",
        title="R2",
        total_amount=Decimal("250.00"),
        status=RequestStatus.RECORDED,
    )

    statuses = get_request_statuses([r1.id, r2.id, 9999])
    assert set(statuses.keys()) == {r1.id, r2.id}
    assert statuses[r1.id] == RequestStatusDTO(
        request_id=r1.id,
        user_id=101,
        department="CSE",
        request_type="expense",
        total_amount=Decimal("150.00"),
        status=RequestStatus.APPROVED,
    )
    assert statuses[r2.id] == RequestStatusDTO(
        request_id=r2.id,
        user_id=102,
        department="ECE",
        request_type="voucher",
        total_amount=Decimal("250.00"),
        status=RequestStatus.RECORDED,
    )


def test_get_request_statuses_empty():
    assert get_request_statuses([]) == {}
    assert get_request_statuses([None]) == {}


def test_get_travel_statuses_plural():
    t1 = TAClaim.objects.create(
        user_id=201,
        department="ME",
        purpose="Trip",
        departure_date="2026-04-01",
        arrival_date="2026-04-05",
        source_location="DEL",
        destination_location="BOM",
        claimed_amount=Decimal("5000.00"),
        status=TAClaimStatus.VERIFIED,
    )

    statuses = get_travel_statuses([t1.id, 8888])
    assert set(statuses.keys()) == {t1.id}
    assert statuses[t1.id] == TAClaimStatusDTO(
        claim_id=t1.id,
        user_id=201,
        department="ME",
        claimed_amount=Decimal("5000.00"),
        status=TAClaimStatus.VERIFIED,
    )


def test_get_travel_statuses_empty():
    assert get_travel_statuses([]) == {}
