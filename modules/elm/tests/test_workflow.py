"""ELM application and approval integration tests."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError, PermissionDeniedError
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
SUBSTITUTE = 404
REPLACEMENT = 505


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


def test_substitute_must_have_dedicated_permission():
    configure_category()
    EmployeeContext.objects.create(
        user_id=SUBSTITUTE,
        employee_kind="staff",
        designation="Lecturer",
        organizational_unit="Computer Science",
    )
    day = timezone.localdate() + timedelta(days=3)
    row = service.submit(
        actor=actor(EMPLOYEE, "elm.request.create"),
        category_code="CL",
        starts_on=day,
        ends_on=day,
        reason="Personal leave",
        substitute_required=True,
        substitute_user_id=SUBSTITUTE,
    )
    with pytest.raises(PermissionDeniedError):
        service.substitute_response(
            request_id=row.pk, actor=actor(SUBSTITUTE, "elm.request.create"), accept=True
        )
    row.refresh_from_db()
    assert row.status == "awaiting_substitute"


def test_replacing_declined_substitute_requires_request_permission():
    configure_category()
    for uid in (SUBSTITUTE, REPLACEMENT):
        EmployeeContext.objects.create(
            user_id=uid,
            employee_kind="staff",
            designation="Lecturer",
            organizational_unit="Computer Science",
        )
    day = timezone.localdate() + timedelta(days=3)
    row = service.submit(
        actor=actor(EMPLOYEE, "elm.request.create"),
        category_code="CL",
        starts_on=day,
        ends_on=day,
        reason="Personal leave",
        substitute_required=True,
        substitute_user_id=SUBSTITUTE,
    )
    service.substitute_response(
        request_id=row.pk, actor=actor(SUBSTITUTE, "elm.substitute.respond"), accept=False
    )
    with pytest.raises(PermissionDeniedError):
        service.substitute_response(
            request_id=row.pk,
            actor=actor(EMPLOYEE, "elm.substitute.respond"),
            accept=False,
            replacement_user_id=REPLACEMENT,
        )
    row.refresh_from_db()
    assert row.status == "applicant_action_required"


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


def test_offline_record_enforces_category_employee_scope():
    category = configure_category()
    category.employee_scope = "faculty"
    category.save(update_fields=["employee_scope"])
    day = timezone.localdate() + timedelta(days=3)
    with pytest.raises(ConflictError) as exc:
        service.record_offline(
            actor=actor(707, "elm.account.manage"),
            user_id=EMPLOYEE,
            category_code="CL",
            starts_on=day,
            ends_on=day,
            reason="Previously sanctioned",
            sanction_reference="PAPER-2026-1",
        )
    assert exc.value.code == "leave_category_ineligible"
    assert not LeaveRequest.objects.filter(request_type="offline").exists()


def test_extension_from_original_uses_latest_approved_extension_end():
    category = configure_category("EL", "30.00", "continuous")
    today = timezone.localdate()
    route = {"unit_head_user_id": UNIT_HEAD, "final_authority_user_id": FINAL_AUTHORITY}
    original = LeaveRequest.objects.create(
        employee_user_id=EMPLOYEE,
        category=category,
        request_type="new",
        status="approved",
        starts_on=today - timedelta(days=2),
        ends_on=today + timedelta(days=1),
        chargeable_days=Decimal("4"),
        reason="Earned leave",
        route_snapshot=route,
    )
    LeaveRequest.objects.create(
        employee_user_id=EMPLOYEE,
        category=category,
        request_type="extension",
        status="approved",
        starts_on=today + timedelta(days=2),
        ends_on=today + timedelta(days=3),
        chargeable_days=Decimal("2"),
        reason="First extension",
        original_leave=original,
        route_snapshot=route,
    )

    extension = service.extend(
        request_id=original.pk,
        actor=actor(EMPLOYEE, "elm.request.create"),
        ends_on=today + timedelta(days=5),
        reason="Second extension",
    )

    assert extension.starts_on == today + timedelta(days=4)
    assert extension.original_leave_id == original.pk


def test_resumption_adjustment_uses_original_and_approved_extension_periods():
    category = configure_category("EL", "30.00", "continuous")
    today = timezone.localdate()
    route = {"unit_head_user_id": UNIT_HEAD, "final_authority_user_id": FINAL_AUTHORITY}
    original = LeaveRequest.objects.create(
        employee_user_id=EMPLOYEE,
        category=category,
        request_type="new",
        status="approved",
        starts_on=today - timedelta(days=10),
        ends_on=today - timedelta(days=6),
        chargeable_days=Decimal("5"),
        reason="Earned leave",
        route_snapshot=route,
    )
    extension = LeaveRequest.objects.create(
        employee_user_id=EMPLOYEE,
        category=category,
        request_type="extension",
        status="approved",
        starts_on=today - timedelta(days=5),
        ends_on=today - timedelta(days=3),
        chargeable_days=Decimal("3"),
        reason="Extension",
        original_leave=original,
        route_snapshot=route,
    )
    account = LeaveAccount.objects.get(user_id=EMPLOYEE, category=category, year=today.year)
    LeaveTransaction.objects.create(
        account=account,
        request=original,
        kind="charge",
        amount=Decimal("-5"),
        reference="original",
        note="Original approved period",
    )
    LeaveTransaction.objects.create(
        account=account,
        request=extension,
        kind="charge",
        amount=Decimal("-3"),
        reference="extension",
        note="Approved extension period",
    )

    record = service.report_resumption(
        request_id=original.pk,
        actor=actor(EMPLOYEE, "elm.request.create"),
        actual_return_date=today - timedelta(days=1),
    )
    service.review_resumption(
        resumption_id=record.pk, actor=actor(FINAL_AUTHORITY, "elm.workflow.review")
    )

    adjustment = account.transactions.get(kind="resumption_adjustment")
    assert adjustment.amount == Decimal("-2")
    assert sum(account.transactions.values_list("amount", flat=True), Decimal("0")) == Decimal(
        "-10"
    )


def test_resumption_rejects_duplicate_pending_and_reviewed_reports():
    category = configure_category("EL", "30.00", "continuous")
    today = timezone.localdate()
    original = LeaveRequest.objects.create(
        employee_user_id=EMPLOYEE,
        category=category,
        request_type="new",
        status="approved",
        starts_on=today - timedelta(days=3),
        ends_on=today - timedelta(days=1),
        chargeable_days=Decimal("3"),
        reason="Earned leave",
        route_snapshot={"final_authority_user_id": FINAL_AUTHORITY},
    )
    args = {
        "request_id": original.pk,
        "actor": actor(EMPLOYEE, "elm.request.create"),
        "actual_return_date": today - timedelta(days=1),
    }
    record = service.report_resumption(**args)
    with pytest.raises(ConflictError) as pending:
        service.report_resumption(**args)
    assert pending.value.code == "resumption_already_reported"

    service.review_resumption(
        resumption_id=record.pk, actor=actor(FINAL_AUTHORITY, "elm.workflow.review")
    )
    with pytest.raises(ConflictError) as reviewed:
        service.report_resumption(**args)
    assert reviewed.value.code == "resumption_already_reported"


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
