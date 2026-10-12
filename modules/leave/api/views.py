from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.services import (
    get_dashboard_summary,
    get_leave_balances,
    get_leave_requests_for_user,
    get_leave_types,
    get_review_queue,
)

ENFORCED_LEAVE_PERMISSIONS = (
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
    "leave.request.view",
    "leave.request.approve",
    "leave.balance.update",
    "leave.type.manage",
)


class LeaveDashboardView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    def get(self, request, *args, **kwargs):
        employee_id = getattr(request.principal, "user_id", None)
        payload = get_dashboard_summary(employee_id)
        payload["enforced_permissions"] = ENFORCED_LEAVE_PERMISSIONS
        return Response(payload)


class LeaveRequestListView(APIView):
    permission_classes = [
        HasModuleGrant("leave"),
        HasPermission("leave.request.view_self", "leave.request.create", "leave.request.delete"),
    ]

    def get(self, request, *args, **kwargs):
        items = get_leave_requests_for_user(getattr(request.principal, "user_id", None))
        return Response({"items": items, "count": len(items)})


class LeaveReviewView(APIView):
    permission_classes = [
        HasModuleGrant("leave"),
        HasPermission("leave.request.view", "leave.request.approve"),
    ]

    def get(self, request, *args, **kwargs):
        items = get_review_queue()
        return Response({"items": items, "count": len(items)})


class LeaveBalanceManagementView(APIView):
    permission_classes = [
        HasModuleGrant("leave"),
        HasPermission("leave.balance.update"),
    ]

    def get(self, request, *args, **kwargs):
        balances = get_leave_balances(getattr(request.principal, "user_id", None))
        return Response({"balances": balances})


class LeaveTypeManagementView(APIView):
    permission_classes = [
        HasModuleGrant("leave"),
        HasPermission("leave.type.manage"),
    ]

    def get(self, request, *args, **kwargs):
        return Response({"leave_types": get_leave_types()})
