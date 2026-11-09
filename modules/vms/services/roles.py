"""Time-bound VMS role assignment (VMS-UC-001, CFR-002, BR-181..184).

Only a Super Admin (IAM permission ``vms.role.assign``, decision D-3) may
assign, reassign or revoke. An Admin holds no such permission, so an Admin can
assign neither Admin nor Security (BR-184: Super Admin > Admin > Security).
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.vms.models import (
    Alert,
    Escalation,
    Gate,
    RoleAssignment,
    VisitRequest,
    Zone,
)
from modules.vms.services.common import audit, authz, notify

PERM = "vms.role.assign"
HOST_KINDS = authz.HOST_KINDS      # BR-185: faculty/staff, the only assignable people
Scope = RoleAssignment.ScopeType


@dataclass(frozen=True)
class HandoffCounts:
    """What the new holder now answers for (BR-183)."""
    contingency_decisions: int = 0
    escalations: int = 0
    alerts: int = 0

    @property
    def total(self) -> int:
        return self.contingency_decisions + self.escalations + self.alerts

    def as_dict(self) -> dict:
        return {"contingency_decisions": self.contingency_decisions,
                "escalations": self.escalations, "alerts": self.alerts}


def _directory_users(user_ids):
    return directory.get_users(list(user_ids))


def _check_assignee(user_id: int) -> None:
    user = _directory_users([user_id]).get(user_id)
    if user is None:
        raise BadRequestError("The user does not exist in the directory.",
                              code="unknown_user")
    if user.kind not in HOST_KINDS:
        raise BadRequestError("Only faculty or staff can hold a VMS role.",
                              code="ineligible_user")


def _check_scope(scope_type: str, scope_id) -> int | None:
    if scope_type not in Scope.values:
        raise BadRequestError("Unknown scope type.", code="validation_error")
    if scope_type == Scope.CAMPUS:
        if scope_id is not None:
            raise BadRequestError("A campus scope has no scope id.",
                                  code="validation_error")
        return None
    if scope_id is None:
        raise BadRequestError("scope_id is required for a zone or gate scope.",
                              code="validation_error")
    model = Zone if scope_type == Scope.ZONE else Gate
    if not model.objects.filter(pk=scope_id, is_active=True).exists():
        raise BadRequestError("The scope target does not exist or is inactive.",
                              code="unknown_scope")
    return scope_id


def _overlapping(user_id, role, scope_type, scope_id, starts_at, ends_at):
    return RoleAssignment.objects.filter(
        user_id=user_id, role=role, scope_type=scope_type, scope_id=scope_id,
        revoked_at__isnull=True, starts_at__lt=ends_at, ends_at__gt=starts_at)


def assign(*, actor, user_id: int, role: str, scope_type: str = Scope.CAMPUS,
           scope_id=None, starts_at=None, ends_at=None) -> RoleAssignment:
    """BR-181: every assignment has an end. BR-184: Super Admin only."""
    authz.require(actor, PERM)
    if role not in RoleAssignment.Role.values:
        raise BadRequestError("Unknown role.", code="validation_error")
    now = timezone.now()
    starts_at = starts_at or now
    if ends_at is None:
        raise BadRequestError("A role assignment must have an end (BR-181).",
                              code="validation_error")
    if ends_at <= starts_at:
        raise BadRequestError("ends_at must be after starts_at.",
                              code="validation_error")
    if ends_at <= now:
        raise BadRequestError("ends_at is already in the past.",
                              code="validation_error")
    scope_id = _check_scope(scope_type, scope_id)
    _check_assignee(user_id)
    with transaction.atomic():
        # Serialise assignments for one user so two requests cannot both pass
        # the overlap check.
        list(RoleAssignment.objects.select_for_update().filter(user_id=user_id))
        if _overlapping(user_id, role, scope_type, scope_id, starts_at, ends_at).exists():
            raise ConflictError("An identical assignment already overlaps this window.",
                                code="overlapping_assignment")
        row = RoleAssignment.objects.create(
            user_id=user_id, role=role, scope_type=scope_type, scope_id=scope_id,
            starts_at=starts_at, ends_at=ends_at, assigned_by_user_id=actor.user_id)
        audit.record(actor=actor, action="vms.role.assigned", entity=row,
                     detail={"user_id": user_id, "role": role, "scope_type": scope_type,
                             "scope_id": scope_id, "ends_at": ends_at.isoformat()})
        notify.enqueue(
            topic="role.assigned", dedupe_key=f"role-assigned:{row.pk}",
            subject="You were assigned a VMS role",
            body=(f"You now hold the {role} role until "
                  f"{ends_at:%Y-%m-%d %H:%M}."),
            user_id=user_id, channels=("inapp",))
    return row


def _get_live_for_update(assignment_id: int, now) -> RoleAssignment:
    row = RoleAssignment.objects.select_for_update().filter(pk=assignment_id).first()
    if row is None:
        raise NotFoundError("No such role assignment.")
    if row.revoked_at is not None or row.ends_at <= now:
        raise ConflictError("The assignment is no longer active.",
                            code="assignment_inactive")
    return row


def revoke(*, actor, assignment_id: int) -> RoleAssignment:
    authz.require(actor, PERM)
    now = timezone.now()
    with transaction.atomic():
        row = _get_live_for_update(assignment_id, now)
        row.revoked_at = now
        row.save(update_fields=["revoked_at"])
        audit.record(actor=actor, action="vms.role.revoked", entity=row,
                     detail={"user_id": row.user_id, "role": row.role})
    return row


def reassign(*, actor, assignment_id: int, new_user_id: int,
             ends_at=None) -> tuple[RoleAssignment, HandoffCounts]:
    """BR-182: the old holder loses the role now and the new holder has it now."""
    authz.require(actor, PERM)
    _check_assignee(new_user_id)
    now = timezone.now()
    with transaction.atomic():
        old = _get_live_for_update(assignment_id, now)
        if old.user_id == new_user_id:
            raise BadRequestError("The role is already held by that user.",
                                  code="validation_error")
        ends_at = ends_at or old.ends_at
        if ends_at <= now:
            raise BadRequestError("ends_at is already in the past.",
                                  code="validation_error")
        if _overlapping(new_user_id, old.role, old.scope_type, old.scope_id,
                        now, ends_at).exists():
            raise ConflictError("The new holder already has an identical assignment.",
                                code="overlapping_assignment")
        old.revoked_at = now
        old.save(update_fields=["revoked_at"])
        new = RoleAssignment.objects.create(
            user_id=new_user_id, role=old.role, scope_type=old.scope_type,
            scope_id=old.scope_id, starts_at=now, ends_at=ends_at,
            assigned_by_user_id=actor.user_id)
        counts = handoff(old, new)
        audit.record(actor=actor, action="vms.role.reassigned", entity=new,
                     detail={"from_assignment": old.pk, "from_user_id": old.user_id,
                             "to_user_id": new_user_id, "handoff": counts.as_dict()})
    return new, counts


def open_items(assignment) -> HandoffCounts:
    """Open work inside the assignment's scope (BR-183).

    Nothing in the schema stores "assigned to admin X": pending contingency
    decisions, open escalations and open alerts are routed by scope, i.e. by
    whoever holds an active assignment covering them (RoleAssignment is the
    routing table). So re-pointing is implicit; this reports what moves.
    """
    requests = VisitRequest.objects.filter(status=VisitRequest.Status.AWAITING_ADMIN)
    escalations = Escalation.objects.filter(status=Escalation.Status.OPEN)
    alerts = Alert.objects.filter(status=Alert.Status.OPEN)
    if assignment.scope_type == Scope.ZONE:
        requests = requests.filter(requested_zones=assignment.scope_id)
        escalations = escalations.filter(Q(visit_log__zone_id=assignment.scope_id)
                                         | Q(visit_log__gate__zone_id=assignment.scope_id))
        alerts = alerts.filter(detail__zone_id=assignment.scope_id)
    elif assignment.scope_type == Scope.GATE:
        requests = requests.none()
        escalations = escalations.filter(visit_log__gate_id=assignment.scope_id)
        alerts = alerts.filter(detail__gate_id=assignment.scope_id)
    return HandoffCounts(contingency_decisions=requests.distinct().count(),
                         escalations=escalations.count(), alerts=alerts.count())


def handoff(old: RoleAssignment, new: RoleAssignment) -> HandoffCounts:
    """BR-183: tell the new holder what they now answer for."""
    counts = open_items(new)
    if counts.total:
        notify.enqueue(
            topic="role.handoff", dedupe_key=f"role-handoff:{new.pk}",
            subject="VMS role handed over to you",
            body=(f"You now hold open work: {counts.contingency_decisions} walk-in "
                  f"decisions, {counts.escalations} escalations, {counts.alerts} alerts."),
            user_id=new.user_id, channels=("inapp",))
    return counts


def list_active(*, actor, at=None):
    authz.require(actor, PERM)
    return RoleAssignment.objects.filter(
        revoked_at__isnull=True, ends_at__gt=at or timezone.now()).order_by("-id")


def my_roles(actor, at=None):
    """The caller's own active VMS roles; any signed-in user."""
    return authz.active_assignments(actor.user_id, at).order_by("-id")
