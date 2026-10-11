from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import LeaveRequest, LeaveBalance, LeaveType


class LeaveRequestListCreateView(generics.ListCreateAPIView):
    """List and create leave requests."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Only show own requests or approved ones
        return (LeaveRequest.objects.filter(user=user) | 
                LeaveRequest.objects.filter(status='approved'))
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        # Attach current user to the request
        serializer.save(user=self.request.user)


class LeaveBalanceView(APIView):
    """Get leave balances for authenticated user."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        balances = []
        
        # Get all leave types
        leave_types = LeaveType.objects.all()
        
        for lt in leave_types:
            balance, created = LeaveBalance.objects.get_or_create(
                user=user,
                leave_type=lt,
                defaults={
                    'season_year': 2026,
                    'total_entitled': lt.entitlement_days_per_month * 12,
                    'used': 0,
                    'available': lt.entitlement_days_per_month * 12,
                }
            )
            balances.append({
                'leave_type': lt.code,
                'leave_type_name': lt.name,
                'total_entitled': balance.total_entitled,
                'used': balance.used,
                'available': balance.available,
            })
        
        return Response({'balances': balances})


class LeaveApprovalView(APIView):
    """Approve or reject a leave request."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, request_id):
        action = request.data.get('action')
        
        if action not in ['approve', 'reject']:
            return Response(
                {'error': 'Invalid action. Use "approve" or "reject".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            request_obj = LeaveRequest.objects.get(pk=request_id)
        except LeaveRequest.DoesNotExist:
            return Response(
                {'error': 'Leave request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is authorized to approve (simplified - in real app, check permissions)
        if action == 'approve':
            request_obj.status = 'approved'
            request_obj.approved_by = request.user
            request_obj.approval_date = timezone.now()
            request_obj.save()
            
            # Update balance
            request_obj.leave_type.balance.used += request_obj.duration_days
            request_obj.leave_type.balance.available -= request_obj.duration_days
            request_obj.leave_type.balance.save()
        
        else:  # reject
            request_obj.status = 'rejected'
            request_obj.rejection_reason = request.data.get('reason', '')
            request_obj.save()
        
        return Response({
            'status': 'success',
            'message': f'Request {action}d successfully.',
            'request': request_obj.id,
        })
