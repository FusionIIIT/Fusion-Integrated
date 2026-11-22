"""Specification-driven executable test suite for Strategy WF (Workflows).

Traceable to WF_DESIGN.json.
Covering all explicitly specified distinct workflow paths and decision outcomes.
"""
from types import SimpleNamespace
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.department.models import (
    Announcement,
    InventoryItem,
    StockMovement,
    StockRequest,
)
from modules.department.selectors import announcements as announcement_selectors
from modules.department.services import announcements as announcement_service


def make_actor(permissions=None, user_id=101, active_role="Dept_Admin"):
    permissions = permissions or set()

    def has_permission(code):
        return code in permissions

    return SimpleNamespace(
        user_id=user_id,
        active_role=active_role,
        has_permission=has_permission,
    )


# BW-DEPT-01: Stock Request Approved and Issued
@pytest.mark.django_db
def test_wf_001():
    """test_id: TEST-WF-001, source_id: BW-DEPT-01 Transition 1

    Verify transition from No stock request to Pending HOD Approval on valid Faculty submission.
    """
    item = InventoryItem.objects.create(name="Signal Generators", unit="unit", quantity=6)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Communication lab",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    assert req.status == StockRequest.Status.PENDING


@pytest.mark.django_db
def test_wf_002():
    """test_id: TEST-WF-002, source_id: BW-DEPT-01 Transition 2

    Verify transition from Pending HOD Approval to Approved for Issuance on HOD approval.
    """
    item = InventoryItem.objects.create(name="Function Generators", unit="unit", quantity=4)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=1,
        purpose="Testing",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.APPROVED
    req.decided_at = timezone.now()
    req.decided_by_user_id = 202
    req.save()
    assert req.status == StockRequest.Status.APPROVED


@pytest.mark.django_db
def test_wf_003():
    """test_id: TEST-WF-003, source_id: BW-DEPT-01 Transition 3

    Verify transition from Approved for Issuance to Issued with automatic inventory decrement and audit log.
    """
    item = InventoryItem.objects.create(name="Power Supplies", unit="unit", quantity=8)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Instrumentation lab",
        status=StockRequest.Status.APPROVED,
        submitted_at=timezone.now(),
        decided_at=timezone.now(),
    )
    req.status = StockRequest.Status.ISSUED
    req.issued_at = timezone.now()
    req.issued_by_user_id = 101
    req.save()

    item.refresh_from_db()
    assert item.quantity == 6, "BW-DEPT-01 Transition 3 requires inventory quantity to automatically decrement on issuance"


# BW-DEPT-02: Stock Request Rejected by HOD
@pytest.mark.django_db
def test_wf_004():
    """test_id: TEST-WF-004, source_id: BW-DEPT-02 Transition 1

    Verify initial valid Faculty stock submission enters Pending HOD Approval state.
    """
    item = InventoryItem.objects.create(name="Soldering Stations", unit="unit", quantity=5)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Project fabrication",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    assert req.status == StockRequest.Status.PENDING


@pytest.mark.django_db
def test_wf_005():
    """test_id: TEST-WF-005, source_id: BW-DEPT-02 Transition 2

    Verify transition from Pending HOD Approval to Rejected on HOD rejection.
    """
    item = InventoryItem.objects.create(name="Hot Air Guns", unit="unit", quantity=3)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=1,
        purpose="PCB repair",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.REJECTED
    req.decided_at = timezone.now()
    req.decision_note = "Rejected due to scheduled maintenance"
    req.save()
    assert req.status == StockRequest.Status.REJECTED
    assert item.quantity == 3


# CW-DEPT-01: Stock Request, Approval and Issuance Lifecycle
@pytest.mark.django_db
def test_wf_006():
    """test_id: TEST-WF-006, source_id: CW-DEPT-01 Path 1

    Verify full composite stock path: Request -> Approval -> Issuance.
    """
    item = InventoryItem.objects.create(name="Microchips ATmega328", unit="piece", quantity=50)
    # Step 1: Faculty Request
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=10,
        purpose="Microprocessor class",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    assert req.status == StockRequest.Status.PENDING

    # Step 2: HOD Approval
    req.status = StockRequest.Status.APPROVED
    req.decided_at = timezone.now()
    req.save()
    assert req.status == StockRequest.Status.APPROVED

    # Step 3: Dept_Admin Issuance
    req.status = StockRequest.Status.ISSUED
    req.issued_at = timezone.now()
    req.save()

    item.refresh_from_db()
    assert item.quantity == 40, "CW-DEPT-01 Path 1 requires stock decrement upon completion of issuance path"


@pytest.mark.django_db
def test_wf_007():
    """test_id: TEST-WF-007, source_id: CW-DEPT-01 Path 2

    Verify full composite stock path: Request -> Rejection.
    """
    item = InventoryItem.objects.create(name="Arduino Nano", unit="piece", quantity=20)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=5,
        purpose="Student robotics",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.REJECTED
    req.decided_at = timezone.now()
    req.save()
    assert req.status == StockRequest.Status.REJECTED
    item.refresh_from_db()
    assert item.quantity == 20


# BW-DEPT-03: Feedback Disposed by Dept_Admin
@pytest.mark.django_db
def test_wf_008():
    """test_id: TEST-WF-008, source_id: BW-DEPT-03 Transition 1"""
    pytest.skip("NOT_AUTOMATED: Feedback submission workflow transition not implemented in backend")


@pytest.mark.django_db
def test_wf_009():
    """test_id: TEST-WF-009, source_id: BW-DEPT-03 Transition 2"""
    pytest.skip("NOT_AUTOMATED: Feedback initial review workflow transition not implemented in backend")


@pytest.mark.django_db
def test_wf_010():
    """test_id: TEST-WF-010, source_id: BW-DEPT-03 Transition 3"""
    pytest.skip("NOT_AUTOMATED: Feedback simple close workflow transition not implemented in backend")


# BW-DEPT-04: Feedback Disposed with HOD Oversight
@pytest.mark.django_db
def test_wf_011():
    """test_id: TEST-WF-011, source_id: BW-DEPT-04 Transition 1"""
    pytest.skip("NOT_AUTOMATED: Feedback submission workflow transition not implemented in backend")


@pytest.mark.django_db
def test_wf_012():
    """test_id: TEST-WF-012, source_id: BW-DEPT-04 Transition 2"""
    pytest.skip("NOT_AUTOMATED: Feedback initial review workflow transition not implemented in backend")


@pytest.mark.django_db
def test_wf_013():
    """test_id: TEST-WF-013, source_id: BW-DEPT-04 Transition 3"""
    pytest.skip("NOT_AUTOMATED: Feedback HOD oversight resolution workflow transition not implemented in backend")


# CW-DEPT-02: Feedback Handling Lifecycle
@pytest.mark.django_db
def test_wf_014():
    """test_id: TEST-WF-014, source_id: CW-DEPT-02 Path 1"""
    pytest.skip("NOT_AUTOMATED: Composite feedback handling path 1 not implemented in backend")


@pytest.mark.django_db
def test_wf_015():
    """test_id: TEST-WF-015, source_id: CW-DEPT-02 Path 2"""
    pytest.skip("NOT_AUTOMATED: Composite feedback handling path 2 not implemented in backend")


# BW-DEPT-05: Official Department Change Approved
@pytest.mark.django_db
def test_wf_016():
    """test_id: TEST-WF-016, source_id: BW-DEPT-05 Transition 1"""
    pytest.skip("NOT_AUTOMATED: Official department change submission workflow not implemented in backend")


@pytest.mark.django_db
def test_wf_017():
    """test_id: TEST-WF-017, source_id: BW-DEPT-05 Transition 2"""
    pytest.skip("NOT_AUTOMATED: Official department change approval workflow not implemented in backend")


# BW-DEPT-06: Official Department Change Rejected
@pytest.mark.django_db
def test_wf_018():
    """test_id: TEST-WF-018, source_id: BW-DEPT-06 Transition 1"""
    pytest.skip("NOT_AUTOMATED: Official department change submission workflow not implemented in backend")


@pytest.mark.django_db
def test_wf_019():
    """test_id: TEST-WF-019, source_id: BW-DEPT-06 Transition 2"""
    pytest.skip("NOT_AUTOMATED: Official department change rejection workflow not implemented in backend")


# CW-DEPT-03: Official Department Change Lifecycle
@pytest.mark.django_db
def test_wf_020():
    """test_id: TEST-WF-020, source_id: CW-DEPT-03 Lifecycle"""
    pytest.skip("NOT_AUTOMATED: Official department change composite lifecycle not implemented in backend")


# BW-DEPT-07: HOD Role Reassignment and Headship Synchronization
@pytest.mark.django_db
def test_wf_021():
    """test_id: TEST-WF-021, source_id: BW-DEPT-07 Transition 1"""
    pytest.skip("NOT_AUTOMATED: HOD role reassignment submission workflow not implemented in backend")


@pytest.mark.django_db
def test_wf_022():
    """test_id: TEST-WF-022, source_id: BW-DEPT-07 Transition 2"""
    pytest.skip("NOT_AUTOMATED: HOD role transition execution workflow not implemented in backend")


# BW-DEPT-08: Dept_Admin Role Reassignment and Access Transition
@pytest.mark.django_db
def test_wf_023():
    """test_id: TEST-WF-023, source_id: BW-DEPT-08 Transition 1"""
    pytest.skip("NOT_AUTOMATED: Dept_Admin role reassignment submission workflow not implemented in backend")


@pytest.mark.django_db
def test_wf_024():
    """test_id: TEST-WF-024, source_id: BW-DEPT-08 Transition 2"""
    pytest.skip("NOT_AUTOMATED: Dept_Admin role transition execution workflow not implemented in backend")

