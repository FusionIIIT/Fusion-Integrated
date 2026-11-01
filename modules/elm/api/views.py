"""ELM API views — HTTP endpoints for the Employee Leave Management module."""from __future__ import annotations

import datetime

from rest_framework import status
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.request import Request
from django.db.models import F, Q
from django.shortcuts import get_object_or_404

from modules.elm.models import (
    LeaveCategory,
    EmployeeLeaveBalance,
    LeaveApplication,
    LeaveApplicationTransition,
    SubstituteNomination,
)
from modules.elm.contracts import (
    submit_leave_application,
    process_unit_head_review,
    approve_leave_application,
    withdraw_leave_application,
    can_apply_leave,
)
from modules.elm.services import (
    get_leave_category,
    get_employee_balance,
    get_pending_applications,
    get_approved_leave_years,
    get_substitute_nominations,
    get_sla_status,
)


# -- Leave Application Endpoints -----------------------------------------------

@api_view(["GET", "POST"])
def LeaveApplicationListView(request: Request) -> Response:
    """List or create leave applications."""
    if request.method == "GET":
        user_id = request.query_params.get("user_id")
        if user_id:
            apps = get_pending_applications(int(user_id))
        else:
            # In production, this would be filtered by authenticated user
            apps = []
        return Response([{
            "id": a.id,
            "status": a.status,
            "leave_category": a.leave_category.code,
            "requested_start": a.requested_start,
            "requested_end": a.requested_end,
            "purpose": a.purpose,
        } for a in apps])

    # POST — create a new leave application
    from django.db import models
    user_id = request.data.get("user_id")
    leave_category_code = request.data.get("leave_category_code")
    requested_start = request.data.get("requested_start")
    requested_end = request.data.get("requested_end")
    purpose = request.data.get("purpose", "")
    halftype = request.data.get("halftype", "")
    station_leave = request.data.get("station_leave", False)

    # Validate eligibility
    eligibility = can_apply_leave(user_id, leave_category_code,
                                  requested_start, requested_end)
    if not eligibility["allowed"]:
        return Response({"error": eligibility["reason"]},
                        status=status.HTTP_400_BAD_REQUEST)

    application = submit_leave_application(
        user_id=user_id,
        leave_category_code=leave_category_code,
        requested_start=requested_start,
        requested_end=requested_end,
        purpose=purpose,
        halftype=halftype,
        station_leave=station_leave,
    )

    return Response({
        "id": application.id,
        "status": application.status,
        "message": "Leave application submitted successfully",
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def LeaveApplicationApplyView(request: Request) -> Response:
    """Handle leave application submission (alias for POST /applications)."""
    return LeaveApplicationListView(request)


@api_view(["POST"])
def LeaveApplicationTransitionView(request: Request, pk: int) -> Response:
    """Process a status transition on a leave application."""
    application = get_object_or_404(LeaveApplication, pk=pk)
    data = request.data
    recommended = data.get("recommended", None)
    actor_user_id = data.get("actor_user_id")
    actor_label = data.get("actor_label", "")

    if recommended is not None:
        # Unit Head review
        new_app = process_unit_head_review(
            application, bool(recommended),
            actor_user_id, actor_label,
        )
    else:
        # Could be approval/ rejection from higher authority
        next_role = data.get("next_role", "")
        new_app = approve_leave_application(
            application, next_role, actor_user_id, actor_label,
        )

    return Response({
        "id": new_app.id,
        "status": new_app.status,
    })


@api_view(["POST"])
def LeaveApplicationHistoryView(request: Request, pk: int) -> Response:
    """Get transition history for a leave application."""
    application = get_object_or_404(LeaveApplication, pk=pk)
    transitions = list(application.transitions.all().order_by("-at"))
    return Response({
        "application_id": application.id,
        "transitions": [{
            "from_status": t.from_status,
            "to_status": t.to_status,
            "actor_label": t.actor_label,
            "at": str(t.at),
            "reason": t.reason,
        } for t in transitions],
    })


@api_view(["POST"])
def LeaveApplicationBulkTransitionView(request: Request) -> Response:
    """Bulk transition of leave applications (e.g., SLA escalation)."""
    data = request.data
    application_ids = data.get("application_ids", [])
    next_status = data.get("next_status")
    actor_user_id = data.get("actor_user_id")
    actor_label = data.get("actor_label", "")

    results = []
    for app_id in application_ids:
        application = get_object_or_404(LeaveApplication, pk=app_id)
        application.status = next_status
        application.save(update_fields=["status"])

        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=next_status if hasattr(application, 'status') else "",
            to_status=next_status,
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            reason="Bulk transition via SLA/escalation",
        )
        results.append({"id": app_id, "status": next_status})

    return Response({"results": results})


# -- Leave Balance Endpoints -------------------------------------------------

@api_view(["GET"])
def EmployeeLeaveBalanceListView(request: Request) -> Response:
    """Get leave balance for the authenticated user."""
    user_id = request.query_params.get("user_id")
    if not user_id:
        return Response({"error": "user_id required"},
                        status=status.HTTP_400_BAD_REQUEST)

    balances = get_employee_balance(int(user_id))
    return Response({
        "user_id": int(user_id),
        "balances": {
            bc: {
                "remaining_days": b.remaining_days,
                "used_days": b.used_days,
                "entitlement_days": b.leave_category.entitlement_days,
                "carry_forward": b.leave_category.carry_forward,
            }
            for bc, b in balances.items()
        }
    })


# -- Leave History Endpoints -------------------------------------------------

@api_view(["GET"])
def LeaveHistoryListView(request: Request) -> Response:
    """Get approved leave history for a user."""
    user_id = request.query_params.get("user_id")
    if not user_id:
        return Response({"error": "user_id required"},
                        status=status.HTTP_400_BAD_REQUEST)

    years = get_approved_leave_years(int(user_id))
    return Response({
        "user_id": int(user_id),
        "approved_years": years,
    })


# -- Substitute Nomination Endpoints -----------------------------------------

@api_view(["GET"])
def SubstituteNominationListView(request: Request, pk: int) -> Response:
    """Get pending substitute nominations for an application."""
    nominations = get_substitute_nominations(pk)
    return Response({
        "application_id": pk,
        "nominations": [{
            "substitute_user_id": n.substitute_user_id,
            "accepted": n.accepted,
        } for n in nominations],
    })


@api_view(["POST"])
def SubstituteAcceptView(request: Request, pk: int) -> Response:
    """Accept or decline a substitute nomination."""
    nomination = get_object_or_404(SubstituteNomination, pk=pk)
    accepted = request.data.get("accepted", False)

    nomination.accepted = accepted
    if accepted:
        nomination.accepted_at = datetime.datetime.now()
    nomination.save()

    return Response({
        "substitute_user_id": nomination.substitute_user_id,
        "accepted": nomination.accepted,
    })


# -- SLA Status Endpoint ----------------------------------------------------

@api_view(["GET"])
def SLAStatusView(request: Request) -> Response:
    """Get SLA threshold configuration."""
    return Response(get_sla_status())


# -- Year-End Processing Endpoint -------------------------------------------

@api_view(["POST"])
def YearEndProcessingView(request: Request) -> Response:
    """Trigger year-end leave processing (CL/RH/SCL lapse, VL->EL conversion, EL/COL carry-forward)."""
    # This is a simplified version - real implementation would
    # iterate over all employees and apply category outcomes
    return Response({
        "message": "Year-end processing triggered",
        "note": "Full implementation applies category outcomes per specifications",
    })