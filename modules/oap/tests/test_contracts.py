"""Unit tests for OAP ADR-0013 public API contracts."""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from modules.oap.contracts import (
    get_active_bonafide_numbers,
    get_active_leaves,
    get_no_dues_clearances,
)
from modules.oap.models.bonafide import BonafideRequest
from modules.oap.models.leave import LeaveType, StudentLeaveRequest
from modules.oap.models.nodues import DepartmentType, NoDuesDepartmentalSignoff, NoDuesRequest

pytestmark = pytest.mark.django_db


def test_contracts_empty_inputs():
    assert get_no_dues_clearances([]) == {}
    assert get_active_leaves([]) == {}
    assert get_active_bonafide_numbers([]) == {}


def test_contracts_queries():
    # 1. No dues contract
    nd = NoDuesRequest.objects.create(student_id="24BCS205")
    for dept in DepartmentType.values:
        NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=nd,
            department=dept,
            status="CLEARED",
            dues_amount=Decimal("0.00"),
        )
    nd.check_and_finalize("ACAD_ADMIN")

    res_nd = get_no_dues_clearances(["24BCS205", "UNKNOWN_STUDENT"])
    assert res_nd["24BCS205"].is_cleared is True
    assert res_nd["UNKNOWN_STUDENT"].is_cleared is False

    # 2. Leave contract
    StudentLeaveRequest.objects.create(
        student_id="24BCS205",
        student_name="Rahul",
        leave_type=LeaveType.CASUAL,
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 3),
        reason="Personal",
        status="APPROVED",
    )
    res_leave = get_active_leaves(["24BCS205", "OTHER_STUDENT"])
    assert res_leave["24BCS205"] is True
    assert res_leave["OTHER_STUDENT"] is False

    # 3. Bonafide contract
    bona = BonafideRequest.objects.create(
        student_id="24BCS205",
        purpose="PASSPORT",
        details="Passport verification",
    )
    bona.approve_and_issue(issued_by="ADMIN")

    res_bona = get_active_bonafide_numbers(["24BCS205", "NO_BONA_STUDENT"])
    assert res_bona["24BCS205"] == bona.certificate_number
    assert res_bona["NO_BONA_STUDENT"] is None
