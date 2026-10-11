from rest_framework import viewsets

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import LeaveBalance, LeaveRequest
from ..serializers import LeaveBalanceSerializer, LeaveRequestSerializer


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [
        HasModuleGrant("leave_cell"),
        HasPermission("leave_cell.balances.view"),
    ]


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [
        HasModuleGrant("leave_cell"),
        HasPermission("leave_cell.requests.manage"),
    ]

    def perform_create(self, serializer):
        serializer.save(employee_id=str(self.request.principal.user_id))
