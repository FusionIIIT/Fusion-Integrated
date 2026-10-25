from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from ..models.leave import EmployeeLeave, LeaveBalance, LeaveStatus, LeaveType
from .serializers import EmployeeLeaveSerializer, LeaveBalanceSerializer

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeLeaveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if self.action in ['unit_head_reviews', 'unit_head_decision']:
            return EmployeeLeave.objects.all()
        if hasattr(user, 'user_id'):
            return EmployeeLeave.objects.filter(applicant_id=user.user_id)
        return EmployeeLeave.objects.filter(applicant=user)

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'user_id'):
            User = EmployeeLeave._meta.get_field('applicant').remote_field.model
            django_user, _ = User.objects.get_or_create(
                id=user.user_id,
                defaults={'username': user.username, 'email': getattr(user, 'email', '')}
            )
            serializer.save(applicant=django_user)
        else:
            serializer.save(applicant=user)

    @action(detail=False, methods=['get'])
    def unit_head_reviews(self, request):
        pending_leaves = EmployeeLeave.objects.filter(status=LeaveStatus.SUBMITTED)
        serializer = EmployeeLeaveSerializer(pending_leaves, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unit_head_decision(self, request, pk=None):
        leave = self.get_object()
        decision = request.data.get('decision')
        remarks = request.data.get('remarks', '')

        if decision == 'APPROVE':
            with transaction.atomic():
                try:
                    balance = LeaveBalance.objects.select_for_update().get(
                        user=leave.applicant,
                        leave_type=leave.leave_type,
                        year=leave.start_date.year
                    )
                except LeaveBalance.DoesNotExist:
                    return Response(
                        {'error': f'No leave balance record found for year {leave.start_date.year}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if balance.available < leave.duration_days:
                    return Response(
                        {'error': f'Insufficient leave balance. Available: {balance.available}, Requested: {leave.duration_days}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                balance.available -= leave.duration_days
                balance.consumed += leave.duration_days
                balance.save()

                leave.status = LeaveStatus.APPROVED
                leave.unit_head_remarks = remarks
                leave.save()

            return Response(EmployeeLeaveSerializer(leave).data, status=status.HTTP_200_OK)

        elif decision == 'RECOMMEND':
            leave.status = LeaveStatus.RECOMMENDED
            leave.unit_head_remarks = remarks
            leave.save()
            return Response(EmployeeLeaveSerializer(leave).data, status=status.HTTP_200_OK)

        elif decision == 'REJECT':
            leave.status = LeaveStatus.REJECTED
            leave.unit_head_remarks = remarks
            leave.save()
            return Response(EmployeeLeaveSerializer(leave).data, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid decision. Choices: APPROVE, RECOMMEND, REJECT'}, status=status.HTTP_400_BAD_REQUEST)
