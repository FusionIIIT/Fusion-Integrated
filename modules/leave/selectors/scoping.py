"""Scoping queries for leave module endpoints."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.models import LeaveRequest


def my_requests_queryset(user_id: int) -> QuerySet[LeaveRequest]:
    """Returns requests belonging to the given user."""
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")


def substitute_nominations_queryset(user_id: int) -> QuerySet[LeaveRequest]:
    """Returns requests where user is nominated as substitute and awaiting consent."""
    states = ["submitted_pending_substitute", "extension_pending_substitute"]
    return LeaveRequest.objects.filter(substitute_user_id=user_id, state__in=states).order_by(
        "-created_at"
    )


def review_queue_queryset() -> QuerySet[LeaveRequest]:
    """Returns requests pending Unit Head review."""
    states = ["pending_review", "cancellation_pending_review", "extension_pending_review"]
    return LeaveRequest.objects.filter(state__in=states).order_by("created_at")


def routing_queue_queryset() -> QuerySet[LeaveRequest]:
    """Returns requests pending Establishment routing."""
    states = ["pending_routing", "cancellation_pending_routing", "extension_pending_routing"]
    return LeaveRequest.objects.filter(state__in=states).order_by("created_at")


def sanction_queue_queryset(designation: str | None = None) -> QuerySet[LeaveRequest]:
    """Returns requests pending final sanctioning decision."""
    states = ["pending_sanction", "cancellation_pending_sanction", "extension_pending_sanction"]
    qs = LeaveRequest.objects.filter(state__in=states)
    if designation:
        qs = qs.filter(sanctioning_designation=designation)
    return qs.order_by("created_at")


def resumption_queue_queryset() -> QuerySet[LeaveRequest]:
    """Returns requests pending duty resumption verification."""
    return LeaveRequest.objects.filter(state="resumption_pending").order_by("created_at")
