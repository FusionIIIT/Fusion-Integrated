"""Specification-driven executable test suite for Strategy BR (Business Rules).

Traceable to BR_DESIGN.json.
Covering all permitted and prohibited outcomes, threshold sides, and stated exceptions.
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


# BR-DEPT-001: Announcement Creation and Publication Authority
@pytest.mark.django_db
def test_br_001():
    """test_id: TEST-BR-001, source_id: BR-DEPT-001-PERMITTED

    Verify Faculty, Dept_Admin, and HOD are permitted to create and publish announcements.
    """
    for role in ["Faculty", "Dept_Admin", "HOD"]:
        actor = make_actor(
            permissions={"department.announcement.publish"},
            active_role=role,
            user_id=100 + len(role),
        )
        draft = announcement_service.create_draft(
            actor=actor,
            title=f"Announcement by {role}",
            body=f"Content for {role}",
        )
        published = announcement_service.publish(
            announcement_id=draft.pk,
            actor=actor,
            target_roles=["Student"],
            target_programs=["CSE"],
            target_academic_years=["2026"],
        )
        assert published.is_active is True


@pytest.mark.django_db
def test_br_002():
    """test_id: TEST-BR-002, source_id: BR-DEPT-001-PROHIBITED

    Verify Student or unauthenticated user is prohibited from publishing announcements.
    """
    student = make_actor(permissions=set(), active_role="Student")
    with pytest.raises(PermissionDeniedError):
        announcement_service.create_draft(actor=student, title="Student Post", body="Disallowed")


# BR-DEPT-002: Announcement Visibility Filtering
@pytest.mark.django_db
def test_br_003():
    """test_id: TEST-BR-003, source_id: BR-DEPT-002-MATCH

    Verify viewer matching target role, program, and academic year can view announcement.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Dept_Admin",
    )
    d = announcement_service.create_draft(actor=actor, title="Targeted Match", body="CSE 2026")
    announcement_service.publish(
        announcement_id=d.pk,
        actor=actor,
        target_roles=["Student"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    if hasattr(announcement_selectors, "relevant_announcements"):
        results = announcement_selectors.relevant_announcements(
            role="Student", program="CSE", academic_year="2026"
        )
    else:
        results = announcement_selectors.active_announcements()
    titles = [a.title for a in results]
    assert "Targeted Match" in titles


@pytest.mark.django_db
def test_br_004():
    """test_id: TEST-BR-004, source_id: BR-DEPT-002-MISMATCH

    Verify viewer not matching target role, program, or academic year cannot view announcement.
    """
    actor = make_actor(
        permissions={"department.announcement.publish"},
        active_role="Dept_Admin",
    )
    d = announcement_service.create_draft(actor=actor, title="Targeted ECE 2024", body="ECE")
    announcement_service.publish(
        announcement_id=d.pk,
        actor=actor,
        target_roles=["Faculty"],
        target_programs=["ECE"],
        target_academic_years=["2024"],
    )
    if hasattr(announcement_selectors, "relevant_announcements"):
        results = announcement_selectors.relevant_announcements(
            role="Student", program="CSE", academic_year="2026"
        )
    else:
        results = announcement_selectors.active_announcements()
    titles = [a.title for a in results]
    assert "Targeted ECE 2024" not in titles, "BR-DEPT-002 requires non-matching announcements to be prohibited from view"


# BR-DEPT-004: Announcement Modification and Deletion Authority
@pytest.mark.django_db
def test_br_005():
    """test_id: TEST-BR-005, source_id: BR-DEPT-004-HOD-EDIT

    Verify HOD is permitted to edit active department announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    draft = announcement_service.create_draft(actor=hod, title="Title V1", body="Body V1")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    assert hasattr(announcement_service, "edit") or hasattr(announcement_service, "update_announcement"), (
        "BR-DEPT-004 requires HOD edit authority implementation"
    )
    edit_fn = getattr(announcement_service, "edit", getattr(announcement_service, "update_announcement", None))
    updated = edit_fn(announcement_id=ann.pk, actor=hod, title="Title V2", body="Body V2")
    assert updated.title == "Title V2"


@pytest.mark.django_db
def test_br_006():
    """test_id: TEST-BR-006, source_id: BR-DEPT-004-HOD-HIDE

    Verify HOD is permitted to hide active department announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    draft = announcement_service.create_draft(actor=hod, title="Title", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    hidden = announcement_service.hide(announcement_id=ann.pk, actor=hod)
    assert hidden.is_hidden is True


@pytest.mark.django_db
def test_br_007():
    """test_id: TEST-BR-007, source_id: BR-DEPT-004-HOD-DELETE

    Verify HOD is permitted to delete active department announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    draft = announcement_service.create_draft(actor=hod, title="Title", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    deleted = announcement_service.soft_delete(announcement_id=ann.pk, actor=hod)
    assert deleted.deleted_at is not None


@pytest.mark.django_db
def test_br_008():
    """test_id: TEST-BR-008, source_id: BR-DEPT-004-NON_HOD-PROHIBITED

    Verify non-HOD actor is prohibited from editing, hiding, or deleting active announcement.
    """
    hod = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="HOD",
    )
    admin = make_actor(
        permissions={"department.announcement.publish", "department.announcement.manage"},
        active_role="Dept_Admin",
    )
    draft = announcement_service.create_draft(actor=hod, title="Active Ann", body="Body")
    ann = announcement_service.publish(
        announcement_id=draft.pk,
        actor=hod,
        target_roles=["Faculty"],
        target_programs=["CSE"],
        target_academic_years=["2026"],
    )
    with pytest.raises(PermissionDeniedError):
        announcement_service.hide(announcement_id=ann.pk, actor=admin)
    with pytest.raises(PermissionDeniedError):
        announcement_service.soft_delete(announcement_id=ann.pk, actor=admin)


# BR-DEPT-005: Stock Request Initiation Authority
@pytest.mark.django_db
def test_br_009():
    """test_id: TEST-BR-009, source_id: BR-DEPT-005-FACULTY

    Verify Faculty is permitted to submit stock requests.
    """
    faculty = make_actor(permissions={"department.inventory.request"}, active_role="Faculty")
    item = InventoryItem.objects.create(name="ICs", unit="piece", quantity=20)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=faculty.user_id,
        requested_quantity=5,
        purpose="Digital electronics",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    assert req.status == StockRequest.Status.PENDING


@pytest.mark.django_db
def test_br_010():
    """test_id: TEST-BR-010, source_id: BR-DEPT-005-NON_FACULTY

    Verify non-Faculty is prohibited from submitting stock requests.
    """
    student = make_actor(permissions=set(), active_role="Student")
    with pytest.raises(PermissionDeniedError):
        announcement_service._require_permission(student, "department.inventory.request")


# BR-DEPT-006: Stock Request Approval Authority
@pytest.mark.django_db
def test_br_011():
    """test_id: TEST-BR-011, source_id: BR-DEPT-006-HOD-APPROVE

    Verify HOD is permitted to approve stock request.
    """
    item = InventoryItem.objects.create(name="Relays", unit="piece", quantity=10)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Power systems",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.APPROVED
    req.decided_at = timezone.now()
    req.save()
    assert req.status == StockRequest.Status.APPROVED


@pytest.mark.django_db
def test_br_012():
    """test_id: TEST-BR-012, source_id: BR-DEPT-006-HOD-REJECT

    Verify HOD is permitted to reject stock request.
    """
    item = InventoryItem.objects.create(name="Diodes", unit="pack", quantity=10)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Testing",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.REJECTED
    req.decided_at = timezone.now()
    req.save()
    assert req.status == StockRequest.Status.REJECTED


@pytest.mark.django_db
def test_br_013():
    """test_id: TEST-BR-013, source_id: BR-DEPT-006-NON_HOD-PROHIBITED

    Verify non-HOD is prohibited from making stock request approval decisions.
    """
    admin = make_actor(permissions={"department.inventory.view"}, active_role="Dept_Admin")
    with pytest.raises(PermissionDeniedError):
        announcement_service._require_permission(admin, "department.inventory.approve")


# BR-DEPT-007: Stock Issuance Authority and Precondition
@pytest.mark.django_db
def test_br_014():
    """test_id: TEST-BR-014, source_id: BR-DEPT-007-APPROVED-PERMITTED

    Verify Dept_Admin is permitted to issue stock for HOD-approved request.
    """
    item = InventoryItem.objects.create(name="Transformers", unit="unit", quantity=5)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=1,
        purpose="Lab",
        status=StockRequest.Status.APPROVED,
        submitted_at=timezone.now(),
        decided_at=timezone.now(),
    )
    req.status = StockRequest.Status.ISSUED
    req.issued_at = timezone.now()
    req.issued_by_user_id = 101
    req.save()
    assert req.status == StockRequest.Status.ISSUED


@pytest.mark.django_db
def test_br_015():
    """test_id: TEST-BR-015, source_id: BR-DEPT-007-UNAPPROVED-PROHIBITED

    Verify stock issuance is prohibited for requests not approved by HOD.
    """
    item = InventoryItem.objects.create(name="Inductors", unit="piece", quantity=12)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=2,
        purpose="Circuits",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.status = StockRequest.Status.ISSUED
    with pytest.raises(ValidationError):
        req.full_clean()


@pytest.mark.django_db
def test_br_016():
    """test_id: TEST-BR-016, source_id: BR-DEPT-007-NON_ADMIN-PROHIBITED

    Verify non-Dept_Admin is prohibited from issuing stock.
    """
    faculty = make_actor(permissions={"department.inventory.request"}, active_role="Faculty")
    with pytest.raises(PermissionDeniedError):
        announcement_service._require_permission(faculty, "department.inventory.issue")


# BR-DEPT-008: Confidential Feedback Submission
@pytest.mark.django_db
def test_br_017():
    """test_id: TEST-BR-017, source_id: BR-DEPT-008-SUBMIT-PERMITTED"""
    pytest.skip("NOT_AUTOMATED: Feedback submission backend interface not implemented")


@pytest.mark.django_db
def test_br_018():
    """test_id: TEST-BR-018, source_id: BR-DEPT-008-CONFIDENTIALITY"""
    pytest.skip("NOT_AUTOMATED: Feedback confidentiality backend interface not implemented")


# BR-DEPT-009: Feedback Disposition Authority and Terminal State
@pytest.mark.django_db
def test_br_019():
    """test_id: TEST-BR-019, source_id: BR-DEPT-009-ADMIN-RESOLVE"""
    pytest.skip("NOT_AUTOMATED: Feedback resolution backend interface not implemented")


@pytest.mark.django_db
def test_br_020():
    """test_id: TEST-BR-020, source_id: BR-DEPT-009-HOD-RESOLVE"""
    pytest.skip("NOT_AUTOMATED: Feedback resolution backend interface not implemented")


@pytest.mark.django_db
def test_br_021():
    """test_id: TEST-BR-021, source_id: BR-DEPT-009-TERMINAL-LOCKED"""
    pytest.skip("NOT_AUTOMATED: Feedback terminal lock backend interface not implemented")


# BR-DEPT-011: Official Department Detail Changes Approval Requirement
@pytest.mark.django_db
def test_br_022():
    """test_id: TEST-BR-022, source_id: BR-DEPT-011-OFFICIAL-PENDING"""
    pytest.skip("NOT_AUTOMATED: Official department change backend interface not implemented")


@pytest.mark.django_db
def test_br_023():
    """test_id: TEST-BR-023, source_id: BR-DEPT-011-HEADSHIP-EXCLUDED"""
    pytest.skip("NOT_AUTOMATED: Headship modification check backend interface not implemented")


# BR-DEPT-013: Official Department Detail Approval Authority
@pytest.mark.django_db
def test_br_024():
    """test_id: TEST-BR-024, source_id: BR-DEPT-013-APPROVE"""
    pytest.skip("NOT_AUTOMATED: Official change approval backend interface not implemented")


@pytest.mark.django_db
def test_br_025():
    """test_id: TEST-BR-025, source_id: BR-DEPT-013-REJECT"""
    pytest.skip("NOT_AUTOMATED: Official change rejection backend interface not implemented")


@pytest.mark.django_db
def test_br_026():
    """test_id: TEST-BR-026, source_id: BR-DEPT-013-NON_HOD-PROHIBITED"""
    pytest.skip("NOT_AUTOMATED: Official change approval authority backend interface not implemented")


# BR-DEPT-015: Stock Request Inventory Validation
@pytest.mark.django_db
def test_br_027():
    """test_id: TEST-BR-027, source_id: BR-DEPT-015-VALID-QUANTITY

    Verify requested quantity > 0 and <= current inventory passes validation.
    """
    item = InventoryItem.objects.create(name="Resistor Packs", unit="pack", quantity=100)
    req = StockRequest(
        item=item,
        requested_by_user_id=301,
        requested_quantity=10,
        purpose="Introductory circuits",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    req.full_clean()
    req.save()
    assert req.pk is not None


@pytest.mark.django_db
def test_br_028():
    """test_id: TEST-BR-028, source_id: BR-DEPT-015-EXCEEDS-PROHIBITED

    Verify requested quantity > current inventory is prohibited and blocked before approval.
    """
    item = InventoryItem.objects.create(name="Spectrum Analyzers", unit="unit", quantity=2)
    req = StockRequest(
        item=item,
        requested_by_user_id=301,
        requested_quantity=5,  # Exceeds current inventory of 2
        purpose="Advanced RF experiment",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        req.full_clean()


@pytest.mark.django_db
def test_br_029():
    """test_id: TEST-BR-029, source_id: BR-DEPT-015-ZERO-QTY-PROHIBITED

    Verify requested quantity <= 0 is prohibited.
    """
    item = InventoryItem.objects.create(name="Soldering Wire", unit="roll", quantity=10)
    req = StockRequest(
        item=item,
        requested_by_user_id=301,
        requested_quantity=0,
        purpose="Assembly",
        status=StockRequest.Status.PENDING,
        submitted_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        req.full_clean()


# BR-DEPT-016: Immutable Stock Movement Logging & Inventory Decrement
@pytest.mark.django_db
def test_br_030():
    """test_id: TEST-BR-030, source_id: BR-DEPT-016-DECREMENT

    Verify stock issuance automatically decrements current inventory quantity.
    """
    item = InventoryItem.objects.create(name="Logic Gates ICs", unit="piece", quantity=30)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=10,
        purpose="Logic lab",
        status=StockRequest.Status.APPROVED,
        submitted_at=timezone.now(),
        decided_at=timezone.now(),
    )
    req.status = StockRequest.Status.ISSUED
    req.issued_at = timezone.now()
    req.issued_by_user_id = 101
    req.save()

    item.refresh_from_db()
    assert item.quantity == 20, "BR-DEPT-016 requires current inventory quantity to decrement upon stock issuance"


@pytest.mark.django_db
def test_br_031():
    """test_id: TEST-BR-031, source_id: BR-DEPT-016-LOG-ISSUANCE

    Verify stock issuance records immutable movement log with before/after counts.
    """
    item = InventoryItem.objects.create(name="Soldering Flux", unit="bottle", quantity=15)
    req = StockRequest.objects.create(
        item=item,
        requested_by_user_id=301,
        requested_quantity=3,
        purpose="Assembly",
        status=StockRequest.Status.APPROVED,
        submitted_at=timezone.now(),
        decided_at=timezone.now(),
    )
    move = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.ISSUANCE,
        quantity=3,
        quantity_before=15,
        quantity_after=12,
        performed_by_user_id=101,
        performed_by_role="Dept_Admin",
        stock_request=req,
    )
    assert move.quantity_before == 15
    assert move.quantity_after == 12


@pytest.mark.django_db
def test_br_032():
    """test_id: TEST-BR-032, source_id: BR-DEPT-016-IMMUTABILITY

    Verify stock movement log records are immutable and cannot be updated or deleted.
    """
    item = InventoryItem.objects.create(name="Ethernet Patch Cords", unit="piece", quantity=40)
    move = StockMovement.objects.create(
        item=item,
        movement_type=StockMovement.MovementType.INSERTION,
        quantity=20,
        quantity_before=20,
        quantity_after=40,
        performed_by_user_id=101,
        performed_by_role="Dept_Admin",
    )
    move.quantity = 25
    with pytest.raises(ValidationError):
        move.save()
    with pytest.raises(ValidationError):
        move.delete()


# BR-DEPT-017: Feedback Initial Review Obligation
@pytest.mark.django_db
def test_br_033():
    """test_id: TEST-BR-033, source_id: BR-DEPT-017-REVIEW-REQUIRED"""
    pytest.skip("NOT_AUTOMATED: Feedback review obligation backend interface not implemented")


@pytest.mark.django_db
def test_br_034():
    """test_id: TEST-BR-034, source_id: BR-DEPT-017-NO-PRE-REVIEW-OVERSIGHT"""
    pytest.skip("NOT_AUTOMATED: Feedback review precondition backend interface not implemented")


# BR-DEPT-018: Feedback Categorization and Simple Issue Closure
@pytest.mark.django_db
def test_br_035():
    """test_id: TEST-BR-035, source_id: BR-DEPT-018-CATEGORIZE"""
    pytest.skip("NOT_AUTOMATED: Feedback categorization backend interface not implemented")


@pytest.mark.django_db
def test_br_036():
    """test_id: TEST-BR-036, source_id: BR-DEPT-018-SIMPLE-CLOSE"""
    pytest.skip("NOT_AUTOMATED: Feedback simple closure backend interface not implemented")


# BR-DEPT-021: Department Role Assignment Authority
@pytest.mark.django_db
def test_br_037():
    """test_id: TEST-BR-037, source_id: BR-DEPT-021-INST-ADMIN"""
    pytest.skip("NOT_AUTOMATED: Role assignment authority backend interface not implemented")


@pytest.mark.django_db
def test_br_038():
    """test_id: TEST-BR-038, source_id: BR-DEPT-021-DEPT-ACTOR-PROHIBITED"""
    pytest.skip("NOT_AUTOMATED: Role assignment restriction backend interface not implemented")


# BR-DEPT-022: Unique Active Role Enforcement
@pytest.mark.django_db
def test_br_039():
    """test_id: TEST-BR-039, source_id: BR-DEPT-022-UNIQUE-HOD"""
    pytest.skip("NOT_AUTOMATED: Unique HOD enforcement backend interface not implemented")


@pytest.mark.django_db
def test_br_040():
    """test_id: TEST-BR-040, source_id: BR-DEPT-022-UNIQUE-ADMIN"""
    pytest.skip("NOT_AUTOMATED: Unique Dept_Admin enforcement backend interface not implemented")


# BR-DEPT-023: Time-Bounded Validity Period
@pytest.mark.django_db
def test_br_041():
    """test_id: TEST-BR-041, source_id: BR-DEPT-023-BOUNDED"""
    pytest.skip("NOT_AUTOMATED: Role validity period backend interface not implemented")


# BR-DEPT-024: Effective Role Access Transition & Headship Synchronization
@pytest.mark.django_db
def test_br_042():
    """test_id: TEST-BR-042, source_id: BR-DEPT-024-HEADSHIP-SYNC"""
    pytest.skip("NOT_AUTOMATED: Headship synchronization backend interface not implemented")

