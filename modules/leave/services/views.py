"""Leave Management service views.

Follows placement module pattern: thin HTTP layer in api/
"""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.authentication import LeaveAuthentication
from modules.leave.models import (
    LeaveBalance,
    LeaveCategory,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestAudit,
)
from modules.leave.services import serializers as sv

MODULE = HasModuleGrant("leave_management")

# Permission codes
P_VIEW_LEAVE = "leave_management.leave.view"
P_VIEW_LEAVE_BALANCE = "leave_management.leave.balance.view"
P_CREATE_LEAVE = "leave_management.leave.create"
P_APPROVE_LEAVE = "leave_management.leave.approve"
P_CANCEL_LEAVE = "leave_management.leave.cancel"
P_VIEW_SANCTIONS = "leave_management.leave.sanction.view"
P_VIEW_POLICIES = "leave_management.leave.policy.view"


def _actor(request):
    """Get the current user from request."""
    return getattr(request, "principal", None)


def _client_ip(request):
    """Get client IP address."""
    from rest_framework.settings import api_settings

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = api_settings.NUM_PROXIES or 0
    if forwarded and hops:
        addrs = [a.strip() for a in forwarded.split(",") if a.strip()]
        if addrs:
            return addrs[-min(hops, len(addrs))]
    return request.META.get("REMOTE_ADDR")


class _Scoped(generics.GenericAPIView):
    """Leave module scoped views with authentication."""

    authentication_classes = [LeaveAuthentication]

    def get_serializer_context(self):
        """Get serializer context with actor."""
        ctx = super().get_serializer_context()
        ctx["actor"] = _actor(self.request)
        return ctx


# -- Leave Balance Views ------------------------------------------------------


class LeaveBalanceListView(_Scoped, generics.ListAPIView):
    """List user's leave balances."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.balance.view")]

    def get_queryset(self):
        """Get leave balances filtered by user."""
        queryset = LeaveBalance.objects.filter(user_id=self.request.user.id).select_related("leave_category")
        return queryset

    def get_serializer_context(self):
        """Get serializer context."""
        ctx = super().get_serializer_context()
        ctx["user_id"] = self.request.user.id
        ctx["actor"] = _actor(self.request)
        return ctx

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveBalanceSerializer


# -- Leave Request Views ------------------------------------------------------


class LeaveRequestListView(_Scoped, generics.ListAPIView):
    """List leave requests."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.view")]

    def get_queryset(self):
        """Get leave requests filtered by user."""
        queryset = LeaveRequest.objects.filter(user_id=self.request.user.id)
        return queryset

    def get_serializer_context(self):
        """Get serializer context."""
        ctx = super().get_serializer_context()
        ctx["user_id"] = self.request.user.id
        ctx["actor"] = _actor(self.request)
        return ctx

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveRequestSerializer


class LeaveRequestCreateView(_Scoped, generics.CreateAPIView):
    """Create a new leave request."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.create")]

    def create(self, request, *args, **kwargs):
        """Create a leave request."""
        serializer = sv.LeaveRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            # Business logic would go here
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveRequestCreateSerializer


class LeaveRequestUpdateView(_Scoped, generics.UpdateAPIView):
    """Update a leave request (draft only)."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.view")]

    def get_queryset(self):
        """Get leave requests filtered by user."""
        queryset = LeaveRequest.objects.filter(user_id=self.request.user.id)
        return queryset

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveRequestUpdateSerializer


# -- Leave Policy Views -------------------------------------------------------


class LeavePolicyListView(_Scoped, generics.ListAPIView):
    """List leave policies."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.policy.view")]

    def get_queryset(self):
        """Get leave policies."""
        queryset = LeavePolicy.objects.filter(is_active=True)
        return queryset

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeavePolicySerializer


class LeavePolicyDetailView(_Scoped, generics.RetrieveAPIView):
    """Get a specific leave policy."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.policy.view")]

    def get_queryset(self):
        """Get leave policies."""
        queryset = LeavePolicy.objects.filter(is_active=True)
        return queryset

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeavePolicySerializer


class LeavePolicyUpdateView(_Scoped, generics.UpdateAPIView):
    """Update a leave policy (admin only)."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.policy.manage")]

    def get_queryset(self):
        """Get leave policies."""
        queryset = LeavePolicy.objects.all()
        return queryset

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeavePolicySerializer


# -- Leave Sanction Views -----------------------------------------------------


class LeaveSanctionListView(_Scoped, generics.ListAPIView):
    """List leave sanctions."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.sanction.view")]

    def get_queryset(self):
        """Get leave sanctions."""
        queryset = LeaveRequestAudit.objects.all()
        return queryset

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveRequestAuditSerializer


# -- Leave Category Views -----------------------------------------------------


class LeaveCategoryListView(_Scoped, generics.ListAPIView):
    """List leave categories."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.view")]

    def get_queryset(self):
        """Get leave categories."""
        return LeaveCategory.objects.all()

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveCategorySerializer


class LeaveCategoryDetailView(_Scoped, generics.RetrieveAPIView):
    """Get a specific leave category."""

    permission_classes = [HasModuleGrant("leave_management"), HasPermission("leave_management.leave.view")]

    def get_queryset(self):
        """Get leave categories."""
        return LeaveCategory.objects.all()

    def get_serializer(self):
        """Get serializer instance."""
        return sv.LeaveCategorySerializer
