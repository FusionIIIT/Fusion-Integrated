"""HTTP layer: parse, scope, delegate, serialize.

Views are transport-only. Reads use selectors/scoping, writes use services/.
Authorisation is enforced by HasModuleGrant and HasPermission from fusion_auth.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.exceptions import ConflictError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.models import LeaveBalance, LeaveRequest
from modules.elm.selectors import scoping
from modules.elm.serializers import (
    LeaveApprovalSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)
from modules.elm.services.leave_requests import apply_leave, review_leave


class LeaveTypeViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveTypeSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [
                HasModuleGrant("elm")(),
                HasPermission("elm.leave_type.view", "elm.leave_type.manage")(),
            ]
        return [
            HasModuleGrant("elm")(),
            HasPermission("elm.leave_type.manage")(),
        ]

    def get_queryset(self):
        return scoping.scope_leave_types(getattr(self.request, "principal", None))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if (
            LeaveRequest.objects.filter(leave_type=instance).exists()
            or LeaveBalance.objects.filter(leave_type=instance).exists()
        ):
            raise ConflictError(
                "Cannot delete leave type with associated requests or balances."
            )
        return super().destroy(request, *args, **kwargs)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.leave_balance.view_self", "elm.leave_balance.view"),
    ]
    pagination_class = CursorPagination
    ordering = ["-id"]

    def get_queryset(self):
        return scoping.scope_leave_balances(getattr(self.request, "principal", None))


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    pagination_class = CursorPagination
    ordering = ["-id"]

    def get_permissions(self):
        if self.action == "create":
            return [
                HasModuleGrant("elm")(),
                HasPermission("elm.leave_request.create")(),
            ]
        if self.action == "approve_reject":
            return [
                HasModuleGrant("elm")(),
                HasPermission("elm.leave_request.review")(),
            ]
        if self.action == "pending":
            return [
                HasModuleGrant("elm")(),
                HasPermission(
                    "elm.leave_request.review", "elm.leave_request.view"
                )(),
            ]
        return [
            HasModuleGrant("elm")(),
            HasPermission(
                "elm.leave_request.view_self", "elm.leave_request.view"
            )(),
        ]

    def get_queryset(self):
        return scoping.scope_leave_requests(getattr(self.request, "principal", None))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = page if page is not None else list(queryset)
        people = directory.get_users([r.employee_user_id for r in target])
        serializer = self.get_serializer(
            target, many=True, context={"people": people, "request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        people = directory.get_users([instance.employee_user_id])
        serializer = self.get_serializer(
            instance, context={"people": people, "request": request}
        )
        return Response(serializer.data)

    def perform_create(self, serializer):
        data = serializer.validated_data
        leave = apply_leave(
            principal=self.request.principal,
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data.get("reason", ""),
        )
        serializer.instance = leave

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[
            HasModuleGrant("elm"),
            HasPermission("elm.leave_request.review"),
        ],
    )
    def approve_reject(self, request, pk=None):
        leave = self.get_object()
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_val = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")
        updated_leave = review_leave(
            principal=request.principal,
            leave_request_id=leave.id,
            action=action_val,
            remarks=remarks,
        )
        people = directory.get_users([updated_leave.employee_user_id])
        return Response(
            LeaveRequestSerializer(
                updated_leave, context={"people": people, "request": request}
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[
            HasModuleGrant("elm"),
            HasPermission(
                "elm.leave_request.review", "elm.leave_request.view"
            ),
        ],
    )
    def pending(self, request):
        qs = self.get_queryset().filter(status="pending")
        page = self.paginate_queryset(qs)
        target = page if page is not None else list(qs)
        people = directory.get_users([r.employee_user_id for r in target])
        serializer = self.get_serializer(
            target, many=True, context={"people": people, "request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
