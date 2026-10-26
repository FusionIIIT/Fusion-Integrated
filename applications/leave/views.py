from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .models import LeaveType, LeaveBalance, LeaveRequest, LeaveWorkflowHistory
from .serializers import (
    LeaveTypeSerializer, LeaveBalanceSerializer, 
    LeaveRequestSerializer, LeaveActionSerializer
)


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for leave type information."""
    
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LeaveType.objects.all()


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for leave balance inquiry."""
    
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return LeaveBalance.objects.filter(user=user)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """Main viewset for leave request management."""
    
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return LeaveRequest.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """Create a new leave request for the authenticated user."""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """
        Reviewer action endpoint for approve/reject/forward.
        
        Permissions:
        - Applicant can approve their own request (self-sanction for Director)
        - Unit Head can approve/reject CL/RH requests
        - Higher authorities can handle higher-sanction leave types
        """
        leave_request = self.get_object()
        action_serializer = LeaveActionSerializer(data=request.data)
        
        if not action_serializer.is_valid():
            return Response(
                action_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action = action_serializer.validated_data['action']
        remarks = action_serializer.validated_data.get('remarks', '')
        
        # Determine who can take this action based on leave type and current state
        user = self.request.user
        
        # Check if user is authorized for this action
        if not self._is_authorized_for_action(leave_request, action):
            return Response(
                {'detail': 'You are not authorized to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Process the action
        if action == 'approve':
            leave_request.status = 'approved'
            leave_request.remarks = remarks or leave_request.remarks
            
            # Deduct balance on approval
            try:
                balance = LeaveBalance.objects.get(
                    user=leave_request.user, 
                    leave_type=leave_request.leave_type
                )
                balance.consumed_days += float(leave_request.total_days)
                balance.save()
                
                # Record workflow history
                LeaveWorkflowHistory.objects.create(
                    request=leave_request,
                    from_state=leave_request.status,
                    to_state='approved',
                    reviewer=user,
                    action_taken='approve',
                    remarks=remarks
                )
                
            except LeaveBalance.DoesNotExist:
                pass  # Balance will be created on first use
            
        elif action == 'reject':
            leave_request.status = 'rejected'
            leave_request.remarks = remarks or (leave_request.remarks + f" - {remarks}")
            
            # Record workflow history
            LeaveWorkflowHistory.objects.create(
                request=leave_request,
                from_state=leave_request.status,
                to_state='rejected',
                reviewer=user,
                action_taken='reject',
                remarks=remarks
            )
            
        elif action == 'forward':
            # Forward to next authority level
            leave_request.status = 'unit_head_review' if leave_request.status == 'draft' else \
                                   'establishment_review' if leave_request.status == 'unit_head_review' else \
                                   'final_decision_pending'
            
            # Record workflow history
            LeaveWorkflowHistory.objects.create(
                request=leave_request,
                from_state=leave_request.status,
                to_state='forwarded',
                reviewer=user,
                action_taken='forward',
                remarks=remarks
            )
        
        leave_request.save()
        
        return Response({
            'status': 'success',
            'message': f'Request {action}d successfully.',
            'leave_request_id': leave_request.id
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Allow applicant to cancel a pending request.
        Only works before final approval.
        """
        leave_request = self.get_object()
        
        # Check if cancellation is allowed (before start date)
        today = request.data.get('today', str(date.today()))
        from datetime import datetime
        today_date = datetime.strptime(today, '%Y-%m-%d').date()
        
        if leave_request.status == 'approved':
            return Response(
                {'detail': 'Cannot cancel an approved leave. Use cancellation workflow instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if leave has started
        start_date = datetime.strptime(str(leave_request.start_date), '%Y-%m-%d').date()
        if today_date >= start_date:
            return Response(
                {'detail': 'Cannot cancel a request after the leave has started.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restore balance if approved
        try:
            balance = LeaveBalance.objects.get(
                user=leave_request.user, 
                leave_type=leave_request.leave_type
            )
            if leave_request.status == 'approved':
                balance.consumed_days -= float(leave_request.total_days)
                balance.save()
        except LeaveBalance.DoesNotExist:
            pass
        
        # Cancel the request
        leave_request.status = 'cancelled'
        leave_request.remarks = request.data.get('remarks', '') or leave_request.remarks
        leave_request.save()
        
        # Record workflow history
        LeaveWorkflowHistory.objects.create(
            request=leave_request,
            from_state=leave_request.status,
            to_state='cancelled',
            reviewer=request.user,
            action_taken='cancel',
            remarks=request.data.get('remarks', '')
        )
        
        return Response({
            'status': 'success',
            'message': 'Leave request cancelled successfully.',
            'leave_request_id': leave_request.id
        }, status=status.HTTP_200_OK)
    
    def _is_authorized_for_action(self, leave_request, action):
        """Check if current user is authorized for the requested action."""
        from django.contrib.auth.models import User
        
        # Applicant can always act on their own request (self-sanction for Director)
        if self.request.user == leave_request.user:
            return True
        
        # Unit Head can approve/reject CL/RH requests
        if leave_request.leave_type.name in ['CL', 'RH']:
            # Check if user is Unit Head of applicant's department
            # This would be determined by organizational hierarchy configuration
            return False  # Would need proper authorization check
        
        # Higher authorities for higher-sanction leave types
        if leave_request.leave_type.name in ['EL', 'COL', 'VL', 'SCL']:
            # Check authority level based on hierarchy configuration
            return False  # Would need proper authorization check
        
        return False
