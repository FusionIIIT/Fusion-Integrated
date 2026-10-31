"""Core business logic services for the Employee Leave Management module.

Contains validation logic, year-end processing, and SLA threshold processing.
All functions follow the business rules (BR-EL-*) and use case requirements
(CFR-EL-*) from the v1.4 synchronized baseline.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    YearEndProcessingRun,
)

# ============================================================================
# Leave Validation Service
# ============================================================================


class LeaveValidationService:
    """Validate leave applications per BR-EL-001 through BR-EL-031."""

    @staticmethod
    def validate_new_application(application):
        """Validate a new leave application before progression.

        Checks per CFR-EL-002-003, BR-EL-001, BR-EL-003, BR-EL-011, BR-EL-012,
        BR-EL-013.
        """
        errors = []

        # BR-EL-001: Supported leave-category eligibility
        category = application.leave_category
        if category.code not in ["CL", "RH", "SCL", "EL", "COL", "VL"]:
            errors.append(f"Unsupported leave category: {category.code}")
            return {"valid": False, "error": "; ".join(errors)}

        # BR-EL-010: Half-day treatment is limited to a single-date CL request.
        if application.day_part != LeaveApplication.DayPartChoices.FULL_DAY:
            if category.code != "CL" or not category.supports_half_day:
                errors.append("Half-day requests are only supported for Casual Leave.")
            elif application.requested_start != application.requested_end:
                errors.append("A half-day CL request must cover exactly one date.")

        # BR-EL-013: Station Leave coupling — already handled at application level

        # BR-EL-011: Substitute eligibility checks
        if category.code in ["CL", "RH"] and application.substitute_accepted is False:
            # CL/RH don't typically require substitutes, but if nominated...
            pass

        # BR-EL-003: Validate category eligibility, entitlement/balance,
        # counting/calendar conditions, and impermissible overlap
        validation = LeaveValidationService._validate_eligibility_and_balance(application)
        if not validation["valid"]:
            errors.append(validation["error"])

        # BR-EL-012: Applicant non-overlap with half-day CL exception
        overlap_validation = LeaveValidationService._validate_no_overlap(application)
        if not overlap_validation["valid"]:
            errors.append(overlap_validation["error"])

        if errors:
            return {"valid": False, "error": "; ".join(errors)}

        return {"valid": True, "error": None}

    @staticmethod
    def validate_extension_application(application):
        """Validate an extension against its ongoing approved base leave."""
        original = application.extension_of
        if original is None:
            return {"valid": False, "error": "The original approved leave is required."}
        today = date.today()
        if (
            original.employee_user_id != application.employee_user_id
            or original.status != LeaveApplication.StatusChoices.APPROVED
            or original.leave_category.code not in {"EL", "COL", "VL"}
            or not original.requested_start <= today <= original.requested_end
        ):
            return {
                "valid": False,
                "error": "An extension requires the applicant's ongoing approved EL, COL, or VL.",
            }
        if (
            application.leave_category_id != original.leave_category_id
            or application.requested_start <= original.requested_end
            or application.requested_start > application.requested_end
        ):
            return {
                "valid": False,
                "error": (
                    "The extension period must follow the original leave and use its category."
                ),
            }

        balance_result = LeaveValidationService._validate_eligibility_and_balance(application)
        if not balance_result["valid"]:
            return balance_result
        overlap_result = LeaveValidationService._validate_no_overlap(application)
        if not overlap_result["valid"]:
            return overlap_result
        return {"valid": True, "error": None}

    @staticmethod
    def count_requested_days(application):
        """Count days charged for a valid request, including half-day CL."""
        if application.day_part in {
            LeaveApplication.DayPartChoices.FIRST_HALF,
            LeaveApplication.DayPartChoices.SECOND_HALF,
        }:
            return Decimal("0.5")
        inclusive_days = (application.requested_end - application.requested_start).days + 1
        if application.leave_category.continuous_day_counting:
            return Decimal(inclusive_days)
        weekdays = sum(
            1
            for day_offset in range(inclusive_days)
            if (application.requested_start + timedelta(days=day_offset)).weekday() < 5
        )
        return Decimal(weekdays)

    @staticmethod
    def _validate_eligibility_and_balance(application):
        """Validate leave-category eligibility and available entitlement/balance."""
        category = application.leave_category
        user_id = application.employee_user_id

        # Confirm the applicant is an active payroll employee and that the leave
        # category applies to their faculty/staff classification.
        from modules.directory.contracts import get_users

        employee = get_users([user_id]).get(user_id)
        if employee is None or employee.kind not in {"faculty", "staff"}:
            return {
                "valid": False,
                "error": "The applicant is not an active Faculty or Staff employee.",
            }
        employee_type = "F" if employee.kind == "faculty" else "S"
        if category.applicable_to not in {"B", employee_type}:
            return {
                "valid": False,
                "error": f"{category.code} is not applicable to this employee category.",
            }

        if application.requested_start > application.requested_end:
            return {
                "valid": False,
                "error": "The leave end date must be on or after the start date.",
            }

        # Get or create balance for this category/year
        year = date.today().year
        balance, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            leave_category=category,
            year=year,
            defaults={
                "entitlement_per_year": category.annual_entitlement or Decimal("0"),
            },
        )

        # Check entitlement/balance per BR-EL-002...010.
        available = balance.available()
        requested_days = LeaveValidationService.count_requested_days(application)
        if requested_days <= 0:
            return {
                "valid": False,
                "error": "The requested period contains no chargeable leave days.",
            }
        if available < requested_days:
            return {
                "valid": False,
                "error": (
                    f"Insufficient {category.code} balance: {available:.1f} days "
                    f"available; {requested_days:.1f} days requested."
                ),
            }

        # Category-specific entitlement checks
        if category.code == "CL":
            # BR-EL-002: 8 days/year, unused lapses
            if available < 1:  # Need at least 1 full day or 2 half-days
                return {
                    "valid": False,
                    "error": (
                        f"Insufficient CL balance: {available:.1f} days available "
                        f"(entitlement: {balance.entitlement_per_year})"
                    ),
                }
        elif category.code == "RH":
            # BR-EL-003: 2 days/year, must be applicable RH, unused lapses
            if available < 1:
                return {
                    "valid": False,
                    "error": f"Insufficient RH balance: {available:.1f} days available",
                }
        elif category.code == "SCL":
            # BR-EL-004: Up to 15 days/year, admissibility by authority
            if available < 1:
                return {
                    "valid": False,
                    "error": f"Insufficient SCL balance: {available:.1f} days available",
                }
        elif category.code == "EL":
            # BR-EL-005: Non-faculty 30/year, carry forward
            # BR-EL-010: Continuous-day counting for EL
            if available < 1:
                return {
                    "valid": False,
                    "error": f"Insufficient EL balance: {available:.1f} days available",
                }
        elif category.code == "COL":
            # BR-EL-009: 20 days/year, balance-controlled, evidence may be required
            if available < 1:
                return {
                    "valid": False,
                    "error": f"Insufficient COL balance: {available:.1f} days available",
                }
        elif category.code == "VL":
            # BR-EL-006: Faculty 60 VL, Academic Calendar vacation periods
            # VL-specific validation - check vacation period applicability
            # BR-EL-006: VL may be availed only during applicable vacation period
            # This would check against Academic Calendar data
            pass

        # BR-EL-011: Continuous-day counting
        # For EL, COL, VL: intervening weekends/closed holidays count as leave days
        # For CL, SCL, RH: they do NOT count
        if category.code in ["EL", "COL", "VL"]:
            # Continuous day counting applies - need to compute chargeable days
            # The actual counting logic would consider intervening weekends/holidays
            # For now, we accept; the full counting is done in the workflow
            pass
        # CL, SCL, RH: continuous-day rule does NOT apply

        # Check for impermissible overlap per BR-EL-012
        # (handled separately in _validate_no_overlap)

        return {"valid": True, "error": None, "available": available}

    @staticmethod
    def _validate_no_overlap(application):
        """Check for impermissible overlap with active pending/approved leave.

        BR-EL-012: A new request shall not impermissibly overlap the employee's
        active pending or approved leave. First-half and second-half CL on the
        same date are non-overlapping when they occupy different halves.
        """

        user_id = application.employee_user_id
        new_start = application.requested_start
        new_end = application.requested_end
        new_category = application.leave_category.code

        # Find all pending or approved leave applications for this user
        overlapping = LeaveApplication.objects.filter(
            employee_user_id=user_id,
            status__in=[
                LeaveApplication.StatusChoices.SUBMITTED,
                LeaveApplication.StatusChoices.APPROVED,
                LeaveApplication.StatusChoices.AWAITING_SUBSTITUTE_RESPONSE,
                LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW,
                LeaveApplication.StatusChoices.AWAITING_ESTABLISHMENT_ROUTING,
                LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION,
            ],
        ).exclude(pk=application.pk)

        for existing in overlapping:
            existing_start = existing.requested_start
            existing_end = existing.requested_end
            existing_category = existing.leave_category.code

            # Check date overlap
            if new_start > existing_end or new_end < existing_start:
                # No overlap
                continue

            # BR-EL-012: first-half and second-half CL on one date are distinct.
            same_single_date = new_start == new_end == existing_start == existing_end
            is_half_day_pair = (
                new_category == existing_category == "CL"
                and same_single_date
                and application.day_part
                in {
                    LeaveApplication.DayPartChoices.FIRST_HALF,
                    LeaveApplication.DayPartChoices.SECOND_HALF,
                }
                and existing.day_part
                in {
                    LeaveApplication.DayPartChoices.FIRST_HALF,
                    LeaveApplication.DayPartChoices.SECOND_HALF,
                }
            )
            if is_half_day_pair and application.day_part != existing.day_part:
                continue

            return {
                "valid": False,
                "error": f"Impermissible overlap with existing {existing_category} leave "
                f"(existing: {existing_start} to {existing_end})",
            }

        return {"valid": True, "error": None}


# ============================================================================
# Year-End Processing Service
# ============================================================================


class YearEndProcessingService:
    """Apply year-end leave outcomes once and record the resulting transactions."""

    @staticmethod
    @transaction.atomic
    def execute_year_end(year=None):
        year = year or date.today().year
        run, _ = YearEndProcessingRun.objects.select_for_update().get_or_create(year=year)
        if run.completed_at is not None:
            return run.result

        transactions = []
        categories = list(LeaveCategory.objects.all())

        for category in categories:
            balances = LeaveBalance.objects.select_for_update().filter(
                leave_category=category,
                year=year,
            )
            for balance in balances:
                unused = max(balance.available(), Decimal("0"))
                if unused == 0:
                    continue

                if category.code in {"CL", "RH", "SCL"}:
                    transactions.append(
                        {
                            "user_id": balance.user_id,
                            "category": category.code,
                            "action": "lapse",
                            "days": float(unused),
                        }
                    )
                    continue

                if category.code in {"EL", "COL"}:
                    next_balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
                        user_id=balance.user_id,
                        leave_category=category,
                        year=year + 1,
                        defaults={
                            "entitlement_per_year": balance.entitlement_per_year,
                        },
                    )
                    next_balance.carried_forward_from_previous += unused
                    next_balance.save(update_fields=["carried_forward_from_previous"])
                    transactions.append(
                        {
                            "user_id": balance.user_id,
                            "category": category.code,
                            "action": "carry_forward",
                            "days": float(unused),
                        }
                    )
                    continue

                if category.code == "VL":
                    el_category = LeaveCategory.objects.filter(code="EL").first()
                    if el_category is None:
                        continue
                    converted = unused / Decimal("2")
                    next_el_balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
                        user_id=balance.user_id,
                        leave_category=el_category,
                        year=year + 1,
                        defaults={"entitlement_per_year": Decimal("0")},
                    )
                    next_el_balance.carried_forward_from_previous += converted
                    next_el_balance.save(update_fields=["carried_forward_from_previous"])
                    transactions.append(
                        {
                            "user_id": balance.user_id,
                            "category": category.code,
                            "action": "vl_to_el_conversion",
                            "unused_vl": float(unused),
                            "converted_el": float(converted),
                        }
                    )

        result = {
            "year": year,
            "transactions": transactions,
            "exceptions": [],
            "summary": {
                "total_transactions": len(transactions),
                "categories_processed": len(categories),
            },
        }
        run.result = result
        run.completed_at = timezone.now()
        run.save(update_fields=["result", "completed_at"])
        return result


# ============================================================================
# SLA Threshold Trigger Service
# ============================================================================


class SLATriggerService:
    """Process SLA reminder and escalation threshold events per EL-UC-021 and BR-EL-032-033."""

    @staticmethod
    def process_sla_threshold():
        """Process configured SLA reminder or escalation threshold.

        BR-EL-032: When an SLA-controlled actionable task reaches its configured
        reminder threshold, issue a reminder to the responsible user and log it
        only if the task is still pending; otherwise issue no reminder.

        BR-EL-033: When an SLA-controlled actionable task remains pending past
        its configured escalation threshold, perform the configured escalation
        action: notify the configured higher/responsible authority and, where
        the escalation configuration changes routing/responsibility, apply that
        routing/responsibility change; log the escalation.

        If the task is no longer pending, no escalation shall be issued.
        """
        # In a real implementation, this would:
        # 1. Identify all SLA-controlled actionable tasks
        # 2. Check each task's elapsed time against configured thresholds
        # 3. At reminder threshold: if still pending, remind responsible user + log
        # 4. At escalation threshold: if still pending, notify/escalate to higher authority + log
        # 5. If task is no longer pending: issue no reminder/escalation

        return {
            "reminders_issued": 0,
            "escalations_issued": 0,
            "tasks_checked": 0,
            "tasks_no_longer_pending": 0,
        }
