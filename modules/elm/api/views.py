"""ELM HTTP adapters using the platform permission gates and error envelope."""

import html

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import views
from rest_framework.response import Response

from core.api.exceptions import DomainError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.elm.domain.state_machine import CREDITS
from modules.elm.models import (
    AccountEntry,
    LeaveActionLog,
    LeaveBalance,
    LeaveRequest,
    Notification,
)
from modules.elm.services.leave_service import LeaveService, account, employee, lock_people

from .serializers import (
    ApproverDecisionSerializer,
    FollowupActionSerializer,
    FollowupSerializer,
    LeaveBalanceSerializer,
    LeaveCreateSerializer,
    LeaveRequestSerializer,
    LedgerEntrySerializer,
    MaintenanceSerializer,
    NotificationSerializer,
    OfflineSerializer,
    ReasonSerializer,
    ReplacementSerializer,
    SubstituteDecisionSerializer,
)


class ElmView(views.APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm")]

    def get_permissions(self):
        return [*super().get_permissions(), HasPermission(self.permission_code)()]


@extend_schema_view(
    get=extend_schema(responses=LeaveRequestSerializer(many=True), operation_id="elm_my_leaves"),
    post=extend_schema(
        request=LeaveCreateSerializer,
        responses={201: LeaveRequestSerializer},
        operation_id="elm_apply",
    ),
)
class LeaveListCreateView(ElmView):
    @property
    def permission_code(self):
        return "elm.leave.apply" if self.request.method == "POST" else "elm.leave.view_self"

    def get(self, request):
        qs = LeaveRequest.objects.filter(
            applicant_user_id=str(request.principal.user_id)
        ).prefetch_related("action_logs")
        return Response(LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        s = LeaveCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            LeaveRequestSerializer(
                LeaveService.apply_leave(request.principal, **s.validated_data)
            ).data,
            status=201,
        )


@extend_schema_view(
    get=extend_schema(
        responses=LeaveBalanceSerializer(many=True),
        parameters=[OpenApiParameter("year", int)],
        operation_id="elm_balances",
    )
)
class LeaveBalanceView(ElmView):
    permission_code = "elm.leave.view_self"

    @transaction.atomic
    def get(self, request):
        try:
            year = int(request.query_params.get("year", timezone.localdate().year))
        except ValueError as exc:
            raise DomainError("Year must be an integer.") from exc
        if not 1900 <= year <= 2200:
            raise DomainError("Year must be between 1900 and 2200.")
        lock_people([request.principal.user_id])
        profile = employee(request.principal.user_id)
        for category in CREDITS:
            account(profile, category, year)
        qs = LeaveBalance.objects.filter(user_id=profile.user_id, year=year).order_by("leave_type")
        return Response(LeaveBalanceSerializer(qs, many=True).data)


@extend_schema_view(
    get=extend_schema(
        responses=LeaveRequestSerializer(many=True), operation_id="elm_substitute_queue"
    )
)
class SubstituteQueueView(ElmView):
    permission_code = "elm.leave.substitute"

    def get(self, request):
        qs = LeaveRequest.objects.filter(
            substitute_user_id=str(request.principal.user_id), status="PENDING_SUBSTITUTE"
        ).prefetch_related("action_logs")
        return Response(LeaveRequestSerializer(qs, many=True).data)


@extend_schema_view(
    post=extend_schema(
        request=SubstituteDecisionSerializer,
        responses=LeaveRequestSerializer,
        operation_id="elm_substitute_decision",
    )
)
class SubstituteDecisionView(ElmView):
    permission_code = "elm.leave.substitute"

    def post(self, request, pk):
        s = SubstituteDecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        req = LeaveService.respond_substitute(request.principal, pk, **s.validated_data)
        return Response(LeaveRequestSerializer(req).data)


@extend_schema_view(
    post=extend_schema(
        request=ReplacementSerializer,
        responses=LeaveRequestSerializer,
        operation_id="elm_replace_substitute",
    )
)
class ReplacementView(ElmView):
    permission_code = "elm.leave.apply"

    def post(self, request, pk):
        s = ReplacementSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            LeaveRequestSerializer(
                LeaveService.replace_substitute(request.principal, pk, **s.validated_data)
            ).data
        )


@extend_schema_view(
    get=extend_schema(responses=LeaveRequestSerializer(many=True), operation_id="elm_approvals")
)
class ApprovalsQueueView(ElmView):
    permission_code = "elm.leave.approve"

    def get(self, request):
        qs = LeaveRequest.objects.filter(
            current_approver_user_id=str(request.principal.user_id),
            current_approver_role=request.principal.active_role,
            status__in=["PENDING_UNIT_HEAD", "PENDING_AUTHORITY"],
        ).prefetch_related("action_logs")
        return Response(LeaveRequestSerializer(qs, many=True).data)


@extend_schema_view(
    post=extend_schema(
        request=ApproverDecisionSerializer,
        responses=LeaveRequestSerializer,
        operation_id="elm_decide",
    )
)
class ApproverDecisionView(ElmView):
    permission_code = "elm.leave.approve"

    def post(self, request, pk):
        s = ApproverDecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        req = LeaveService.review_unit_head(request.principal, pk, **s.validated_data)
        return Response(LeaveRequestSerializer(req).data)


@extend_schema_view(
    post=extend_schema(
        request=ReasonSerializer, responses=LeaveRequestSerializer, operation_id="elm_withdraw"
    )
)
class LeaveWithdrawView(ElmView):
    permission_code = "elm.leave.apply"

    def post(self, request, pk):
        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            LeaveRequestSerializer(
                LeaveService.withdraw_leave(request.principal, pk, **s.validated_data)
            ).data
        )


@extend_schema_view(
    post=extend_schema(
        request=FollowupActionSerializer,
        responses={201: LeaveRequestSerializer},
        parameters=[
            OpenApiParameter(
                "kind", str, OpenApiParameter.PATH, enum=["cancel", "extend", "resume"]
            )
        ],
        operation_id="elm_followup",
    )
)
class FollowupView(ElmView):
    permission_code = "elm.leave.apply"

    def post(self, request, pk, kind):
        s = (
            ReasonSerializer(data=request.data)
            if kind == "cancel"
            else FollowupSerializer(data=request.data)
        )
        s.is_valid(raise_exception=True)
        req = LeaveService.followup(request.principal, pk, kind.upper(), **s.validated_data)
        return Response(LeaveRequestSerializer(req).data, status=201)


@extend_schema_view(
    get=extend_schema(responses={(200, "text/html"): OpenApiTypes.STR}, operation_id="elm_export")
)
class ExportView(ElmView):
    permission_code = "elm.leave.view_self"

    def get(self, request, pk):
        try:
            req = LeaveRequest.objects.get(pk=pk, applicant_user_id=str(request.principal.user_id))
        except LeaveRequest.DoesNotExist as exc:
            raise NotFoundError() from exc
        rows = [
            ("Reference", req.id),
            ("Employee", req.applicant_user_id),
            ("Category", req.leave_type),
            ("Request type", req.request_kind),
            ("Dates", f"{req.start_date} to {req.end_date}"),
            ("Days", req.duration_days),
            ("Reason", req.reason),
            ("Status", req.status),
            ("Station address", req.station_leave_address),
        ]
        body = "".join(
            f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows
        )
        history = "".join(
            f"<li>{html.escape(str(a.created_at))}: "
            f"{html.escape(a.action)} - {html.escape(a.remarks)}</li>"
            for a in req.action_logs.all()
        )
        doc = (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            "<title>Leave application</title><style>"
            "body{font:16px sans-serif;max-width:800px;margin:40px auto}"
            "td,th{text-align:left;padding:8px;border:1px solid #ccc}"
            "table{border-collapse:collapse}@media print{body{margin:0}}"
            f"</style><h1>Leave application</h1><table>{body}</table>"
            f"<h2>History</h2><ul>{history}</ul></html>"
        )
        response = HttpResponse(doc, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="leave-{req.id}.html"'
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
        return response


@extend_schema_view(
    get=extend_schema(responses=NotificationSerializer(many=True), operation_id="elm_notifications")
)
class NotificationsView(ElmView):
    permission_code = "elm.leave.view_self"

    def get(self, request):
        return Response(
            list(
                Notification.objects.filter(recipient_user_id=str(request.principal.user_id))
                .order_by("-created_at")
                .values("id", "event", "message", "created_at", "request_id")[:200]
            )
        )


@extend_schema_view(
    get=extend_schema(responses=LedgerEntrySerializer(many=True), operation_id="elm_ledger")
)
class LedgerView(ElmView):
    permission_code = "elm.leave.view_self"

    def get(self, request):
        return Response(
            list(
                AccountEntry.objects.filter(user_id=str(request.principal.user_id))
                .order_by("-created_at")
                .values("id", "year", "leave_type", "action", "amount", "created_at", "request_id")
            )
        )


@extend_schema_view(
    post=extend_schema(
        request=OfflineSerializer,
        responses={201: LeaveRequestSerializer},
        operation_id="elm_offline",
    )
)
class OfflineView(ElmView):
    permission_code = "elm.leave.admin"

    def post(self, request):
        s = OfflineSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        req = LeaveService.record_offline(request.principal, **s.validated_data)
        return Response(LeaveRequestSerializer(req).data, status=201)


@extend_schema_view(
    post=extend_schema(
        request=MaintenanceSerializer,
        responses=LeaveRequestSerializer,
        operation_id="elm_maintenance",
    )
)
class MaintenanceView(ElmView):
    permission_code = "elm.leave.admin"

    @transaction.atomic
    def post(self, request, pk):
        # Annotation is intentionally not an alternative sanction/ledger endpoint.
        if (
            set(request.data) != {"remarks"}
            or not isinstance(request.data["remarks"], str)
            or not request.data["remarks"].strip()
        ):
            raise DomainError(
                "Maintenance accepts only nonempty audit remarks; "
                "sanction and balance fields are immutable."
            )
        try:
            req = LeaveRequest.objects.select_for_update().get(pk=pk)
        except LeaveRequest.DoesNotExist as exc:
            raise NotFoundError() from exc
        LeaveActionLog.objects.create(
            leave_request=req,
            actor_user_id=str(request.principal.user_id),
            actor_role="leave_admin",
            action="MAINTENANCE_NOTE",
            remarks=request.data["remarks"][:4000],
        )
        return Response(LeaveRequestSerializer(req).data)
