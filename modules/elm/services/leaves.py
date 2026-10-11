from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import Leave, LeaveCategory
from modules.elm.selectors import scoping
from modules.elm.selectors.scoping import P_MANAGE_LEAVE_REQUESTS as P_MANAGE
from modules.placement.services.authz import require


def create(user_id: int, actor, **data) -> Leave:
    require(actor, P_MANAGE)
    leave = Leave.objects.create(
        user_id=user_id,
        created_by_user_id=actor.user_id,
        created_by_recruiter_id=None if actor.kind != "recruiter" else actor.account_id,
        **data)
    return leave


def update(leave_id: int, actor, scope, **data) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be updated.", code="status_mismatch")

    touched = []
    for key, value in data.items():
        if hasattr(leave, key):
            setattr(leave, key, value)
            touched.append(key)
    if touched:
        leave.save(update_fields=[*touched, "updated_at"])
    return leave


def cancel(leave_id: int, actor, scope) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be cancelled.", code="status_mismatch")

    leave.status = "cancelled"
    leave.cancelled_by_user_id = actor.user_id
    leave.save(update_fields=["status", "cancelled_by_user_id", "updated_at"])
    return leave


def extend(leave_id: int, actor, scope) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be extended.", code="status_mismatch")

    leave.status = "extended"
    leave.extended_by_user_id = actor.user_id
    leave.save(update_fields=["status", "extended_by_user_id", "updated_at"])
    return leave


def resume(leave_id: int, actor, scope) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be resumed.", code="status_mismatch")

    leave.status = "resumed"
    leave.resumed_by_user_id = actor.user_id
    leave.save(update_fields=["status", "resumed_by_user_id", "updated_at"])
    return leave


def withdraw(leave_id: int, actor, scope) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be withdrawn.", code="status_mismatch")

    leave.status = "withdrawn"
    leave.withdrawn_by_user_id = actor.user_id
    leave.save(update_fields=["status", "withdrawn_by_user_id", "updated_at"])
    return leave


def approve(leave_id: int, actor, scope) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be approved.", code="status_mismatch")

    leave.status = "approved"
    leave.approved_by_user_id = actor.user_id
    leave.save(update_fields=["status", "approved_by_user_id", "updated_at"])
    return leave


def reject(leave_id: int, actor, scope) -> Leave:
    require(actor, P_MANAGE)
    qs = scope if scope is not None else Leave.objects.all()
    leave = (qs.select_for_update()
               .filter(pk=leave_id).first())
    if leave is None:
        raise NotFoundError("No such leave request.")
    if leave.status != "pending":
        raise ConflictError(f"Only pending requests can be rejected.", code="status_mismatch")

    leave.status = "rejected"
    leave.rejected_by_user_id = actor.user_id
    leave.save(update_fields=["status", "rejected_by_user_id", "updated_at"])
    return leave


def evaluate_for(leave: Leave, user_id: int, policy: LeaveCategory) -> dict:
    # This is a placeholder for the actual business logic.
    # The logic will depend on the specific rules defined in BR-EL-*.
    # For now, we assume all leave requests are valid and approved.
    return {"status": "approved"}
