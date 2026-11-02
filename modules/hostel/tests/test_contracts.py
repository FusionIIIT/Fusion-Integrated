"""Public cross-module contract tests (ADR-0013, contract testing)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.hostel.contracts import (
    get_hostel_no_dues_clearances,
    get_student_hostel_allocations,
    get_student_leave_summaries,
)
from modules.hostel.domain.constants import FineStatus, HostelGender, LeaveStatus, LeaveType
from modules.hostel.models import HostelFine, HostelLeave
from modules.hostel.services import allotment_service, hostel_service, room_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_data():
    hostel = hostel_service.create_hostel(
        name="Panini Hostel",
        code="BH-2",
        capacity=50,
        gender=HostelGender.BOYS,
        creator_user_id=1,
    )
    room = room_service.create_room(
        hostel_id=hostel.id,
        room_number="201",
        floor=2,
        capacity=2,
    )
    allotment = allotment_service.allot_room(
        student_user_id=5001,
        hostel_id=hostel.id,
        room_id=room.id,
        bed_number="A",
    )
    return hostel, room, allotment


def test_get_student_hostel_allocations(setup_data):
    """Test plural student hostel allocations contract."""
    res = get_student_hostel_allocations([5001, 9999])
    assert 5001 in res
    assert 9999 in res

    dto = res[5001]
    assert dto.user_id == 5001
    assert dto.has_active_hostel is True
    assert dto.hostel_code == "BH-2"
    assert dto.room_number == "201"
    assert dto.bed_number == "A"

    dto_none = res[9999]
    assert dto_none.has_active_hostel is False
    assert dto_none.hostel_code is None


def test_get_hostel_no_dues_clearances(setup_data):
    """Test plural hostel clearance for student graduation / semester registration."""
    hostel, _, _ = setup_data

    # Initially student 5001 has no fines -> cleared
    res = get_hostel_no_dues_clearances([5001])
    assert res[5001].cleared is True
    assert res[5001].total_fine_amount == 0.0

    # Impose fine on student 5001
    HostelFine.objects.create(
        student_user_id=5001,
        hostel=hostel,
        amount=Decimal("1500.00"),
        reason="Damage to table",
        issued_date=date.today(),
        status=FineStatus.PENDING.value,
    )

    # Now clearance must report false with pending amount
    res2 = get_hostel_no_dues_clearances([5001])
    assert res2[5001].cleared is False
    assert res2[5001].total_fine_amount == 1500.0
    assert res2[5001].pending_fines_count == 1


def test_get_student_leave_summaries(setup_data):
    """Test plural student leave summaries contract."""
    hostel, _, _ = setup_data

    # Create approved leave for 5001
    HostelLeave.objects.create(
        student_user_id=5001,
        hostel=hostel,
        from_date=date.today(),
        to_date=date.today() + timedelta(days=2),
        leave_type=LeaveType.HOME.value,
        reason="Home trip",
        status=LeaveStatus.APPROVED.value,
    )

    res = get_student_leave_summaries([5001, 7777])
    assert res[5001].active_leave is True
    assert res[5001].total_leaves_taken == 1

    assert res[7777].active_leave is False
    assert res[7777].total_leaves_taken == 0
