"""Workflow review services for substitute, unit head, establishment, and sanctioning."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.errors import InvalidStateTransitionError, InvalidSubstituteError
from modules.elm.domain.state_machine import (
    transition_establishment_routing,
    transition_final_sanction,
    transition_replacement_substitute,
    transition_substitute_response,
    transition_unit_head_review,
)
from modules.elm.domain.validation import validate_substitute
from modules.elm.models import LeaveApplication
from modules.elm.selectors.applications import get_active_leaves_for_user
from modules.elm.selectors.balances import get_closed_holiday_dates

from .balances import deduct_balance, restore_balance


@transaction.atomic
def respond_as_substitute(
    application_id: int,
    substitute_id: int,
    decision: str,  # 'accepted' or 'declined'
    remarks: str = "",
    is_director: bool = False,
) -> LeaveApplication:
    """Substitute response (EL-UC-002, BR-EL-015)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.substitute_id != substitute_id:
        raise InvalidSubstituteError("User is not the nominated substitute for this application.")

    accepted = decision == "accepted"
    new_state = transition_substitute_response(
        current_state=app.status,
        accepted=accepted,
        is_director=is_director,
    )

    app.substitute_status = "accepted" if accepted else "declined"
    app.substitute_remarks = remarks
    app.status = new_state
    app.save(update_fields=["substitute_status", "substitute_remarks", "status", "updated_at"])
    return app


@transaction.atomic
def nominate_replacement_substitute(
    application_id: int,
    user_id: int,
    new_substitute_id: int,
) -> LeaveApplication:
    """Nominate replacement substitute after decline (EL-UC-019, BR-EL-015)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id, user_id=user_id)

    # Validate eligibility of new substitute
    sub_leaves = get_active_leaves_for_user(user_id=new_substitute_id)
    validate_substitute(
        applicant_id=user_id,
        substitute_id=new_substitute_id,
        start_date=app.start_date,
        end_date=app.end_date,
        substitute_leaves=sub_leaves,
    )

    new_state = transition_replacement_substitute(app.status)
    app.substitute_id = new_substitute_id
    app.substitute_status = "pending"
    app.substitute_remarks = ""
    app.status = new_state
    app.save(
        update_fields=[
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "status",
            "updated_at",
        ]
    )
    return app


@transaction.atomic
def review_at_unit_head(
    application_id: int,
    unit_head_id: int,
    action: str,  # 'approve', 'reject', 'recommend', 'not_recommend'
    remarks: str = "",
    establishment_configured: bool = False,
) -> LeaveApplication:
    """Unit Head review action (EL-UC-003, BR-EL-016, BR-EL-017)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    new_state = transition_unit_head_review(
        current_state=app.status,
        category=app.leave_category,
        action=action,
        establishment_configured=establishment_configured,
    )

    app.unit_head_id = unit_head_id
    app.unit_head_remarks = remarks
    app.unit_head_acted_at = timezone.now()

    if action in ("recommend", "not_recommend"):
        app.unit_head_recommendation = "recommended" if action == "recommend" else "not_recommended"

    # If Unit Head approved CL/RH directly (BR-EL-016), deduct balance
    if new_state == "approved" and app.status == "awaiting_unit_head":
        deduct_balance(
            user_id=app.user_id,
            category=app.leave_category,
            days=app.chargeable_days,
            year=app.start_date.year,
        )

    # If Unit Head approved CL/RH cancellation (BR-EL-023), restore balance
    if new_state == "cancelled" and app.status == "cancellation_pending_unit_head":
        restore_balance(
            user_id=app.user_id,
            category=app.leave_category,
            days=app.chargeable_days,
            year=app.start_date.year,
        )

    app.status = new_state
    app.save()
    return app


@transaction.atomic
def route_at_establishment(
    application_id: int,
    reviewer_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Establishment verification and routing (EL-UC-004, BR-EL-019)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    new_state = transition_establishment_routing(app.status)
    app.status = new_state
    app.save(update_fields=["status", "updated_at"])
    return app


@transaction.atomic
def sanction_final_decision(
    application_id: int,
    sanctioner_id: int,
    role: str,
    action: str,  # 'approve' or 'reject'
    remarks: str = "",
) -> LeaveApplication:
    """Final sanction decision (EL-UC-005, BR-EL-018, BR-EL-020)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    old_state = app.status
    new_state = transition_final_sanction(current_state=old_state, action=action)

    app.sanctioning_authority_id = sanctioner_id
    app.sanction_role = role
    app.sanction_decision = action
    app.sanction_remarks = remarks
    app.sanction_acted_at = timezone.now()

    # Balance effects:
    # 1. New leave approved -> deduct balance
    if new_state == "approved" and old_state in (
        "awaiting_final_sanction",
        "awaiting_director_self_sanction",
    ):
        deduct_balance(
            user_id=app.user_id,
            category=app.leave_category,
            days=app.chargeable_days,
            year=app.start_date.year,
        )

    # 2. Approved cancellation approved -> restore balance (BR-EL-023)
    if new_state == "cancelled" and old_state == "cancellation_pending_final":
        restore_balance(
            user_id=app.user_id,
            category=app.leave_category,
            days=app.chargeable_days,
            year=app.start_date.year,
        )

    # 3. Extension approved -> deduct incremental days (BR-EL-025)
    if new_state == "approved" and old_state == "ext_pending_final":
        deduct_balance(
            user_id=app.user_id,
            category=app.leave_category,
            days=app.chargeable_days,
            year=app.start_date.year,
        )

    app.status = new_state
    app.save()
    return app


@transaction.atomic
def review_resumption(
    application_id: int,
    reviewer_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Sanctioning Authority review of duty resumption (EL-UC-011, BR-EL-028)."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.status != "resumption_review_pending":
        raise InvalidStateTransitionError("Application is not pending resumption review.")

    actual_date = app.resumption_date
    if not actual_date:
        raise InvalidStateTransitionError("No resumption date specified on application.")

    approved_end = app.end_date
    closed_holidays = get_closed_holiday_dates(year=approved_end.year)

    if actual_date == approved_end:
        # Normal return: no adjustment to leave or balance (BR-EL-028)
        app.resumption_status = "normal"
    elif actual_date < approved_end:
        # Early return: restore balance for unused days (BR-EL-028)
        app.resumption_status = "early"
        unused_start = actual_date + datetime.timedelta(days=1)
        if unused_start <= approved_end:
            unused_days = calculate_chargeable_days(
                category=app.leave_category,
                start_date=unused_start,
                end_date=approved_end,
                closed_holidays=closed_holidays,
            )
            restore_balance(
                user_id=app.user_id,
                category=app.leave_category,
                days=unused_days,
                year=approved_end.year,
            )
    else:
        # Late return: deduct balance for extra days (BR-EL-028)
        app.resumption_status = "late"
        extra_start = approved_end + datetime.timedelta(days=1)
        extra_days = calculate_chargeable_days(
            category=app.leave_category,
            start_date=extra_start,
            end_date=actual_date,
            closed_holidays=closed_holidays,
        )
        deduct_balance(
            user_id=app.user_id,
            category=app.leave_category,
            days=extra_days,
            year=approved_end.year,
        )

    app.status = "resumption_reviewed"
    app.save(update_fields=["resumption_status", "status", "updated_at"])
    return app
