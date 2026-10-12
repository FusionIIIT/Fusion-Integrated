"""Leave Management API views.

Follows placement module pattern: HTTP views in api/views.py,
service logic in services/views.py.
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.models import LeaveBalance, LeaveCategory, LeavePolicy, LeaveRequest, LeaveRequestAudit
from modules.leave.services import serializers as sv


# -- Leave Balance Views --


class LeaveBalanceListView(generics.ListAPIView):
    """List user's leave balances."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.balance.view"),
    ]

    def get_queryset(self):
        """Get leave balances filtered by user."""
        queryset = LeaveBalance.objects.filter(user_id=self.request.user.id).select_related("leave_category")
        return queryset


class LeaveBalanceDetailView(generics.RetrieveAPIView):
    """Get a specific user's leave balance."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.balance.view"),
    ]

    def get_queryset(self):
        """Get leave balances filtered by user."""
        queryset = LeaveBalance.objects.filter(user_id=self.request.user.id).select_related("leave_category")
        return queryset


# -- Leave Request Views --


class LeaveRequestListView(generics.ListAPIView):
    """List leave requests."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def get_queryset(self):
        """Get leave requests filtered by user."""
        queryset = LeaveRequest.objects.filter(user_id=self.request.user.id)
        return queryset


class LeaveRequestDetailView(generics.RetrieveAPIView):
    """Get a specific leave request."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def get_queryset(self):
        """Get leave requests filtered by user."""
        queryset = LeaveRequest.objects.filter(user_id=self.request.user.id)
        return queryset


class LeaveRequestCreateView(generics.CreateAPIView):
    """Create a new leave request."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.create"),
    ]

    def create(self, request, *args, **kwargs):
        """Create a leave request."""
        serializer = sv.LeaveRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            # TODO: Implement business logic here
            # Create the leave request
            from modules.leave.models import LeaveRequest
            request_instance = LeaveRequest.objects.create(**data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeaveRequestApproveView(APIView):
    """Approve a leave request."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.approve"),
    ]

    def post(self, request, pk):
        """Approve a leave request."""
        # TODO: Implement business logic here
        # Update the leave request status
        from modules.leave.models import LeaveRequest
        request_instance = LeaveRequest.objects.get(pk=pk)
        request_instance.status = "approved"
        request_instance.save()
        # Create audit trail
        from modules.leave.models import LeaveRequestAudit
        audit = LeaveRequestAudit.objects.create(
            request=request_instance,
            action="approve",
            previous_status="pending",
            new_status="approved",
            actor=request.user,
            actor_type="Unit Head",
        )
        return Response({"status": "approved"}, status=status.HTTP_200_OK)


class LeaveRequestCancelView(APIView):
    """Cancel a leave request."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.cancel"),
    ]

    def post(self, request, pk):
        """Cancel a leave request."""
        # TODO: Implement business logic here
        from modules.leave.models import LeaveRequest, LeaveRequestAudit
        request_instance = LeaveRequest.objects.get(pk=pk)
        request_instance.status = "cancelled"
        request_instance.cancelled_by = request.user
        request_instance.cancelled_at = timezone.now()
        request_instance.save()
        # Create audit trail
        audit = LeaveRequestAudit.objects.create(
            request=request_instance,
            action="cancel",
            previous_status="approved",
            new_status="cancelled",
            actor=request.user,
            actor_type="Unit Head",
        )
        return Response({"status": "cancelled"}, status=status.HTTP_200_OK)


class LeaveRequestResumeView(APIView):
    """Resume a leave request after resignation."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def post(self, request, pk):
        """Resume a leave request."""
        # TODO: Implement business logic here
        from modules.leave.models import LeaveRequest, LeaveRequestAudit
        request_instance = LeaveRequest.objects.get(pk=pk)
        request_instance.status = "resumed"
        request_instance.resumed_by = request.user
        request_instance.resumed_at = timezone.now()
        request_instance.save()
        # Create audit trail
        audit = LeaveRequestAudit.objects.create(
            request=request_instance,
            action="resumefromresigned",
            previous_status="cancelled",
            new_status="resumed",
            actor=request.user,
            actor_type="Unit Head",
        )
        return Response({"status": "resumed"}, status=status.HTTP_200_OK)


class LeaveRequestExtendView(APIView):
    """Extend a leave request."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def post(self, request, pk):
        """Extend a leave request."""
        # TODO: Implement business logic here
        from modules.leave.models import LeaveRequest, LeaveRequestAudit
        request_instance = LeaveRequest.objects.get(pk=pk)
        # Extend the leave request
        request_instance.end_date = request.data.get("end_date")
        request_instance.duration_days = request.data.get("duration_days", 1)
        request_instance.save()
        # Create audit trail
        audit = LeaveRequestAudit.objects.create(
            request=request_instance,
            action="extend",
            previous_status="approved",
            new_status="approved",
            actor=request.user,
            actor_type="Unit Head",
        )
        return Response({"status": "extended"}, status=status.HTTP_200_OK)


class LeaveRequestWithdrawView(APIView):
    """Withdraw a pending leave request."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def post(self, request, pk):
        """Withdraw a pending leave request."""
        # TODO: Implement business logic here
        from modules.leave.models import LeaveRequest, LeaveRequestAudit
        request_instance = LeaveRequest.objects.get(pk=pk)
        request_instance.status = "draft"
        request_instance.save()
        # Create audit trail
        audit = LeaveRequestAudit.objects.create(
            request=request_instance,
            action="withdraw",
            previous_status="pending",
            new_status="draft",
            actor=request.user,
            actor_type="Unit Head",
        )
        return Response({"status": "withdrawn"}, status=status.HTTP_200_OK)


# -- Leave Policy Views --


class LeavePolicyListView(generics.ListAPIView):
    """List leave policies."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.policy.view"),
    ]

    def get_queryset(self):
        """Get leave policies."""
        queryset = LeavePolicy.objects.filter(is_active=True)
        return queryset


class LeavePolicyDetailView(generics.RetrieveAPIView):
    """Get a specific leave policy."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.policy.view"),
    ]

    def get_queryset(self):
        """Get leave policies."""
        queryset = LeavePolicy.objects.filter(is_active=True)
        return queryset


class LeavePolicyUpdateView(generics.UpdateAPIView):
    """Update a leave policy (admin only)."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.policy.manage"),
    ]

    def get_queryset(self):
        """Get leave policies."""
        queryset = LeavePolicy.objects.all()
        return queryset


# -- Leave Sanction Views --


class LeaveSanctionListView(generics.ListAPIView):
    """List leave sanctions."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.sanction.view"),
    ]

    def get_queryset(self):
        """Get leave sanctions."""
        queryset = LeaveRequestAudit.objects.all()
        return queryset


class LeaveSanctionDetailView(generics.RetrieveAPIView):
    """Get a specific leave sanction."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.sanction.view"),
    ]

    def get_queryset(self):
        """Get leave sanctions."""
        queryset = LeaveRequestAudit.objects.all()
        return queryset


class LeaveSanctionCreateView(APIView):
    """Create a leave sanction."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.sanction.view"),
    ]

    def post(self, request, request_id):
        """Create a leave sanction."""
        # TODO: Implement business logic here
        from modules.leave.models import LeaveRequest, LeaveSanction
        request_instance = LeaveRequest.objects.get(pk=request_id)
        sanction = LeaveSanction.objects.create(
            request=request_instance,
            authority=request.data.get("authority"),
            authority_type=request.data.get("authority_type"),
            decision=request.data.get("decision"),
            notes=request.data.get("notes"),
        )
        return Response({"status": sanction.decision}, status=status.HTTP_201_CREATED)


# -- Leave Category Views --


class LeaveCategoryListView(generics.ListAPIView):
    """List leave categories."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def get_queryset(self):
        """Get leave categories."""
        return LeaveCategory.objects.all()


class LeaveCategoryDetailView(generics.RetrieveAPIView):
    """Get a specific leave category."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.view"),
    ]

    def get_queryset(self):
        """Get leave categories."""
        return LeaveCategory.objects.all()


# -- Holiday Calendar Views --


class LeaveHolidayCalendarListView(generics.ListAPIView):
    """List holiday calendars."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.holiday.view"),
    ]

    def get_queryset(self):
        """Get holiday calendars."""
        queryset = LeavePolicy.objects.all()  # TODO: Use LeaveHolidayCalendar model
        return queryset


class LeaveHolidayCalendarDetailView(generics.RetrieveAPIView):
    """Get a specific holiday calendar."""

    permission_classes = [
        HasModuleGrant("leave_management"),
        HasPermission("leave_management.leave.holiday.view"),
    ]

    def get_queryset(self):
        """Get holiday calendars."""
        queryset = LeavePolicy.objects.all()  # TODO: Use LeaveHolidayCalendar model
        return queryset
