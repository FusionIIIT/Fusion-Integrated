from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import LeaveType, LeaveBalance, LeaveRequest
from .services import apply_leave, approve_leave, reject_leave

class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    permission_classes = [permissions.IsAuthenticated]

class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all()
    permission_classes = [permissions.IsAuthenticated]

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        leave_type = LeaveType.objects.get(pk=request.data.get('leave_type'))
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        apply_leave(user, leave_type, start_date, end_date)
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        leave_request = self.get_object()
        if 'approve' in request.data:
            approve_leave(leave_request)
        elif 'reject' in request.data:
            reject_leave(leave_request)
        return Response(status=status.HTTP_200_OK)