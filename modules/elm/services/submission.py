"""Database-backed validation and submission for ELM leave applications."""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.models import UserRef
from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveCalendarDay,
    LeavePolicy,
    LeaveTransition,
)
from modules.elm.services.validation import (
    ACTIVE_OVERLAP_STATUSES,
    calculate_leave_days,
    cl_halves_are_compatible,
    date_intervals_overlap,
)


def _calendar_days(leave_code, start_date, end_date):
    """Return the relevant published calendar records for the interval."""
    return LeaveCalendarDay.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
        published=True,
    ).filter(
        effective_from__isnull=True
    ) | LeaveCalendarDay.objects.filter(
        date__gte=start_date,
        date__lte=end_date,
        published=True,
        effective_from__lte=end_date,
    ).filter(
        effective_to__isnull=True
    )


def _count_requested_days(leave_code, start_date, end_date, half_day):
    """Count requested days using continuous or working-day rules."""
    if leave_code in {"EL", "COL", "VL"}:
        return calculate_leave_days(
            leave_code, start_date, end_date, half_day
        )

    if half_day != "full":
        return calculate_leave_days(
            leave_code, start_date, end_date, half_day
        )

    calendar_rows = list(
        LeaveCalendarDay.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            published=True,
        ).filter(
            effective_from__isnull=True
        ) | LeaveCalendarDay.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            published=True,
            effective_from__lte=start_date,
        ).filter(
            effective_to__isnull=True
        )
    )
    closed_dates = {
        row.date for row in calendar_rows
        if row.kind in {"holiday", "closed"}
    }
    count = Decimal("0")
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in closed_dates:
            count += Decimal("1")
        current = date.fromordinal(current.toordinal() + 1)
    return count


@transaction.atomic
def submit_leave(application: LeaveApplication, actor):
    """Validate and persist a new leave application atomically.

    The caller must set applicant_user_id from the authenticated identity,
    not from untrusted request data.
    """
    actor_user_id = getattr(actor, "user_id", None)
    has_permission = getattr(actor, "has_permission", None)

    if (
        actor_user_id is None
        or not callable(has_permission)
        or not has_permission("elm.leave.apply")
    ):
        raise PermissionDeniedError(
            "You do not have permission to apply for leave.",
            code="permission_denied",
        )
    if application.pk:
        raise ValidationError("Only a new, unsaved application can be submitted.")

    if application.applicant_user_id != actor_user_id:
        raise ValidationError("You may submit leave only for your own account.")

    if not application.purpose.strip():
        raise ValidationError("Purpose/reason is required.")

    if application.end_date < application.start_date:
        raise ValidationError("End date cannot precede start date.")

    employee = UserRef.objects.filter(
        user_id=actor_user_id, is_active=True,
        kind__in=["faculty", "staff"],
    ).first()
    if employee is None:
        raise ValidationError("An active faculty/staff directory record is required.")

    policy = LeavePolicy.objects.filter(
        code=application.leave_code, active=True
    ).first()
    if policy is None:
        raise ValidationError("This leave category has no active policy.")

    if policy.faculty_only and employee.kind != "faculty":
        raise ValidationError("This leave category is restricted to faculty.")
    if policy.staff_only and employee.kind != "staff":
        raise ValidationError("This leave category is restricted to staff.")

    requested_days = _count_requested_days(
        application.leave_code,
        application.start_date,
        application.end_date,
        application.half_day,
    )
    if requested_days <= 0:
        raise ValidationError("The requested period contains no countable leave days.")

    if application.leave_code == "RH":
        if application.start_date != application.end_date:
            raise ValidationError("An RH request must select one published RH date.")
        if not LeaveCalendarDay.objects.filter(
            date=application.start_date,
            kind="restricted",
            published=True,
        ).exists():
            raise ValidationError("The selected date is not a published Restricted Holiday.")

    if application.leave_code == "VL":
        vacation_dates = set(
            LeaveCalendarDay.objects.filter(
                date__gte=application.start_date,
                date__lte=application.end_date,
                kind="vacation",
                published=True,
            ).values_list("date", flat=True)
        )
        expected_dates = {
            date.fromordinal(day)
            for day in range(
                application.start_date.toordinal(),
                application.end_date.toordinal() + 1,
            )
        }
        if not expected_dates.issubset(vacation_dates):
            raise ValidationError("VL must fall entirely within published vacation dates.")

    balance = LeaveBalance.objects.select_for_update().filter(
        user_id=actor_user_id,
        leave_code=application.leave_code,
        leave_year=application.start_date.year,
    ).first()
    if balance is None:
        raise ValidationError("No balance has been configured for this leave category and year.")

    if balance.available < requested_days:
        raise ValidationError("Insufficient available leave balance.")

    existing = LeaveApplication.objects.filter(
        applicant_user_id=actor_user_id,
        status__in=ACTIVE_OVERLAP_STATUSES,
        start_date__lte=application.end_date,
        end_date__gte=application.start_date,
    )
    for old in existing:
        if cl_halves_are_compatible(
            old.leave_code, old.start_date, old.end_date, old.half_day,
            application.leave_code, application.start_date,
            application.end_date, application.half_day,
        ):
            continue
        if date_intervals_overlap(
            old.start_date, old.end_date,
            application.start_date, application.end_date,
        ):
            raise ValidationError(
                f"Requested dates overlap active leave application #{old.pk}."
            )

    if application.station_leave_required and not application.station_leave_details.strip():
        raise ValidationError("Station Leave details are required when Station Leave applies.")

    if policy.requires_substitute:
        if not application.substitute_user_id:
            raise ValidationError("A substitute must be nominated for this application.")
        if application.substitute_user_id == actor_user_id:
            raise ValidationError("The applicant cannot be their own substitute.")

        substitute = UserRef.objects.filter(
            user_id=application.substitute_user_id,
            is_active=True,
            kind__in=["faculty", "staff"],
        ).first()
        if substitute is None:
            raise ValidationError("The nominated substitute is not an active employee.")

        responsibility_start = application.responsibility_start or application.start_date
        responsibility_end = application.responsibility_end or application.end_date
        if responsibility_end < responsibility_start:
            raise ValidationError("Invalid substitute responsibility period.")

        substitute_conflict = LeaveApplication.objects.filter(
            applicant_user_id=application.substitute_user_id,
            status__in=ACTIVE_OVERLAP_STATUSES,
            start_date__lte=responsibility_end,
            end_date__gte=responsibility_start,
        ).exists()
        if substitute_conflict:
            raise ValidationError("The nominated substitute has overlapping active leave.")

        application.status = "awaiting_substitute"
    else:
        application.status = "unit_head_review"

    application.submitted_at = timezone.now()
    application.save()

    LeaveTransition.objects.create(
        application=application,
        from_status="draft",
        to_status=application.status,
        actor_user_id=actor_user_id,
        action="submit",
        remarks="Application submitted",
        metadata={"requested_days": str(requested_days)},
    )
    return application


@transaction.atomic
def withdraw_leave(*, application_id: int, actor):
    """Withdraw an applicant's own pending leave application."""
    actor_user_id = getattr(actor, "user_id", None)
    has_permission = getattr(actor, "has_permission", None)

    if (
        actor_user_id is None
        or not callable(has_permission)
        or not has_permission("elm.leave.withdraw_self")
    ):
        raise PermissionDeniedError(
            "You do not have permission to withdraw leave.",
            code="permission_denied",
        )

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id, applicant_user_id=actor_user_id)
        .first()
    )
    if application is None:
        raise NotFoundError("No such leave application.")

    withdrawable_states = {
        "awaiting_substitute",
        "applicant_action",
        "unit_head_review",
        "establishment",
        "final_sanction",
    }
    if application.status not in withdrawable_states:
        raise ConflictError(
            "Only pending leave applications can be withdrawn.",
            code="leave_not_withdrawable",
        )

    previous_status = application.status
    application.status = "withdrawn"
    application.save()

    LeaveTransition.objects.create(
        application=application,
        from_status=previous_status,
        to_status="withdrawn",
        actor_user_id=actor_user_id,
        action="withdraw",
        remarks="Application withdrawn by applicant",
    )
    return application


@transaction.atomic
def respond_to_substitute(*, application_id: int, actor, response: str):
    """Accept or decline a request assigned to the authenticated substitute."""
    actor_user_id = getattr(actor, "user_id", None)
    has_permission = getattr(actor, "has_permission", None)

    if (
        actor_user_id is None
        or not callable(has_permission)
        or not has_permission("elm.leave.substitute_respond")
    ):
        raise PermissionDeniedError(
            "You do not have permission to respond to substitute requests.",
            code="permission_denied",
        )

    if response not in {"accept", "decline"}:
        raise BadRequestError(
            "Response must be either 'accept' or 'decline'.",
            code="invalid_substitute_response",
        )

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(
            pk=application_id,
            substitute_user_id=actor_user_id,
        )
        .first()
    )
    if application is None:
        raise NotFoundError("No such substitute request.")

    if application.status != "awaiting_substitute":
        raise ConflictError(
            "This application is no longer awaiting a substitute response.",
            code="substitute_response_not_allowed",
        )

    previous_status = application.status
    if response == "accept":
        application.status = "unit_head_review"
        action = "substitute_accept"
        remarks = "Nominated substitute accepted responsibility"
    else:
        application.status = "applicant_action"
        action = "substitute_decline"
        remarks = "Nominated substitute declined; applicant action required"

    application.save()

    LeaveTransition.objects.create(
        application=application,
        from_status=previous_status,
        to_status=application.status,
        actor_user_id=actor_user_id,
        action=action,
        remarks=remarks,
        metadata={"response": response},
    )
    return application
