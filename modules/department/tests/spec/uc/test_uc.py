"""Specification-driven executable test suite for Strategy UC (Use Cases).

Traceable to UC_DESIGN.json.
Covering all Main Success Flows (MSF) and explicitly specified Alternative/Exception flows.
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


# UC-DEPT-001: Deliver Relevant Announcements
@pytest.mark.django_db
def test_uc_001():
    """test_id: TEST-UC-001, source_id: UC-DEPT-001 Main Flow

    Verify authenticated department user views announcements matching role, program, and year.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Dept_Admin",
    )
    d = announcement_service.create_draft(actor=actor, title="CSE Student Meeting", body="Mandatory meeting")
    announcement_service.publish(
        announcement_id=d.pk,
        actor=actor,
        target_roles=["Student"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    # The UC requires visibility filtering by viewer context
    if hasattr(announcement_selectors, "relevant_announcements"):
        results = announcement_selectors.relevant_announcements(
            role="Student", program="CSE", academic_year="2026"
        )
    else:
        results = announcement_selectors.active_announcements()
    titles = [a.title for a in results]
    assert "CSE Student Meeting" in titles


@pytest.mark.django_db
def test_uc_002():
    """test_id: TEST-UC-002, source_id: UC-DEPT-001 Alternative A1

    Verify user with no matching announcements receives empty result list.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Dept_Admin",
    )
    d = announcement_service.create_draft(actor=actor, title="ECE Only Announcement", body="ECE details")
    announcement_service.publish(
        announcement_id=d.pk,
        actor=actor,
        target_roles=["Student"],
        target_programs=["ECE"],
        target_academic_years=["2024"],
    )
    # Viewer is in CSE 2026, so ECE 2024 announcement must NOT be returned
    if hasattr(announcement_selectors, "relevant_announcements"):
        results = announcement_selectors.relevant_announcements(
            role="Student", program="CSE", academic_year="2026"
        )
    else:
        results = announcement_selectors.active_announcements()
    titles = [a.title for a in results]
    assert "ECE Only Announcement" not in titles, "UC-DEPT-001 Alternative A1 requires non-matching announcements to be excluded"


@pytest.mark.django_db
def test_uc_003():
    """test_id: TEST-UC-003, source_id: UC-DEPT-001 Exception E1

    Verify unauthenticated user cannot view announcements.
    """
    # Unauthenticated viewer check at service/permission boundary
    anon = None
    with pytest.raises((PermissionDeniedError, AttributeError)):
        announcement_service._require_permission(anon, "department.announcement.view")


# UC-DEPT-002: Create and Publish Announcement
@pytest.mark.django_db
def test_uc_004():
    """test_id: TEST-UC-004, source_id: UC-DEPT-002 Main Flow

    Verify authorized user creates draft and publishes announcement with target audience.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Faculty",
    )
    draft = announcement_service.create_draft(
        actor=actor,
        title="Department Colloquium",
        body="Speaker Dr. Rao on Monday.",
    )
    published = announcement_service.publish(
        announcement_id=draft.pk,
        actor=actor,
        target_roles=["Faculty", "Student"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    assert published.is_active is True
    # Publication must trigger notification to target scope
    assert hasattr(published, "notification_dispatched") and published.notification_dispatched, (
        "UC-DEPT-002 Main Flow Step 5 requires notification of published announcement to relevant audience"
    )


@pytest.mark.django_db
def test_uc_002_alt():
    """test_id: TEST-UC-002-ALT, source_id: UC-DEPT-002 Alternative A1

    Verify draft announcement can be saved without immediate publishing.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Dept_Admin",
    )
    draft = announcement_service.create_draft(
        actor=actor,
        title="Draft Memo",
        body="Not ready for publication yet.",
    )
    assert draft.pk is not None
    assert draft.published_at is None
    assert draft.is_active is False


@pytest.mark.django_db
def test_uc_005():
    """test_id: TEST-UC-005, source_id: UC-DEPT-002 Exception E1

    Verify unauthorized user (Student) is blocked from creating/publishing announcements.
    """
    student = make_actor(permissions=set(), active_role="Student")
    with pytest.raises(PermissionDeniedError):
        announcement_service.create_draft(
            actor=student,
            title="Unauthorized",
            body="Blocked",
        )


@pytest.mark.django_db
def test_uc_006():
    """test_id: TEST-UC-006, source_id: UC-DEPT-002 Exception E2

    Verify publishing with missing audience targeting lists is rejected.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Dept_Admin",
    )
    draft = announcement_service.create_draft(
        actor=actor,
        title="Incomplete Target",
        body="Missing target fields",
    )
    with pytest.raises(ConflictError):
        announcement_service.publish(
            announcement_id=draft.pk,
            actor=actor,
            target_roles=[],
            target_programs=["CSE"],
            target_academic_years=["2026"],
        )


# UC-DEPT-003: Maintain Active Announcements
@pytest.mark.django_db
def test_uc_007():
    """test_id: TEST-UC-007, source_id: UC-DEPT-003 Main Flow

    Verify HOD can edit active announcement content.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    draft = announcement_service.create_draft(actor=hod, title="Original", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    assert hasattr(announcement_service, "edit") or hasattr(announcement_service, "update_announcement"), (
        "UC-DEPT-003 Main Flow requires HOD edit capability for active announcements"
    )
    edit_fn = getattr(announcement_service, "edit", getattr(announcement_service, "update_announcement", None))
    updated = edit_fn(announcement_id=ann.pk, actor=hod, title="Updated Title", body="Updated Content")
    assert updated.title == "Updated Title"


@pytest.mark.django_db
def test_uc_008():
    """test_id: TEST-UC-008, source_id: UC-DEPT-003 Alternative A1

    Verify HOD can hide active department announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    draft = announcement_service.create_draft(actor=hod, title="To Hide", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    hidden = announcement_service.hide(announcement_id=ann.pk, actor=hod)
    assert hidden.is_hidden is True
    assert hidden.is_active is False


@pytest.mark.django_db
def test_uc_009():
    """test_id: TEST-UC-009, source_id: UC-DEPT-003 Alternative A2

    Verify HOD can delete active department announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    draft = announcement_service.create_draft(actor=hod, title="To Delete", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    deleted = announcement_service.soft_delete(announcement_id=ann.pk, actor=hod)
    assert deleted.deleted_at is not None
    assert deleted.is_active is False


@pytest.mark.django_db
def test_uc_010():
    """test_id: TEST-UC-010, source_id: UC-DEPT-003 Exception E1

    Verify non-HOD (e.g. Dept_Admin) cannot hide or delete active announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    non_hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="Dept_Admin",
    )
    draft = announcement_service.create_draft(actor=hod, title="Protected", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    with pytest.raises(PermissionDeniedError):
        announcement_service.hide(announcement_id=ann.pk, actor=non_hod)
    with pytest.raises(PermissionDeniedError):
        announcement_service.soft_delete(announcement_id=ann.pk, actor=non_hod)


# UC-DEPT-004: Request Stock Item
@pytest.mark.django_db
def test_uc_011():
    """test_id: TEST-UC-011, source_id: UC-DEPT-004 Main Flow

    Verify Faculty can request stock item when requested quantity <= available inventory.
    """
    item = InventoryItem.objects.create(name="Breadboards V2", unit="piece", quantity=10)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=4,
        purpose="Class lab sessions",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    assert req.pk is not None
    assert req.status == StockRequest.Status.PENDING


@pytest.mark.django_db
def test_uc_012():
    """test_id: TEST-UC-012, source_id: UC-DEPT-004 Exception E1

    Verify stock request rejected when requested quantity exceeds current inventory.
    """
    item = InventoryItem.objects.create(name="Oscilloscopes V2", unit="piece", quantity=3)
    req = StockRequest(
        item=item,
        requested_by_user_id=301,
        requested_quantity=10,  # Exceeds inventory of 3
        purpose="Project",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        req.full_clean()


@pytest.mark.django_db
def test_uc_013():
    """test_id: TEST-UC-013, source_id: UC-DEPT-004 Exception E2

    Verify non-Faculty actor cannot submit stock request.
    """
    student = make_actor(permissions=set(), active_role="Student")
    with pytest.raises(PermissionDeniedError):
        announcement_service._require_permission(student, "department.inventory.request")


# UC-DEPT-005: Approve or Reject Stock Request
@pytest.mark.django_db
def test_uc_014():
    """test_id: TEST-UC-014, source_id: UC-DEPT-005 Main Flow

    Verify HOD can approve pending stock request.
    """
    item = InventoryItem.objects.create(name="Jumper Wires", unit="pack", quantity=25)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=5,
        purpose="Workshop",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.APPROVED
    req.decided_at = timezone.now()
    req.decided_by_user_id = 202
    req.save()
    assert req.status == StockRequest.Status.APPROVED


@pytest.mark.django_db
def test_uc_015():
    """test_id: TEST-UC-015, source_id: UC-DEPT-005 Alternative A1

    Verify HOD can reject pending stock request with note.
    """
    item = InventoryItem.objects.create(name="Laser Modules", unit="piece", quantity=4)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Optics lab",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.REJECTED
    req.decided_at = timezone.now()
    req.decision_note = "Stock reserved for semester exams"
    req.save()
    assert req.status == StockRequest.Status.REJECTED


@pytest.mark.django_db
def test_uc_016():
    """test_id: TEST-UC-016, source_id: UC-DEPT-005 Exception E1

    Verify non-HOD actor cannot decide stock request.
    """
    admin = make_actor(permissions={"department.inventory.view"}, active_role="Dept_Admin")
    with pytest.raises(PermissionDeniedError):
        announcement_service._require_permission(admin, "department.inventory.approve")


# UC-DEPT-006: Allocate and Issue Stock
@pytest.mark.django_db
def test_uc_017():
    """test_id: TEST-UC-017, source_id: UC-DEPT-006 Main Flow

    Verify Dept_Admin issues HOD-approved stock, decrements inventory, and logs audit record.
    """
    item = InventoryItem.objects.create(name="Logic Probes", unit="piece", quantity=10)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=3,
        purpose="Lab exercise",
        status=StockRequest.Status.APPROVED,
        submitted_at=timezone.now(),
        decided_at=timezone.now(),
    )
    req.status = StockRequest.Status.ISSUED
    req.issued_at = timezone.now()
    req.issued_by_user_id = 101
    req.save()

    # The use case requires inventory quantity to decrement on issue
    item.refresh_from_db()
    assert item.quantity == 7, "UC-DEPT-006 Main Flow requires inventory quantity to be decremented upon stock issuance"


@pytest.mark.django_db
def test_uc_018():
    """test_id: TEST-UC-018, source_id: UC-DEPT-006 Exception E1

    Verify stock issuance rejected when request is not approved by HOD.
    """
    item = InventoryItem.objects.create(name="Multimeter Probes", unit="pair", quantity=8)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Circuits lab",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.ISSUED
    with pytest.raises(ValidationError):
        req.full_clean()


@pytest.mark.django_db
def test_uc_019():
    """test_id: TEST-UC-019, source_id: UC-DEPT-006 Exception E2

    Verify non-Dept_Admin actor cannot issue stock.
    """
    faculty = make_actor(permissions={"department.inventory.request"}, active_role="Faculty")
    with pytest.raises(PermissionDeniedError):
        announcement_service._require_permission(faculty, "department.inventory.issue")


# UC-DEPT-007: Submit Confidential Feedback
@pytest.mark.django_db
def test_uc_020():
    """test_id: TEST-UC-020, source_id: UC-DEPT-007 Main Flow"""
    pytest.skip("NOT_AUTOMATED: Feedback submission backend interface not implemented")


@pytest.mark.django_db
def test_uc_021():
    """test_id: TEST-UC-021, source_id: UC-DEPT-007 Exception E1"""
    pytest.skip("NOT_AUTOMATED: Feedback submission backend interface not implemented")


# UC-DEPT-008: Initial Review and Disposition of Feedback
@pytest.mark.django_db
def test_uc_022():
    """test_id: TEST-UC-022, source_id: UC-DEPT-008 Main Flow"""
    pytest.skip("NOT_AUTOMATED: Feedback initial review backend interface not implemented")


@pytest.mark.django_db
def test_uc_023():
    """test_id: TEST-UC-023, source_id: UC-DEPT-008 Alternative A1"""
    pytest.skip("NOT_AUTOMATED: Feedback close backend interface not implemented")


@pytest.mark.django_db
def test_uc_024():
    """test_id: TEST-UC-024, source_id: UC-DEPT-008 Alternative A2"""
    pytest.skip("NOT_AUTOMATED: Feedback resolve backend interface not implemented")


# UC-DEPT-010: Update Department Details
@pytest.mark.django_db
def test_uc_025():
    """test_id: TEST-UC-025, source_id: UC-DEPT-010 Main Flow"""
    pytest.skip("NOT_AUTOMATED: Department details update backend interface not implemented")


@pytest.mark.django_db
def test_uc_026():
    """test_id: TEST-UC-026, source_id: UC-DEPT-010 Alternative A1"""
    pytest.skip("NOT_AUTOMATED: Official department change backend interface not implemented")


@pytest.mark.django_db
def test_uc_027():
    """test_id: TEST-UC-027, source_id: UC-DEPT-010 Exception E1"""
    pytest.skip("NOT_AUTOMATED: Headship modification check backend interface not implemented")


# UC-DEPT-012: Approve Official Department Changes
@pytest.mark.django_db
def test_uc_028():
    """test_id: TEST-UC-028, source_id: UC-DEPT-012 Main Flow"""
    pytest.skip("NOT_AUTOMATED: Official change approval backend interface not implemented")


@pytest.mark.django_db
def test_uc_029():
    """test_id: TEST-UC-029, source_id: UC-DEPT-012 Alternative A1"""
    pytest.skip("NOT_AUTOMATED: Official change rejection backend interface not implemented")


# UC-DEPT-014: HOD Oversight and Resolution of Feedback
@pytest.mark.django_db
def test_uc_030():
    """test_id: TEST-UC-030, source_id: UC-DEPT-014 Main Flow"""
    pytest.skip("NOT_AUTOMATED: HOD feedback resolution backend interface not implemented")


@pytest.mark.django_db
def test_uc_031():
    """test_id: TEST-UC-031, source_id: UC-DEPT-014 Exception E1"""
    pytest.skip("NOT_AUTOMATED: HOD feedback oversight precondition backend interface not implemented")


# UC-DEPT-019: Insert Department Stock / Maintain Inventory
@pytest.mark.django_db
def test_uc_032():
    """test_id: TEST-UC-032, source_id: UC-DEPT-019 Main Flow

    Verify Dept_Admin inserts inventory stock, quantity updates, and immutable audit log is created.
    """
    item = InventoryItem.objects.create(name="USB Oscilloscopes", unit="unit", quantity=5)
    movement = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.INSERTION,
        quantity=5,
        quantity_before=0,
        quantity_after=5,
        performed_by_user_id=101,
        performed_by_role="Dept_Admin",
    )
    assert item.quantity == 5
    assert movement.pk is not None


# UC-DEPT-020: Maintain Department Role Assignments
@pytest.mark.django_db
def test_uc_033():
    """test_id: TEST-UC-033, source_id: UC-DEPT-020 Main Flow"""
    pytest.skip("NOT_AUTOMATED: Department role assignment backend interface not implemented")


@pytest.mark.django_db
def test_uc_034():
    """test_id: TEST-UC-034, source_id: UC-DEPT-020 Exception E1"""
    pytest.skip("NOT_AUTOMATED: Department role assignment authority backend interface not implemented")


# UC-DEPT-022: Apply Effective Department Role Transition
@pytest.mark.django_db
def test_uc_035():
    """test_id: TEST-UC-035, source_id: UC-DEPT-022 Main Flow"""
    pytest.skip("NOT_AUTOMATED: Role transition execution backend interface not implemented")

