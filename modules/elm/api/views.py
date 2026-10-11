from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models.leave import EmployeeLeave, LeaveBalance, LeaveStatus
from .serializers import EmployeeLeaveSerializer, LeaveBalanceSerializer

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if self.action in ['unit_head_reviews']:
            return EmployeeLeave.objects.filter(status=LeaveStatus.SUBMITTED)
        return EmployeeLeave.objects.filter(applicant=user)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    @action(detail=True, methods=['post'])
    def unit_head_decision(self, request, pk=None):
        leave = self.get_object()
        decision = request.data.get('decision')
        remarks = request.data.get('remarks', '')

        if decision == 'APPROVE':
            leave.status = LeaveStatus.APPROVED
        elif decision == 'RECOMMEND':
            leave.status = LeaveStatus.RECOMMENDED
        elif decision == 'REJECT':
            leave.status = LeaveStatus.REJECTED
        else:
            return Response({'error': 'Invalid decision'}, status=status.HTTP_400_BAD_REQUEST)

        leave.unit_head_remarks = remarks
        leave.save()
        return Response(EmployeeLeaveSerializer(leave).data)
