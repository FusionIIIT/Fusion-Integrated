
"""Transactional and authorized decisions for employee leave applications."""

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain.leave_rules import (
    LeaveRuleError,
    validate_sufficient_balance,
)
from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationStatus,
    LeaveBalance,
    LeaveType,
)
from modules.elm.services.leave_application import (
    _calendar_year_day_counts,
    validate_leave_application,
)


@transaction.atomic
def decide_leave_application(
    *,
    actor,
    application_id: int,
    decision: str,
) -> LeaveApplication:
    """Approve or reject a pending request as its assigned final authority."""

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id)
        .first()
    )

    if application is None:
        raise LeaveRuleError("Leave application does not exist.")

    # This literal permission check is also visible to the
    # Fusion permission-manifest validator.
    if actor is None:
        raise PermissionDeniedError(
            "Authentication required.",
            code="not_authenticated",
        )

    check = getattr(actor, "has_permission", None)
    if not callable(check) or not check(
        "elm.leave_application.decide"
    ):
        raise PermissionDeniedError(
            "You do not have permission to decide leave applications.",
            code="permission_denied",
        )

    # The authority must be assigned to this particular application.
    if (
        application.assigned_final_authority_user_id is None
        or getattr(actor, "user_id", None)
        != application.assigned_final_authority_user_id
    ):
        raise PermissionDeniedError(
            "You are not the assigned final authority for this request.",
            code="permission_denied",
        )

    if decision not in {
        LeaveApplicationStatus.APPROVED,
        LeaveApplicationStatus.REJECTED,
    }:
        raise LeaveRuleError("Decision must be approved or rejected.")

    if application.status != LeaveApplicationStatus.PENDING:
        raise LeaveRuleError(
            "Only pending leave applications can be decided."
        )

    if application.leave_type in {LeaveType.CL, LeaveType.RH}:
        allowed_stages = {"awaiting_unit_head_review"}

    elif application.workflow_stage == "awaiting_director_self_sanction":
        allowed_stages = {"awaiting_director_self_sanction"}

    else:
        allowed_stages = {"awaiting_final_sanction"}

    if application.workflow_stage not in allowed_stages:
        raise LeaveRuleError(
            "This application has not completed the required "
            "review and processing stages."
        )

    if decision == LeaveApplicationStatus.APPROVED:
        crosses_years = (
            application.start_date.year != application.end_date.year
        )

        if crosses_years and application.leave_type not in {
            LeaveType.EL,
            LeaveType.COL,
            LeaveType.VL,
        }:
            raise LeaveRuleError(
                "Cross-year approval for this leave type requires "
                "a verified year-by-year leave-day allocation."
            )

        validate_leave_application(
            user_id=application.user_id,
            leave_type=application.leave_type,
            start_date=application.start_date,
            end_date=application.end_date,
            requested_days=application.requested_days,
            half_day=application.half_day,
            exclude_application_id=application.pk,
        )

        years = range(
            application.start_date.year,
            application.end_date.year + 1,
        )

        balances = list(
            LeaveBalance.objects.select_for_update()
            .filter(
                user_id=application.user_id,
                leave_type=application.leave_type,
                leave_year__in=years,
            )
            .order_by("leave_year")
        )

        balances_by_year = {
            balance.leave_year: balance for balance in balances
        }

        if crosses_years:
            days_by_year = _calendar_year_day_counts(
                application.start_date,
                application.end_date,
            )

            if sum(days_by_year.values()) != application.requested_days:
                raise LeaveRuleError(
                    "Cross-year requested days do not match "
                    "the inclusive calendar-day count."
                )

            # Validate all years before deducting any balance.
            for year, year_days in days_by_year.items():
                balance = balances_by_year.get(year)

                if balance is None:
                    raise LeaveRuleError(
                        f"No {application.leave_type} balance exists "
                        f"for year {year}."
                    )

                validate_sufficient_balance(
                    balance.available_balance,
                    year_days,
                )

            for year, year_days in days_by_year.items():
                balance = balances_by_year[year]
                balance.available_balance -= Decimal(str(year_days))
                balance.save(
                    update_fields=["available_balance", "updated_at"]
                )

        else:
            year = application.start_date.year
            balance = balances_by_year.get(year)

            if balance is None:
                raise LeaveRuleError(
                    "No balance exists for this leave type and year."
                )

            validate_sufficient_balance(
                balance.available_balance,
                application.requested_days,
            )

            balance.available_balance -= application.requested_days
            balance.save(
                update_fields=["available_balance", "updated_at"]
            )

    application.status = decision
    application.save(update_fields=["status", "updated_at"])

    return application
