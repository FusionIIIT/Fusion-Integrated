"""ELM application and approval integration tests."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.elm.models import (
    ApprovalRoute,
    EmployeeContext,
    LeaveAccount,
    LeaveCategory,
    LeaveRequest,
    LeaveReservation,
    LeaveTransaction,
)
from modules.elm.selectors import history
from modules.elm.services import workflow as service

pytestmark = pytest.mark.django_db

EMPLOYEE = 101
UNIT_HEAD = 202
FINAL_AUTHORITY = 303


def actor(user_id, *permissions):
    return make_principal(
        user_id=user_id, kind="staff", active_role="staff", permissions=permissions
    )


def configure_category(code="CL", entitlement="8.00", counting="working_days"):
    category = LeaveCategory.objects.create(
        code=code,
        name=code,
        annual_entitlement=Decimal(entitlement),
        employee_scope="all",
        carry_forward=code in {"EL", "COL"},
        counting_rule=counting,
    )
    EmployeeContext.objects.create(
        user_id=EMPLOYEE,
        employee_kind="staff",
        designation="Lecturer",
        organizational_unit="Computer Science",
        unit_head_user_id=UNIT_HEAD,
    )
    ApprovalRoute.objects.create(
        employee_kind="staff",
        organizational_unit="",
        designation="",
        category=code,
        final_authority_user_id=FINAL_AUTHORITY,
        final_authority_role="Director",
        establishment_required=False,
    )
    LeaveAccount.objects.create(
        user_id=EMPLOYEE,
        category=category,
        year=timezone.localdate().year,
        annual_entitlement=Decimal(entitlement),
    )
    return category


def submit_cl(day, half=""):
    return service.submit(
        actor=actor(EMPLOYEE, "elm.request.create"),
        category_code="CL",
        starts_on=day,
        ends_on=day,
        reason="Personal leave",
        half_day=half,
    )


def test_half_day_cl_is_reserved_at_half_a_day():
    configure_category()
    day = timezone.localdate() + timedelta(days=3)
    row = submit_cl(day, "first")
    reservation = LeaveReservation.objects.get(request=row)
    assert reservation.amount == Decimal("0.50")
    assert row.status == "awaiting_unit_head"


def test_different_half_day_cl_requests_on_same_date_are_allowed():
    configure_category()
    day = timezone.localdate() + timedelta(days=3)
    first = submit_cl(day, "first")
    second = submit_cl(day, "second")
    assert first.pk != second.pk
    assert LeaveReservation.objects.filter(request__in=[first, second]).count() == 2


def test_overlapping_pending_leave_is_refused():
    configure_category()
    day = timezone.localdate() + timedelta(days=3)
    submit_cl(day, "first")
    with pytest.raises(ConflictError) as exc:
        submit_cl(day, "first")
    assert exc.value.code == "leave_overlap"


def test_non_cl_unit_head_recommendation_routes_on_without_charging():
    configure_category("EL", "30.00", "continuous")
    day = timezone.localdate() + timedelta(days=3)
    row = service.submit(
        actor=actor(EMPLOYEE, "elm.request.create"),
        category_code="EL",
        starts_on=day,
        ends_on=day + timedelta(days=1),
        reason="Medical leave",
    )
    service.review(
        request_id=row.pk,
        actor=actor(UNIT_HEAD, "elm.workflow.review"),
        action="not_recommended",
        note="Insufficient recommendation",
    )
    row.refresh_from_db()
    assert row.status == "awaiting_final"
    assert not LeaveTransaction.objects.filter(request=row, kind="charge").exists()
    assert row.events.filter(
        event_type="unit_head_reviewed", data__recommendation="not_recommended"
    ).exists()


def test_rejecting_cancellation_keeps_original_approval_and_balance():
    configure_category()
    day = timezone.localdate() + timedelta(days=10)
    applicant = actor(EMPLOYEE, "elm.request.create")
    unit_head = actor(UNIT_HEAD, "elm.workflow.review")
    original = service.submit(
        actor=applicant, category_code="CL", starts_on=day, ends_on=day, reason="Personal leave"
    )
    service.review(request_id=original.pk, actor=unit_head, action="approve")
    original.refresh_from_db()
    assert original.status == "approved"
    cancellation = service.cancel(request_id=original.pk, actor=applicant, reason="Plans changed")
    service.review(
        request_id=cancellation.pk, actor=unit_head, action="reject", note="Cancellation denied"
    )
    original.refresh_from_db()
    cancellation.refresh_from_db()
    assert original.status == "approved"
    assert cancellation.status == "rejected"
    assert not LeaveTransaction.objects.filter(request=cancellation, kind="reversal").exists()


def test_request_history_is_scoped_to_the_requested_user():
    category = LeaveCategory.objects.create(
        code="CL",
        name="Casual Leave",
        annual_entitlement=Decimal("8.00"),
        employee_scope="all",
        carry_forward=False,
        counting_rule="working_days",
    )
    for uid in (EMPLOYEE, UNIT_HEAD):
        LeaveRequest.objects.create(
            employee_user_id=uid,
            category=category,
            request_type="new",
            status="approved",
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate(),
            chargeable_days=Decimal("1"),
            reason="Test",
        )
    assert list(history(user_id=EMPLOYEE).values_list("employee_user_id", flat=True)) == [EMPLOYEE]
