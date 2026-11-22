"""Unit tests for OAP database selectors."""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from modules.oap.models.bonafide import BonafideRequest
from modules.oap.models.branch_change import BranchChangeRequest
from modules.oap.models.leave import LeaveType, RequestStatus, StudentLeaveRequest
from modules.oap.models.nodues import NoDuesRequest
from modules.oap.selectors.selectors import (
    get_all_branch_change_applications,
    get_pending_bonafides,
    get_pending_leaves_for_approver,
    get_student_bonafides,
    get_student_leaves,
    get_student_no_dues,
)

pytestmark = pytest.mark.django_db


def test_selectors():
    # Leave selectors
    l1 = StudentLeaveRequest.objects.create(
        student_id="24BCS205",
        student_name="Rahul",
        leave_type=LeaveType.CASUAL,
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 2),
        reason="Work",
        status=RequestStatus.PENDING,
    )
    assert list(get_student_leaves("24BCS205")) == [l1]
    assert list(get_pending_leaves_for_approver()) == [l1]

    # Bonafide selectors
    b1 = BonafideRequest.objects.create(
        student_id="24BCS205", purpose="GENERAL", details="General"
    )
    assert list(get_student_bonafides("24BCS205")) == [b1]
    assert list(get_pending_bonafides()) == [b1]

    # No dues selector
    nd1 = NoDuesRequest.objects.create(student_id="24BCS205")
    assert list(get_student_no_dues("24BCS205")) == [nd1]

    # Branch change selector
    bc1 = BranchChangeRequest.objects.create(
        student_id="24BCS205",
        current_branch="ECE",
        preferred_branch_1="CSE",
        current_cpi=Decimal("9.10"),
    )
    assert list(get_all_branch_change_applications()) == [bc1]
