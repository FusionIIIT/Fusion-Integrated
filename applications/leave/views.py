from decimal import Decimal
from datetime import date
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LeaveType, LeaveBalance, LeaveRequest, LeaveWorkflowHistory
from .serializers import (
    LeaveTypeSerializer, 
    LeaveBalanceSerializer, 
    LeaveRequestSerializer,
    LeaveActionSerializer,
    LeavePermissionCheckMixin
)


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for leave type information."""
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for leave balance inquiry."""
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveBalance.objects.filter(user=self.request.user)


class LeaveRequestViewSet(LeavePermissionCheckMixin, viewsets.ModelViewSet):
    """Viewset for leave request management with permission checks."""
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Applicants see their own requests; reviewers with higher permissions see all requests."""
        user = self.request.user
        if user.is_staff or self.check_permission(user, 'leave_request.review'):
            return LeaveRequest.objects.all()
        return LeaveRequest.objects.filter(user=user)

    def get_required_permission(self, action_name):
        """Map reviewer action verbs to system permission codes."""
        mapping = {
            'approve': 'leave_request.approve',
            'reject': 'leave_request.reject',
            'forward': 'leave_request.forward',
        }
        return mapping.get(action_name, 'leave_request.review')

    def perform_create(self, serializer):
        """Securely attach the authenticated user to the leave request."""
        serializer.save(user=self.request.user, status='submitted')

    def create(self, request, *args, **kwargs):
        if not self.check_permission(request.user, 'leave_request.create'):
            return Response(
                {'detail': 'You do not have permission to create leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an approved leave request before start date."""
        leave_request = self.get_object()

        if leave_request.user != request.user:
            return Response(
                {'detail': 'You can only cancel your own leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not self.check_permission(request.user, 'leave_request.cancel'):
            return Response(
                {'detail': 'You do not have permission to cancel leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            leave_request.cancel_and_restore_balance()
        except ValueError as err:
            return Response({'detail': str(err)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """Handle reviewer actions (approve/reject/forward)."""
        leave_request = self.get_object()

        # Rule: Reviewers cannot act on their own requests (prevents self-approval)
        if leave_request.user == request.user and not request.user.is_superuser:
            return Response(
                {'detail': 'Reviewers cannot approve or reject their own leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )

        action_serializer = LeaveActionSerializer(data=request.data)
        action_serializer.is_valid(raise_exception=True)
        action_type = action_serializer.validated_data['action']
        remarks = action_serializer.validated_data.get('remarks', '')

        required_perm = self.get_required_permission(action_type)
        if not self.check_permission(request.user, required_perm):
            return Response(
                {'detail': f'You do not have permission to {action_type} leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )

        prior_state = leave_request.status

        if action_type == 'approve':
            try:
                balance = LeaveBalance.objects.get(
                    user=leave_request.user,
                    leave_type=leave_request.leave_type
                )
                balance.consumed_days += Decimal(str(leave_request.total_days))
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass

            leave_request.status = 'approved'

        elif action_type == 'reject':
            leave_request.status = 'rejected'

        elif action_type == 'forward':
            leave_request.status = 'unit_head_review'

        leave_request.save()

        # Record audit log with correct prior and target states
        LeaveWorkflowHistory.objects.create(
            request=leave_request,
            from_state=prior_state,
            to_state=leave_request.status,
            reviewer=request.user,
            action_taken=action_type,
            remarks=remarks
        )

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
