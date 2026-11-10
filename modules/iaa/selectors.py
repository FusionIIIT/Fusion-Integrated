"""IAA-BR-501: role and ownership scoping is applied before object lookup."""

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, FloatField, Q, Sum
from django.db.models.functions import Cast

from core.api.exceptions import PermissionDeniedError
from modules.iaa.domain.rules import AUTHORITIES, OPERATORS, Role
from modules.iaa.models import (
    Anomaly,
    AuditEntry,
    FinancialRequest,
    Notification,
    Observation,
    RoleAssignment,
)


def assignments(user_id):
    return RoleAssignment.objects.filter(user_id=user_id, active=True).order_by(
        "role", "department"
    )


def scope(ctx, queryset, field="department"):
    departments = list(
        assignments(ctx.user_id).filter(role=ctx.role).values_list("department", flat=True)
    )
    return queryset if "" in departments else queryset.filter(**{f"{field}__in": departments})


def has_scope(user_id, role, department):
    return (
        assignments(user_id)
        .filter(role=role)
        .filter(Q(department="") | Q(department=department))
        .exists()
    )


def requests_for(ctx):
    qs = FinancialRequest.objects.all()
    if ctx.role not in OPERATORS:
        return qs.none()
    if ctx.role == Role.BASIC:
        owned = qs.filter(creator_id=ctx.user_id)
        allowed = scope(ctx, owned)
        return owned.filter(Q(pk__in=allowed) | Q(status="draft", department=""))
    if ctx.role == Role.FINANCE:
        return scope(ctx, qs.exclude(status="draft").filter(finance_user_id=ctx.user_id))
    if ctx.role == Role.AUDITOR:
        return scope(ctx, qs.exclude(status="draft"))
    if ctx.role in AUTHORITIES:
        # Former assignees retain read-only access through their immutable history.
        touched = AuditEntry.objects.filter(
            actor_id=ctx.user_id, active_role=ctx.role, action__in=["approve", "reject"]
        )
        return scope(
            ctx,
            qs.filter(
                Q(assignee_id=ctx.user_id, assignee_role=ctx.role)
                | Q(pk__in=touched.values("request_id"))
            ),
        )
    return qs.none()


def anomalies_for(ctx):
    assigned = scope(
        ctx,
        Anomaly.objects.filter(resolver_id=ctx.user_id, resolver_role=ctx.role),
        "request__department",
    )
    return Anomaly.objects.filter(Q(request__in=requests_for(ctx)) | Q(pk__in=assigned))


def observations_for(ctx):
    qs = Observation.objects.all()
    if ctx.role == Role.BASIC:
        return scope(ctx, qs.filter(respondent_id=ctx.user_id), "request__department")
    if ctx.role == Role.AUDITOR:
        return qs.filter(request__in=requests_for(ctx))
    return qs.none()


def notifications_for(ctx):
    # Role revocation/scope changes immediately hide inaccessible target records.
    request_ids = requests_for(ctx).values("id")
    extra = Anomaly.objects.filter(
        resolver_id=ctx.user_id, resolver_role=ctx.role, status__in=["open", "escalated"]
    ).values("request_id")
    extra = scope(ctx, extra, "request__department")
    observations = observations_for(ctx).values("request_id")
    return (
        Notification.objects.filter(user_id=ctx.user_id, role=ctx.role)
        .filter(
            Q(request_id__in=request_ids) | Q(request_id__in=extra) | Q(request_id__in=observations)
        )
        .order_by("-id")
    )


def summary(ctx):
    qs = requests_for(ctx)
    approval_times = AuditEntry.objects.filter(request__in=qs, action__in=["approve", "reject"])
    approval_times = approval_times.annotate(
        seconds=Cast("details__turnaround_seconds", FloatField())
    )
    turnaround = (
        qs.filter(recorded_at__isnull=False)
        .annotate(
            duration=ExpressionWrapper(
                F("recorded_at") - F("submitted_at"), output_field=DurationField()
            )
        )
        .aggregate(value=Avg("duration"))
    )
    return {
        "requests": qs.count(),
        "amount": qs.aggregate(value=Sum("amount"))["value"] or 0,
        "statuses": {
            s: qs.filter(status=s).count() for s in qs.values_list("status", flat=True).distinct()
        },
        "anomalies": list(
            Anomaly.objects.filter(request__in=qs).values("status").annotate(count=Count("id"))
        ),
        "observations": list(
            Observation.objects.filter(request__in=qs).values("status").annotate(count=Count("id"))
        ),
        "average_turnaround_seconds": (
            turnaround["value"].total_seconds() if turnaround["value"] else None
        ),
        "average_approval_turnaround_seconds": approval_times.aggregate(value=Avg("seconds"))[
            "value"
        ],
    }


def require_role(ctx, allowed):
    if ctx.role not in allowed:
        raise PermissionDeniedError("This action is not available to the active IAA role.")
