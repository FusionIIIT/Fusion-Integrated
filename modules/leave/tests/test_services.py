"""Tests for leave application and transition services."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.leave.domain.state_machine import (
    APPLICANT_ACTION_REQUIRED,
    APPROVED,
    AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_SUBSTITUTE,
    AWAITING_UNIT_HEAD,
    CANCELLATION_PENDING_UNIT_HEAD,
    CANCELLED,
    REJECTED,
    WITHDRAWN,
)
from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveCategory,
)
from modules.leave.services import applications as leave_services

pytestmark = pytest.mark.django_db


# --- Helper Principal ---
class DummyPrincipal:
    def __init__(self, user_id=None, permissions=(), roles=(), actor_kind=None):
        self.user_id = user_id
        self.permissions = set(permissions)
        self.roles = set(roles)
        self.actor_kind = actor_kind

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

# --- Fixtures ---

@pytest.fixture
def cl_cat():
    return LeaveCategory.objects.create(code="CL", name="Casual Leave")

@pytest.fixture
def el_cat():
    return LeaveCategory.objects.create(code="EL", name="Earned Leave")

@pytest.fixture
def user_principal():
    return DummyPrincipal(user_id=1)

@pytest.fixture
def cl_balance(cl_cat):
    return LeaveBalance.objects.create(
        category=cl_cat, user_id=1, year=2026, balance_days=Decimal("8.0")
    )

@pytest.fixture
def el_balance(el_cat):
    return LeaveBalance.objects.create(
        category=el_cat, user_id=1, year=2026, balance_days=Decimal("30.0")
    )

@pytest.fixture
def application_instance(cl_cat, cl_balance):
    # Create a base application instance for testing transitions
    return LeaveApplication.objects.create(
        user_id=1,
        category=cl_cat,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        half_day="",
        days_charged=Decimal("2.0"),
        balance_deducted=Decimal("0.0"),
        reason="Test reason",
        is_station_leave=False,
        substitute_user_id=None,
        recommendation="",
        applicant_is_director=False,
        actual_resumption_date=None,
        resumption_status="none",
        status=AWAITING_UNIT_HEAD,
    )

@pytest.fixture
def director_app(cl_cat, cl_balance):
    # Application where applicant is a director
    return LeaveApplication.objects.create(
        user_id=1,
        category=cl_cat,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        half_day="",
        days_charged=Decimal("2.0"),
        balance_deducted=Decimal("0.0"),
        reason="Test reason",
        is_station_leave=False,
        substitute_user_id=None,
        recommendation="",
        applicant_is_director=True,
        actual_resumption_date=None,
        resumption_status="none",
        status=AWAITING_DIRECTOR_SELF_SANCTION,
    )

# --- Tests for actor_kind ---

def test_actor_kind_system(user_principal):
    assert leave_services.actor_kind(None) == "system"

def test_actor_kind_employee_own_application(user_principal, application_instance):
    # Acting on own application
    assert leave_services.actor_kind(user_principal, application_instance) == "employee"

def test_actor_kind_employee_other_application(user_principal, application_instance):
    # Acting on someone else's application (assuming user_id 2 is different)
    application_instance.user_id = 2
    application_instance.save()
    assert leave_services.actor_kind(user_principal, application_instance) == "employee"

def test_actor_kind_employee_other_application_staff(user_principal, application_instance):
    # Staff acting on someone else's application
    staff_principal = DummyPrincipal(user_id=3)
    application_instance.user_id = 2
    application_instance.save()
    assert leave_services.actor_kind(staff_principal, application_instance) == "employee"

def test_actor_kind_employee_own_application_staff(user_principal, application_instance):
    # Staff acting on own application
    staff_principal = DummyPrincipal(user_id=1)
    application_instance.user_id = 1
    application_instance.save()
    assert leave_services.actor_kind(staff_principal, application_instance) == "employee"

def test_actor_kind_unit_head(application_instance):
    # Unit Head principal
    uh_principal = DummyPrincipal(user_id=2, permissions=["leave_management.application.review"])
    assert leave_services.actor_kind(uh_principal, application_instance) == "unit_head"

def test_actor_kind_director(director_app):
    # Director principal acting on their own application
    director_principal = DummyPrincipal(user_id=1, permissions=["leave_management.application.review"])
    assert leave_services.actor_kind(director_principal, director_app) == "director"

# --- Tests for apply ---

@pytest.mark.django_db
def test_apply_cl_happy_path(cl_cat, cl_balance, user_principal):
    start_date = date(2026, 11, 2)
    end_date = date(2026, 11, 3)

    # Mock balance check to ensure it passes for this test
    # In a real scenario, the service would check the balance

    app = leave_services.apply(
        user_id=user_principal.user_id,
        category_code=cl_cat.code,
        start_date=start_date,
        end_date=end_date,
        reason="Test reason",
    )

    assert app.status == AWAITING_UNIT_HEAD
    assert app.days_charged == Decimal("2.0")
    assert app.balance_deducted == Decimal("0.0")

    # Check transition record
    transitions = LeaveApplicationTransition.objects.filter(
        application=app
    ).order_by('at')
    assert transitions.count() == 1
    assert transitions.first().from_status == ""
    assert transitions.first().to_status == AWAITING_UNIT_HEAD

@pytest.mark.django_db
def test_apply_with_substitute(cl_cat, user_principal):
    app = leave_services.apply(
        user_id=user_principal.user_id,
        category_code=cl_cat.code,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Test reason",
        substitute_user_id=99,
    )
    assert app.status == AWAITING_SUBSTITUTE

@pytest.mark.django_db
def test_apply_applicant_director(cl_cat, user_principal):
    app = leave_services.apply(
        user_id=user_principal.user_id,
        category_code=cl_cat.code,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Test reason",
        applicant_is_director=True,
    )
    assert app.status == AWAITING_DIRECTOR_SELF_SANCTION

@pytest.mark.django_db
def test_apply_end_before_start_raises(cl_cat, user_principal):
    with pytest.raises(ConflictError) as excinfo:
        leave_services.apply(
            user_id=user_principal.user_id,
            category_code=cl_cat.code,
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 4),
            reason="Test reason",
        )
    assert "end_date must be on or after start_date" in str(excinfo.value)

@pytest.mark.django_db
def test_apply_overlap_raises(cl_cat, user_principal):
    # Setup existing application
    LeaveApplication.objects.create(
        user_id=user_principal.user_id,
        category=cl_cat,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5),
        half_day="",
        days_charged=Decimal("5.0"),
        balance_deducted=Decimal("5.0"),
        reason="Existing",
        is_station_leave=False,
        substitute_user_id=None,
        recommendation="",
        applicant_is_director=False,
        actual_resumption_date=None,
        resumption_status="none",
        status=AWAITING_UNIT_HEAD,
    )

    # Attempt to apply for overlapping dates
    with pytest.raises(ConflictError) as excinfo:
        leave_services.apply(
            user_id=user_principal.user_id,
            category_code=cl_cat.code,
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 7),
            reason="Overlap test",
        )
    assert "Application overlaps with an existing active leave" in str(excinfo.value)

@pytest.mark.django_db
def test_apply_insufficient_balance_raises(cl_cat, cl_balance, user_principal):
    # Balance is 8.0 days. Nov 1 to Nov 13 has 10 working days (> 8.0).
    with pytest.raises(ConflictError) as excinfo:
        leave_services.apply(
            user_id=user_principal.user_id,
            category_code=cl_cat.code,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 13),
            reason="Insufficient balance test",
        )
    assert "Insufficient leave balance" in str(excinfo.value)

# --- Tests for transition ---

@pytest.mark.django_db
def test_transition_unit_head_approve_cl_deducts_balance(cl_cat, cl_balance, application_instance, user_principal):
    # Application starts in AWAITING_UNIT_HEAD

    # Unit Head principal (assuming permission P_REVIEW)
    uh_principal = DummyPrincipal(user_id=2, permissions=["leave_management.application.review"])

    # Transition to Approved
    app = leave_services.transition(
        application_id=application_instance.pk,
        to_status=APPROVED,
        actor=uh_principal,
        reason="Approved by Unit Head",
    )

    assert app.status == APPROVED
    assert app.balance_deducted == Decimal("2.0")

    # Check balance deduction
    balance = LeaveBalance.objects.get(
        category=cl_cat, user_id=1, year=2026
    )
    assert balance.balance_days == Decimal("6.0")

@pytest.mark.django_db
def test_transition_unit_head_reject_requires_reason(cl_cat, application_instance, user_principal):
    uh_principal = DummyPrincipal(user_id=2, permissions=["leave_management.application.review"])

    # 1. Reject without reason (should fail guard)
    with pytest.raises(ConflictError) as excinfo:
        leave_services.transition(
            application_id=application_instance.pk,
            to_status=REJECTED,
            actor=uh_principal,
            reason="",
        )
    assert "A reason is required for this decision" in str(excinfo.value)

    # 2. Reject with reason (should succeed)
    app = leave_services.transition(
        application_id=application_instance.pk,
        to_status=REJECTED,
        actor=uh_principal,
        reason="Not enough coverage",
    )
    assert app.status == REJECTED
    # Balance should NOT be deducted on rejection
    balance = LeaveBalance.objects.get(
        category=cl_cat, user_id=1, year=2026
    )
    assert balance.balance_days == Decimal("8.0")

@pytest.mark.django_db
def test_transition_substitute_accept_and_decline(cl_cat, user_principal):
    # Setup application in AWAITING_SUBSTITUTE
    app = LeaveApplication.objects.create(
        user_id=1,
        category=cl_cat,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        half_day="",
        days_charged=Decimal("2.0"),
        balance_deducted=Decimal("0.0"),
        reason="Test reason",
        is_station_leave=False,
        substitute_user_id=99,
        recommendation="",
        applicant_is_director=False,
        actual_resumption_date=None,
        resumption_status="none",
        status=AWAITING_SUBSTITUTE,
    )

    sub_principal = DummyPrincipal(user_id=99, permissions=["leave_management.application.respond"])

    # 1. Substitute accepts
    app = leave_services.transition(
        application_id=app.pk,
        to_status=AWAITING_UNIT_HEAD,
        actor=sub_principal,
        reason="Accepted",
    )
    assert app.status == AWAITING_UNIT_HEAD
    assert app.substitute_response == "accepted"

    # Reset app for decline test
    app.status = AWAITING_SUBSTITUTE
    app.substitute_response = "pending"
    app.save()

    # 2. Substitute declines
    app = leave_services.transition(
        application_id=app.pk,
        to_status=APPLICANT_ACTION_REQUIRED,
        actor=sub_principal,
        reason="Declined due to conflict",
    )
    assert app.status == APPLICANT_ACTION_REQUIRED
    assert app.substitute_response == "declined"

@pytest.mark.django_db
def test_transition_withdraw_pending(cl_cat, application_instance, user_principal):
    # Application starts in AWAITING_UNIT_HEAD

    # Employee principal (applicant)
    employee_principal = DummyPrincipal(user_id=1, permissions=["leave_management.application.delete"])

    app = leave_services.transition(
        application_id=application_instance.pk,
        to_status=WITHDRAWN,
        actor=employee_principal,
        reason="Personal reasons",
    )
    assert app.status == WITHDRAWN
    assert app.withdrawn_reason == "Personal reasons"

@pytest.mark.django_db
def test_transition_cancellation_restores_balance(cl_cat, cl_balance, user_principal):
    # 1. Setup: Approved application with 2.0 days deducted
    cl_balance.balance_days = Decimal("6.0")
    cl_balance.save()

    app = LeaveApplication.objects.create(
        user_id=user_principal.user_id,
        category=cl_cat,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        half_day="",
        days_charged=Decimal("2.0"),
        balance_deducted=Decimal("2.0"),
        reason="Original reason",
        is_station_leave=False,
        substitute_user_id=None,
        recommendation="",
        applicant_is_director=False,
        actual_resumption_date=None,
        resumption_status="none",
        status=APPROVED,
    )

    # Verify initial balance before cancellation
    balance = LeaveBalance.objects.get(category=cl_cat, user_id=1, year=2026)
    assert balance.balance_days == Decimal("6.0")

    # 2. Employee requests cancellation (Approved -> Cancellation Pending Unit Head)
    employee_principal = DummyPrincipal(user_id=1, permissions=["leave_management.application.create"])
    app = leave_services.transition(
        application_id=app.pk,
        to_status=CANCELLATION_PENDING_UNIT_HEAD,
        actor=employee_principal,
        reason="Cancel before start",
    )
    assert app.status == CANCELLATION_PENDING_UNIT_HEAD

    # 3. Unit Head approves cancellation (Cancellation Pending Unit Head -> Cancelled)
    uh_principal = DummyPrincipal(user_id=2, permissions=["leave_management.application.review"])
    app = leave_services.transition(
        application_id=app.pk,
        to_status=CANCELLED,
        actor=uh_principal,
        reason="Cancellation approved",
    )
    assert app.status == CANCELLED
    assert app.balance_deducted == Decimal("0.0") # Balance should be reset

    # Check balance restoration
    balance = LeaveBalance.objects.get(
        category=cl_cat, user_id=1, year=2026
    )
    assert balance.balance_days == Decimal("8.0")

@pytest.mark.django_db
def test_transition_unauthorized_actor_raises(cl_cat, application_instance, user_principal):
    # 1. Employee attempting to approve (state machine rejects employee actor)
    employee_principal = DummyPrincipal(user_id=1, permissions=["leave_management.application.delete"])
    with pytest.raises(PermissionDeniedError) as excinfo:
        leave_services.transition(
            application_id=application_instance.pk,
            to_status=APPROVED,
            actor=employee_principal,
            reason="Attempt to approve",
        )
    assert "Your role cannot make that change." in str(excinfo.value) or "This action needs" in str(excinfo.value)

    # 2. User with unit_head role but without required review permission
    unauthorized_principal = DummyPrincipal(user_id=99, permissions=[], actor_kind="unit_head")
    with pytest.raises(PermissionDeniedError) as excinfo:
        leave_services.transition(
            application_id=application_instance.pk,
            to_status=APPROVED,
            actor=unauthorized_principal,
            reason="Attempt to approve",
        )
    assert "This action needs leave_management.application.review" in str(excinfo.value)
