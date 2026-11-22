from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from rest_framework.exceptions import ValidationError

from fusion_auth.client import IamUnavailable
from modules.leave import contracts
from modules.leave.models import (
    AuthorityRoute,
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeavePolicy,
    LeaveRecordCorrection,
    SlaConfiguration,
)
from modules.leave.services import accounts


def save_policy(*, actor_user_id: int, data: dict) -> LeavePolicy:
    leave_type = data["leave_type"]
    if leave_type not in {"CL", "RH", "SCL", "EL", "COL", "VL"}:
        raise ValidationError("Unknown leave category.")
    return LeavePolicy.objects.update_or_create(
        leave_type=leave_type,
        defaults={
            "annual_entitlement": data["annual_entitlement"],
            "applies_to": data.get("applies_to", "all"),
            "carry_forward": data.get("carry_forward", False),
            "substitute_required": data.get("substitute_required", False),
            "medical_evidence_required": data.get("medical_evidence_required", False),
            "higher_sanction": leave_type in {"SCL", "EL", "COL", "VL"},
            "updated_by_user_id": actor_user_id,
        },
    )[0]


def save_route(*, actor_user_id: int, data: dict) -> AuthorityRoute:
    unit_key, leave_type = data["unit_key"].strip(), data["leave_type"]
    if not unit_key:
        raise ValidationError("An organizational unit key is required.")
    try:
        people = contracts.get_employees(
            [
                int(data["unit_head_user_id"]),
                *(
                    [int(data["establishment_user_id"])]
                    if data.get("establishment_user_id")
                    else []
                ),
                *(
                    [int(data["final_authority_user_id"])]
                    if data.get("final_authority_user_id")
                    else []
                ),
            ]
        )
    except IamUnavailable as exc:
        raise ValidationError("IAM employee directory is unavailable.") from exc
    expected = {int(data["unit_head_user_id"])}
    if data.get("establishment_user_id"):
        expected.add(int(data["establishment_user_id"]))
    if data.get("final_authority_user_id"):
        expected.add(int(data["final_authority_user_id"]))
    if not expected.issubset(people):
        raise ValidationError("Every configured route assignee must be an active employee.")
    return AuthorityRoute.objects.update_or_create(
        unit_key=unit_key,
        leave_type=leave_type,
        defaults={
            "unit_head_user_id": data["unit_head_user_id"],
            "establishment_required": data.get("establishment_required", False),
            "establishment_user_id": data.get("establishment_user_id"),
            "final_authority_user_id": data.get("final_authority_user_id"),
            "updated_by_user_id": actor_user_id,
        },
    )[0]


@transaction.atomic
def create_calendar(
    *,
    actor_user_id: int,
    name: str,
    effective_from: date,
    effective_to: date | None,
    dates: list[dict],
) -> HolidayCalendar:
    if effective_to and effective_to < effective_from:
        raise ValidationError("Calendar end date must not precede its start date.")
    calendar = HolidayCalendar.objects.create(
        name=name,
        effective_from=effective_from,
        effective_to=effective_to,
        created_by_user_id=actor_user_id,
    )
    HolidayDate.objects.bulk_create(
        [
            HolidayDate(
                calendar=calendar,
                date=item["date"],
                name=item["name"],
                is_restricted_holiday=item.get("is_restricted_holiday", False),
            )
            for item in dates
        ]
    )
    return calendar


@transaction.atomic
def publish_calendar(calendar: HolidayCalendar) -> HolidayCalendar:
    HolidayCalendar.objects.filter(is_current=True).exclude(pk=calendar.pk).update(is_current=False)
    calendar.is_published = True
    calendar.is_current = True
    calendar.save(update_fields=["is_published", "is_current"])
    return calendar


def save_sla(*, actor_user_id: int, task_kind: str, data: dict) -> SlaConfiguration:
    reminder = data.get("reminder_after_hours")
    escalation = data.get("escalation_after_hours")
    if reminder is not None and escalation is not None and escalation < reminder:
        raise ValidationError("Escalation must not precede the reminder threshold.")
    return SlaConfiguration.objects.update_or_create(
        task_kind=task_kind,
        defaults={
            "reminder_after_hours": reminder,
            "escalation_after_hours": escalation,
            "escalation_user_id": data.get("escalation_user_id"),
            "updated_by_user_id": actor_user_id,
        },
    )[0]


@transaction.atomic
def record_offline_leave(*, actor_user_id: int, data: dict) -> LeaveApplication:
    evidence = data.get("sanction_reference", "").strip()
    if not evidence:
        raise ValidationError("Offline sanction reference evidence is required.")
    try:
        person = contracts.get_employees([int(data["user_id"])]).get(int(data["user_id"]))
    except IamUnavailable as exc:
        raise ValidationError("IAM employee directory is unavailable.") from exc
    if person is None:
        raise ValidationError("The employee is not active in IAM.")
    start, end = data["start_date"], data["end_date"]
    if end < start:
        raise ValidationError("End date must not precede start date.")
    leave_type = data["leave_type"]
    if leave_type not in {"CL", "RH", "SCL", "EL", "COL", "VL"}:
        raise ValidationError("Unknown leave category.")
    days = Decimal(str(data["requested_days"]))
    if days <= 0:
        raise ValidationError("Offline leave days must be positive.")
    application = LeaveApplication.objects.create(
        applicant_user_id=person.user_id,
        request_kind="new",
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        requested_days=days,
        purpose=data.get("purpose", "Offline sanctioned leave"),
        medical_evidence_reference=evidence,
        organizational_unit=person.organizational_unit,
        status="approved",
        submitted_at=None,
    )
    accounts.ensure_annual_credit(
        user_id=person.user_id, leave_type=leave_type, year=start.year, employee_kind=person.kind
    )
    accounts.post(
        user_id=person.user_id,
        leave_type=leave_type,
        year=start.year,
        amount=-days,
        transaction_type="offline_sanction_sync",
        source_key=f"offline:{application.pk}",
        application=application,
        actor_user_id=actor_user_id,
        note=evidence,
    )
    from modules.leave.models import LeaveDecision

    LeaveDecision.objects.create(
        application=application,
        event="offline_recorded",
        from_status="offline_sanctioned",
        to_status="approved",
        actor_user_id=actor_user_id,
        actor_kind="leave_administrator",
        note=evidence,
    )
    return application


@transaction.atomic
def correct_record(*, actor_user_id: int, data: dict):
    user_id = int(data["user_id"])
    leave_type = data["leave_type"]
    amount = Decimal(str(data["amount"]))
    reason = data["reason"].strip()
    if not reason:
        raise ValidationError("A correction reason is required.")
    transaction_row = accounts.post(
        user_id=user_id,
        leave_type=leave_type,
        year=int(data.get("year", date.today().year)),
        amount=amount,
        transaction_type="administrative_adjustment",
        source_key=data.get("source_key") or f"correction:{uuid4().hex}",
        actor_user_id=actor_user_id,
        note=reason,
    )
    return LeaveRecordCorrection.objects.create(
        application_id=data.get("application_id"),
        user_id=user_id,
        leave_type=leave_type,
        amount=amount,
        reason=reason,
        actor_user_id=actor_user_id,
        transaction=transaction_row,
    )
