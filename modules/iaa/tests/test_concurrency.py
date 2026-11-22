"""Concurrency and transactional boundary tests."""

from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.iaa.domain.state_machine import InvalidStateTransitionError
from modules.iaa.models import ExpenseVoucherRequest, RequestStatus
from modules.iaa.services.approvals import record_request_decision
from modules.iaa.services.requests import record_request_processing

pytestmark = pytest.mark.django_db


def test_double_recording_is_prevented():
    req = ExpenseVoucherRequest.objects.create(
        user_id=101,
        department="CSE",
        request_type="expense",
        title="Double Record Test",
        total_amount=Decimal("500.00"),
        status=RequestStatus.APPROVED,
    )
    rec1 = record_request_processing(req.id, finance_user_id=301, acting_role="finance_staff")
    assert rec1.status == RequestStatus.RECORDED

    with pytest.raises(InvalidStateTransitionError):
        record_request_processing(req.id, finance_user_id=301, acting_role="finance_staff")


def test_approval_decision_on_terminal_state_rejected():
    req = ExpenseVoucherRequest.objects.create(
        user_id=101,
        department="CSE",
        request_type="expense",
        title="Terminal Approval Test",
        total_amount=Decimal("500.00"),
        status=RequestStatus.RECORDED,
    )
    with pytest.raises(ConflictError, match="cannot receive an approval decision"):
        record_request_decision(
            request_id=req.id,
            approver_id=401,
            approver_role="HOD",
            decision="approve",
            remarks="Already recorded",
        )
