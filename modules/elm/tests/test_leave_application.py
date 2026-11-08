from datetime import date
from decimal import Decimal

import pytest

from modules.directory.models import UserRef
from modules.elm.domain.leave_rules import LeaveRuleError
from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationStatus,
    LeaveBalance,
    LeaveRoutingRule,
    LeaveType,
)
from modules.elm.services.leave_application import (
    submit_leave_application,
    validate_leave_application,
)


class FakePrincipal:
    def __init__(self, user_id, permissions, active_role="faculty"):
        self.user_id = user_id
        self.permissions = set(permissions)
        self.active_role = active_role

    def has_permission(self, permission_code):
        return permission_code in self.permissions


@pytest.fixture
def cl_balance(db):
    return LeaveBalance.objects.create(
        user_id=201,
        leave_type=LeaveType.CL,
        leave_year=2026,
        entitlement=Decimal("8"),
        available_balance=Decimal("8"),
    )


def validate_cl(**overrides):
    data = {
        "user_id": 201,
        "leave_type": LeaveType.CL,
        "start_date": date(2026, 10, 20),
        "end_date": date(2026, 10, 20),
        "requested_days": Decimal("1"),
    }
    data.update(overrides)
    return validate_leave_application(**data)


@pytest.mark.django_db
def test_valid_cl_request_passes(cl_balance):
    assert validate_cl() is None


@pytest.mark.django_db
def test_half_day_cl_request_passes(cl_balance):
    assert (
        validate_cl(
            requested_days=Decimal("0.5"),
            half_day="first_half",
        )
        is None
    )


@pytest.mark.django_db
def test_half_day_not_allowed_for_multiple_dates(cl_balance):
    with pytest.raises(LeaveRuleError, match="single-date CL"):
        validate_cl(
            end_date=date(2026, 10, 21),
            half_day="first_half",
            requested_days=Decimal("0.5"),
        )


@pytest.mark.django_db
def test_half_day_must_be_half_a_day(cl_balance):
    with pytest.raises(LeaveRuleError, match=r"exactly 0\.5"):
        validate_cl(
            requested_days=Decimal("1"),
            half_day="first_half",
        )


@pytest.mark.django_db
def test_overlapping_pending_request_is_rejected(cl_balance):
    LeaveApplication.objects.create(
        user_id=201,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("1"),
        status=LeaveApplicationStatus.PENDING,
    )

    with pytest.raises(LeaveRuleError, match="overlaps"):
        validate_cl()


@pytest.mark.django_db
def test_opposite_cl_halves_can_coexist(cl_balance):
    LeaveApplication.objects.create(
        user_id=201,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("0.5"),
        half_day="first_half",
        status=LeaveApplicationStatus.APPROVED,
    )

    assert (
        validate_cl(
            requested_days=Decimal("0.5"),
            half_day="second_half",
        )
        is None
    )


@pytest.mark.django_db
def test_same_cl_half_cannot_be_requested_twice(cl_balance):
    LeaveApplication.objects.create(
        user_id=201,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("0.5"),
        half_day="first_half",
        status=LeaveApplicationStatus.PENDING,
    )

    with pytest.raises(LeaveRuleError, match="overlaps"):
        validate_cl(
            requested_days=Decimal("0.5"),
            half_day="first_half",
        )


@pytest.mark.django_db
def test_withdrawn_request_does_not_block_new_request(cl_balance):
    LeaveApplication.objects.create(
        user_id=201,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("1"),
        status=LeaveApplicationStatus.WITHDRAWN,
    )

    assert validate_cl() is None


@pytest.mark.django_db
def test_insufficient_balance_is_rejected(cl_balance):
    with pytest.raises(LeaveRuleError, match="Insufficient"):
        validate_cl(
            requested_days=Decimal("9"),
            end_date=date(2026, 10, 28),
        )


@pytest.mark.django_db
def test_cross_year_el_checks_both_year_balances():
    LeaveBalance.objects.create(
        user_id=301,
        leave_type=LeaveType.EL,
        leave_year=2026,
        entitlement=Decimal("30"),
        available_balance=Decimal("5"),
    )
    LeaveBalance.objects.create(
        user_id=301,
        leave_type=LeaveType.EL,
        leave_year=2027,
        entitlement=Decimal("30"),
        available_balance=Decimal("5"),
    )

    # Dec 29, 2026 through Jan 3, 2027 = 6 calendar days:
    # 3 days in 2026 and 3 days in 2027.
    assert (
        validate_leave_application(
            user_id=301,
            leave_type=LeaveType.EL,
            start_date=date(2026, 12, 29),
            end_date=date(2027, 1, 3),
            requested_days=Decimal("6"),
        )
        is None
    )


@pytest.mark.django_db
def test_cross_year_el_rejects_insufficient_balance_in_second_year():
    LeaveBalance.objects.create(
        user_id=302,
        leave_type=LeaveType.EL,
        leave_year=2026,
        entitlement=Decimal("30"),
        available_balance=Decimal("5"),
    )
    LeaveBalance.objects.create(
        user_id=302,
        leave_type=LeaveType.EL,
        leave_year=2027,
        entitlement=Decimal("30"),
        available_balance=Decimal("2"),
    )

    with pytest.raises(LeaveRuleError, match="Insufficient"):
        validate_leave_application(
            user_id=302,
            leave_type=LeaveType.EL,
            start_date=date(2026, 12, 29),
            end_date=date(2027, 1, 3),
            requested_days=Decimal("6"),
        )


@pytest.mark.django_db
def test_cross_year_el_requires_both_year_balances():
    LeaveBalance.objects.create(
        user_id=303,
        leave_type=LeaveType.EL,
        leave_year=2026,
        entitlement=Decimal("30"),
        available_balance=Decimal("10"),
    )

    with pytest.raises(LeaveRuleError, match="balance exists for year 2027"):
        validate_leave_application(
            user_id=303,
            leave_type=LeaveType.EL,
            start_date=date(2026, 12, 29),
            end_date=date(2027, 1, 3),
            requested_days=Decimal("6"),
        )


@pytest.mark.django_db
def test_cross_year_cl_requires_balance_for_each_year(cl_balance):
    with pytest.raises(
        LeaveRuleError,
        match="No CL balance exists for year 2027",
    ):
        validate_leave_application(
            user_id=201,
            leave_type=LeaveType.CL,
            start_date=date(2026, 12, 31),
            end_date=date(2027, 1, 1),
            requested_days=Decimal("2"),
        )


@pytest.mark.django_db
def test_submission_creates_pending_request_without_deducting_balance(
    cl_balance,
):
    UserRef.objects.create(
        user_id=201,
        username="applicant",
        display_name="Applicant",
        kind="faculty",
        department="CSE",
        is_active=True,
    )

    UserRef.objects.create(
        user_id=202,
        username="unithead",
        display_name="Unit Head",
        kind="staff",
        department="CSE",
        is_active=True,
    )

    LeaveRoutingRule.objects.create(
        department="CSE",
        applicant_designation="faculty",
        leave_type=LeaveType.CL,
        unit_head_user_id=202,
    )

    actor = FakePrincipal(
        user_id=201,
        permissions={"elm.leave_application.create"},
    )

    application = submit_leave_application(
        actor=actor,
        user_id=201,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("1"),
        reason="Personal work",
    )

    cl_balance.refresh_from_db()

    assert application.pk is not None
    assert application.status == LeaveApplicationStatus.PENDING
    assert application.reason == "Personal work"
    assert application.assigned_unit_head_user_id == 202
    assert application.assigned_final_authority_user_id == 202
    assert application.workflow_stage == "awaiting_unit_head_review"
    assert application.establishment_required is False
    assert cl_balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_submission_rejects_invalid_request_without_creating_application(
    cl_balance,
):
    actor = FakePrincipal(
        user_id=201,
        permissions={"elm.leave_application.create"},
    )

    with pytest.raises(LeaveRuleError):
        submit_leave_application(
            actor=actor,
            user_id=201,
            leave_type=LeaveType.CL,
            start_date=date(2026, 10, 21),
            end_date=date(2026, 10, 20),
            requested_days=Decimal("1"),
        )

    assert not LeaveApplication.objects.filter(user_id=201).exists()
    cl_balance.refresh_from_db()
    assert cl_balance.available_balance == Decimal("8")


@pytest.mark.django_db
def test_higher_sanction_leave_routes_to_final_authority():
    LeaveBalance.objects.create(
        user_id=301,
        leave_type=LeaveType.EL,
        leave_year=2026,
        entitlement=Decimal("30"),
        available_balance=Decimal("30"),
    )

    for user_id, username, name, kind in [
        (301, "employee", "Employee", "faculty"),
        (302, "unithead", "Unit Head", "staff"),
        (303, "authority", "Final Authority", "staff"),
    ]:
        UserRef.objects.create(
            user_id=user_id,
            username=username,
            display_name=name,
            kind=kind,
            department="CSE",
            is_active=True,
        )

    LeaveRoutingRule.objects.create(
        department="CSE",
        applicant_designation="faculty",
        leave_type=LeaveType.EL,
        unit_head_user_id=302,
        final_authority_user_id=303,
        establishment_required=True,
    )

    actor = FakePrincipal(
        user_id=301,
        permissions={"elm.leave_application.create"},
    )

    application = submit_leave_application(
        actor=actor,
        user_id=301,
        leave_type=LeaveType.EL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("1"),
    )

    assert application.assigned_unit_head_user_id == 302
    assert application.assigned_final_authority_user_id == 303
    assert application.establishment_required is True
    assert application.workflow_stage == "awaiting_unit_head_review"


@pytest.mark.django_db
def test_director_self_sanction_routes_to_director(cl_balance):
    UserRef.objects.create(
        user_id=201,
        username="director",
        display_name="Director",
        kind="staff",
        department="Administration",
        is_active=True,
    )

    LeaveRoutingRule.objects.create(
        department="Administration",
        applicant_designation="Director",
        leave_type=LeaveType.CL,
        director_self_sanction=True,
    )

    actor = FakePrincipal(
        user_id=201,
        permissions={"elm.leave_application.create"},
        active_role="Director",
    )

    application = submit_leave_application(
        actor=actor,
        user_id=201,
        leave_type=LeaveType.CL,
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        requested_days=Decimal("1"),
    )

    assert application.assigned_unit_head_user_id is None
    assert application.assigned_final_authority_user_id == 201
    assert application.workflow_stage == "awaiting_director_self_sanction"


@pytest.mark.django_db
def test_submission_rejects_missing_routing_configuration(cl_balance):
    UserRef.objects.create(
        user_id=201,
        username="applicant",
        display_name="Applicant",
        kind="faculty",
        department="CSE",
        is_active=True,
    )

    actor = FakePrincipal(
        user_id=201,
        permissions={"elm.leave_application.create"},
    )

    with pytest.raises(LeaveRuleError, match="routing rule"):
        submit_leave_application(
            actor=actor,
            user_id=201,
            leave_type=LeaveType.CL,
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 20),
            requested_days=Decimal("1"),
        )

    assert not LeaveApplication.objects.filter(user_id=201).exists()
