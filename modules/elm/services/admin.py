"""Administrative maintenance, configuration, and offline leave services."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.elm.domain.constants import (
    ApplicationStatus,
    TransactionType,
)
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.validation import (
    validate_balance_sufficient,
    validate_category_eligibility,
    validate_overlap,
)
from modules.elm.models import (
    ApprovalHierarchy,
    Holiday,
    HolidayCalendar,
    LeaveApplication,
    LeaveAuditLog,
    LeavePolicyConfig,
    SlaThresholdConfig,
    VacationPeriod,
)
from modules.elm.selectors.balances import get_balances_for_user
from modules.elm.selectors.calendars import get_closed_holidays_set
from modules.elm.selectors.config import get_active_policy_config
from modules.elm.selectors.leaves import (
    get_active_or_pending_leaves_for_user,
    get_application_by_id,
)
from modules.elm.services.balances import (
    debit_leave_balance,
    ensure_leave_accounts_for_user,
)


@transaction.atomic
def record_offline_leave(
    *,
    employee_user_id: int,
    user_kind: str,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    offline_reference_no: str,
    offline_sanction_date: date,
    offline_sanctioning_authority: str,
    recorded_by_user_id: int,
    is_half_day: bool = False,
    half_day_session: str | None = None,
) -> LeaveApplication:
    """Record already-sanctioned offline leave without a second approval workflow.

    Enforces BR-EL-029, CFR-EL-027, EL-UC-016:
    - Captures sanction/reference evidence
    - Validates record consistency (balance, overlap)
    - Synchronizes balance and records leave directly as APPROVED
    - Does NOT initiate second approval workflow
    """
    if not offline_reference_no or not offline_sanctioning_authority:
        raise BadRequestError("Offline sanction reference number and authority name are required.")

    validate_category_eligibility(category, user_kind)
    year = start_date.year
    ensure_leave_accounts_for_user(employee_user_id, year, user_kind)

    closed_holidays = get_closed_holidays_set(year)
    chargeable_days = calculate_chargeable_days(
        category,
        start_date,
        end_date,
        is_half_day=is_half_day,
        closed_holidays=closed_holidays,
    )

    balances = get_balances_for_user(employee_user_id, year)
    avail_balance = balances.get(category, Decimal("0.00"))
    validate_balance_sufficient(avail_balance, chargeable_days, category)

    existing_leaves = get_active_or_pending_leaves_for_user(employee_user_id)
    validate_overlap(
        existing_leaves,
        start_date,
        end_date,
        is_half_day=is_half_day,
        half_day_session=half_day_session,
    )

    # Directly create as APPROVED without workflow tasks
    app = LeaveApplication.objects.create(
        user_id=employee_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_session=half_day_session if is_half_day else None,
        chargeable_days=chargeable_days,
        purpose=purpose,
        status=ApplicationStatus.APPROVED.value,
        final_decision="approved",
        final_decision_at=timezone.now(),
        final_decision_by_user_id=recorded_by_user_id,
        final_decision_remarks=f"Offline sanction ref {offline_reference_no}",
        is_offline_record=True,
        offline_reference_no=offline_reference_no,
        offline_sanction_date=offline_sanction_date,
        offline_sanctioning_authority=offline_sanctioning_authority,
    )

    # Debit balance
    debit_leave_balance(
        user_id=employee_user_id,
        year=year,
        category=category,
        amount=chargeable_days,
        reference_id=f"offline-{app.id}",
        remarks=f"Offline sanction sync: ref {offline_reference_no}",
        performed_by_user_id=recorded_by_user_id,
        transaction_type=TransactionType.OFFLINE_SANCTION_DEBIT.value,
    )

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=recorded_by_user_id,
        action="record_offline_leave",
        from_state="offline",
        to_state=ApplicationStatus.APPROVED.value,
        remarks=f"Offline leave recorded: ref {offline_reference_no}",
        payload={"offline_ref": offline_reference_no, "chargeable_days": str(chargeable_days)},
    )

    return app


@transaction.atomic
def maintain_leave_record(
    application_id: int,
    admin_user_id: int,
    *,
    reason_note: str,
    new_purpose: str | None = None,
    new_medical_certificate: str | None = None,
) -> LeaveApplication:
    """Authorized leave record maintenance/correction (EL-UC-017, BR-EL-037).

    Does NOT create a new sanctioning decision.
    """
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    update_fields = ["updated_at"]
    if new_purpose is not None:
        app.purpose = new_purpose
        update_fields.append("purpose")
    if new_medical_certificate is not None:
        app.medical_certificate = new_medical_certificate
        update_fields.append("medical_certificate")

    app.save(update_fields=update_fields)

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=admin_user_id,
        action="admin_maintenance",
        from_state=app.status,
        to_state=app.status,
        remarks=reason_note or "Administrative record maintenance",
    )

    return app


@transaction.atomic
def update_policy_config(
    admin_user_id: int,
    **kwargs,
) -> LeavePolicyConfig:
    """Update active leave policy configuration directly (EL-UC-014, BR-EL-030)."""
    cfg = get_active_policy_config()
    for field, val in kwargs.items():
        if hasattr(cfg, field):
            setattr(cfg, field, val)
    cfg.save()
    return cfg


@transaction.atomic
def create_or_update_holiday_calendar(
    year: int,
    label: str = "",
) -> HolidayCalendar:
    """Create or update a holiday calendar for a year (EL-UC-015)."""
    cal, _ = HolidayCalendar.objects.update_or_create(
        year=year,
        defaults={"label": label},
    )
    return cal


@transaction.atomic
def publish_holiday_calendar(
    calendar_id: int,
    admin_user_id: int,
) -> HolidayCalendar:
    """Publish a holiday calendar (BR-EL-031)."""
    cal = HolidayCalendar.objects.filter(id=calendar_id).first()
    if not cal:
        raise NotFoundError(f"Calendar #{calendar_id} not found.")

    # Unpublish any previous calendar for the same year
    HolidayCalendar.objects.filter(year=cal.year).exclude(id=cal.id).update(is_published=False)

    cal.is_published = True
    cal.published_at = timezone.now()
    cal.published_by_user_id = admin_user_id
    cal.save(update_fields=["is_published", "published_at", "published_by_user_id", "updated_at"])
    return cal


@transaction.atomic
def add_holiday(
    calendar_id: int,
    holiday_date: date,
    name: str,
    holiday_type: str,
    description: str = "",
) -> Holiday:
    """Add a holiday to a calendar."""
    cal = HolidayCalendar.objects.filter(id=calendar_id).first()
    if not cal:
        raise NotFoundError(f"Calendar #{calendar_id} not found.")

    h, _ = Holiday.objects.update_or_create(
        calendar=cal,
        date=holiday_date,
        holiday_type=holiday_type,
        defaults={"name": name, "description": description},
    )
    return h


@transaction.atomic
def create_vacation_period(
    academic_year: str,
    name: str,
    start_date: date,
    end_date: date,
) -> VacationPeriod:
    """Add an external academic calendar vacation period for faculty VL (BR-EL-006)."""
    return VacationPeriod.objects.create(
        academic_year=academic_year,
        name=name,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )


@transaction.atomic
def configure_sla_threshold(
    task_type: str,
    reminder_hours: int,
    escalation_hours: int,
    escalation_action: str = "notify_only",
    escalation_target_role: str = "",
) -> SlaThresholdConfig:
    """Configure SLA thresholds for an actionable task class (EL-UC-018, BR-EL-038)."""
    cfg, _ = SlaThresholdConfig.objects.update_or_create(
        task_type=task_type,
        defaults={
            "reminder_threshold_hours": reminder_hours,
            "escalation_threshold_hours": escalation_hours,
            "escalation_action": escalation_action,
            "escalation_target_role": escalation_target_role,
            "is_active": True,
        },
    )
    return cfg


@transaction.atomic
def configure_approval_hierarchy(
    *,
    unit_head_user_id: int,
    sanctioning_authority_user_id: int,
    sanctioning_authority_role: str = "Dean",
    department: str = "",
    designation: str = "",
    applicant_user_id: int | None = None,
    leave_category: str = "",
    establishment_user_id: int | None = None,
    requires_establishment_step: bool = True,
) -> ApprovalHierarchy:
    """Configure approval routing hierarchy."""
    return ApprovalHierarchy.objects.create(
        unit_head_user_id=unit_head_user_id,
        sanctioning_authority_user_id=sanctioning_authority_user_id,
        sanctioning_authority_role=sanctioning_authority_role,
        department=department,
        designation=designation,
        applicant_user_id=applicant_user_id,
        leave_category=leave_category,
        establishment_user_id=establishment_user_id,
        requires_establishment_step=requires_establishment_step,
        is_active=True,
    )
