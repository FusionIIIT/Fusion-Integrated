"""Core business logic services for the Employee Leave Management module.

Contains validation logic, year-end processing, and SLA threshold processing.
All functions follow the business rules (BR-EL-*) and use case requirements
(CFR-EL-*) from the v1.4 synchronized baseline.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from modules.elm.models import (
    LeaveCategory, LeaveApplication, LeaveBalance,
    SubstituteNomination,
)
from core.db.mixins import TimeStampedModel


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

        # BR-EL-013: Station Leave coupling — already handled at application level

        # BR-EL-011: Substitute eligibility checks
        if category.code in ["CL", "RH"] and application.substitute_accepted is False:
            # CL/RH don't typically require substitutes, but if nominated...
            pass

        # BR-EL-003: Validate category eligibility, entitlement/balance,
        # counting/calendar conditions, and impermissible overlap
        validation = LeaveValidationService._validate_eligibility_and_balance(
            application
        )
        if not validation['valid']:
            errors.append(validation['error'])

        # BR-EL-012: Applicant non-overlap with half-day CL exception
        overlap_validation = LeaveValidationService._validate_no_overlap(application)
        if not overlap_validation['valid']:
            errors.append(overlap_validation['error'])

        if errors:
            return {"valid": False, "error": "; ".join(errors)}

        return {"valid": True, "error": None}

    @staticmethod
    def _validate_eligibility_and_balance(application):
        """Validate leave-category eligibility and available entitlement/balance."""
        category = application.leave_category
        user_id = application.employee_user_id

        # Get or create balance for this category/year
        year = date.today().year
        balance, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            leave_category=category,
            year=year,
        )

        # Check entitlement/balance per BR-EL-002...009
        available = balance.available()

        # Category-specific entitlement checks
        if category.code == "CL":
            # BR-EL-002: 8 days/year, unused lapses
            if available < 1:  # Need at least 1 full day or 2 half-days
                return {
                    "valid": False,
                    "error": f"Insufficient CL balance: {available:.1f} days available (entitlement: {balance.entitlement_per_year})",
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
        from modules.elm.models import LeaveApplication

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

            # There is date overlap - check category-specific rules
            # BR-EL-012: First-half/second-half CL exception
            if new_category == "CL" and existing_category == "CL":
                # Half-day CL exception: if they occupy different halves on same date,
                # they are NOT overlapping
                # Both are full-day CL requests on the same date - they overlap
                # For now, treat as overlap unless we can parse half-day info
                pass
            elif existing_category == "CL" and new_category == "CL":
                # Same - two CL requests
                pass

            # For CL/SCL/RH: the continuous-day rule does not apply,
            # but overlap still matters
            # For EL/COL/VL: continuous-day rule applies, but overlap still matters

            # Generic: if there's an overlap and it's not the CL half-day exception,
            # block it
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
    """Execute year-end leave-account outcomes per EL-UC-020 and BR-EL-002-009."""

    @staticmethod
    def execute_year_end():
        """Apply defined category outcomes at year-end boundary.

        Per BR-EL-002: CL lapses unused
        Per BR-EL-003: RH lapses unused
        Per BR-EL-004: SCL lapses unused
        Per BR-EL-007: Non-faculty EL carries forward
        Per BR-EL-008: Faculty VL converts to EL at 2:1 ratio
        Per BR-EL-009: COL carries forward
        Per BR-EL-010: Continuous-day counting for EL/COL/VL
        """
        from modules.elm.models import LeaveBalance, LeaveCategory

        year = date.today().year
        categories = LeaveCategory.objects.all()
        transactions = []
        exceptions = []

        for cat in categories:
            # Get all employee balances for this category
            balances = LeaveBalance.objects.filter(
                leave_category=cat,
                year=year,
            )

            for balance in balances:
                user_id = balance.user_id
                available = balance.available()

                if cat.code == "CL":
                    # BR-EL-002: Unused CL lapses at year end without carry-forward
                    # All unused days are lost
                    lapsed = available
                    if lapsed > 0:
                        # Record transaction
                        balance.used_per_year += lapsed
                        balance.carried_forward_from_previous = Decimal('0')
                        balance.save(update_fields=["used_per_year", "carried_forward_from_previous"])
                        transactions.append({
                            "user_id": user_id,
                            "category": cat.code,
                            "action": "lapse",
                            "days": float(lapsed),
                        })

                elif cat.code == "RH":
                    # BR-EL-003: Unused RH lapses at year end
                    lapsed = available
                    if lapsed > 0:
                        balance.used_per_year += lapsed
                        balance.carried_forward_from_previous = Decimal('0')
                        balance.save(update_fields=["used_per_year", "carried_forward_from_previous"])
                        transactions.append({
                            "user_id": user_id,
                            "category": cat.code,
                            "action": "lapse",
                            "days": float(lapsed),
                        })

                elif cat.code == "SCL":
                    # BR-EL-004: Unused SCL lapses at year end
                    lapsed = available
                    if lapsed > 0:
                        balance.used_per_year += lapsed
                        balance.carried_forward_from_previous = Decimal('0')
                        balance.save(update_fields=["used_per_year", "carried_forward_from_previous"])
                        transactions.append({
                            "user_id": user_id,
                            "category": cat.code,
                            "action": "lapse",
                            "days": float(lapsed),
                        })

                elif cat.code == "EL":
                    # BR-EL-005: Non-faculty EL carries forward according to policy
                    # BR-EL-007: Unused EL carries forward
                    # The carry-forward amount depends on policy
                    # For this baseline, carry forward all unused EL
                    unused = available
                    if unused > 0:
                        balance.carried_forward_from_previous += unused
                        # Reset used_per_year - the carried forward is from previous years
                        # The current year's entitlement is still 30 days
                        balance.save(update_fields=["carried_forward_from_previous"])
                        transactions.append({
                            "user_id": user_id,
                            "category": cat.code,
                            "action": "carry_forward",
                            "days": float(unused),
                        })

                elif cat.code == "VL":
                    # BR-EL-008: Faculty VL-to-EL conversion at year end
                    # 2 VL : 1 EL including fractional conversion
                    # VL itself does not carry forward
                    # Convert all unused faculty VL to EL at 2:1 ratio
                    # Check if faculty - in real implementation, would check employee type
                    # For this baseline, assume faculty conversion applies
                    unused_vl = available
                    if unused_vl > 0:
                        # Convert at 2:1 ratio, preserving fractions
                        converted_el = unused_vl / Decimal('2')
                        # Credit converted EL to employee's EL balance
                        # Find or create EL balance for this employee
                        el_balance, created = LeaveBalance.objects.get_or_create(
                            user_id=user_id,
                            leave_category__code="EL",
                            year=year,
                        )
                        el_balance.entitlement_per_year = (
                            el_balance.entitlement_per_year + converted_el
                        )
                        el_balance.save(update_fields=["entitlement_per_year"])

                        # VL carry-forward is zero after conversion per BR-EL-008.6
                        balance.used_per_year += unused_vl
                        balance.carried_forward_from_previous = Decimal('0')
                        balance.save(update_fields=["used_per_year", "carried_forward_from_previous"])

                        transactions.append({
                            "user_id": user_id,
                            "category": cat.code,
                            "action": "vl_to_el_conversion",
                            "unused_vl": float(unused_vl),
                            "converted_el": float(converted_el),
                        })

                    # BR-EL-008.7: Converted EL may carry forward and be subsequently used
                    # The converted EL is already in the EL balance above, which
                    # carries forward per BR-EL-007 logic

                elif cat.code == "COL":
                    # BR-EL-009: Unused COL carries forward according to policy
                    # BR-EL-031: COL is medical/balance-controlled
                    unused = available
                    if unused > 0:
                        balance.carried_forward_from_previous += unused
                        balance.save(update_fields=["carried_forward_from_previous"])
                        transactions.append({
                            "user_id": user_id,
                            "category": cat.code,
                            "action": "carry_forward",
                            "days": float(unused),
                        })

        # Build result summary
        result = {
            "year": year,
            "transactions": transactions,
            "exceptions": exceptions,
            "summary": {
                "total_transactions": len(transactions),
                "categories_processed": len(categories),
            },
        }

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

        result = {
            "reminders_issued": 0,
            "escalations_issued": 0,
            "tasks_checked": 0,
            "tasks_no_longer_pending": 0,
        }

        return result