from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LeaveType, LeaveBalance, LeaveRequest
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
    
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for leave balance inquiry."""
    
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """Viewset for leave request management with permission checks."""
    
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        """Return only the authenticated user's leave requests."""
        user = self.request.user
        return LeaveRequest.objects.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Create a new leave request with validation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check permission for creating requests
        if not self.check_permission(request.user, 'leave_request.create'):
            return Response(
                {'detail': 'You do not have permission to create leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def list(self, request, *args, **kwargs):
        """List leave requests with permission check."""
        if not self.check_permission(request.user, 'leave_request.view'):
            return Response(
                {'detail': 'You do not have permission to view leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a leave request with permission check."""
        instance = self.get_object()
        
        # Only allow viewing own requests
        if instance.user != request.user:
            return Response(
                {'detail': 'You can only view your own leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an approved leave request before start date."""
        leave_request = self.get_object()
        
        # Only allow cancellation of own requests
        if leave_request.user != request.user:
            return Response(
                {'detail': 'You can only cancel your own leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check permission for cancellation
        if not self.check_permission(request.user, 'leave_request.cancel'):
            return Response(
                {'detail': 'You do not have permission to cancel leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if request is approved
        if leave_request.status != 'approved':
            return Response(
                {'detail': 'Only approved leave requests can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if leave has started
        today = date.today()
        if today >= leave_request.start_date:
            return Response(
                {'detail': 'Cannot cancel after leave start date.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restore balance and mark as cancelled
        leave_request.cancel_and_restore_balance()
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """Handle reviewer actions (approve/reject/forward)."""
        leave_request = self.get_object()
        
        # Only allow reviewers to take actions on their own requests
        if leave_request.user != request.user:
            return Response(
                {'detail': 'You can only act on your own leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        action_serializer = LeaveActionSerializer(data=request.data)
        action_serializer.is_valid(raise_exception=True)
        
        action = action_serializer.validated_data['action']
        
        # Check permission for the specific action
        required_perm = self.get_required_permission(action)
        if not self.check_permission(request.user, required_perm):
            return Response(
                {'detail': f'You do not have permission to {action} leave requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Handle the action
        if action == 'approve':
            # Deduct balance only on approval
            try:
                balance = LeaveBalance.objects.get(
                    user=leave_request.user,
                    leave_type=leave_request.leave_type
                )
                balance.consumed_days += float(leave_request.total_days)
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass  # No balance record
            
            leave_request.status = 'approved'
            
        elif action == 'reject':
            # Reject - no balance change needed
            leave_request.status = 'rejected'
            
        elif action == 'forward':
            # Forward to next reviewer - no state change yet
            pass
        
        leave_request.save()
        
        # Record workflow history
        from .models import LeaveWorkflowHistory
        history, _ = LeaveWorkflowHistory.objects.get_or_create(
            request=leave_request,
            defaults={
                'from_state': leave_request.status,
                'to_state': action,
                'reviewer': request.user,
                'action_taken': action,
                'remarks': action_serializer.validated_data.get('remarks', '')
            }
        )
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete is not allowed - use cancel endpoint instead."""
        return Response(
            {'detail': 'Use the cancel endpoint to cancel leave requests.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
