from rest_framework import permissions, viewsets

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import LeaveBalance, LeaveRequest
from ..serializers import LeaveBalanceSerializer, LeaveRequestSerializer


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated, HasModuleGrant("leave_cell"),
                          HasPermission("leave_cell.balances.view")]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveBalance.objects.none()
        return LeaveBalance.objects.filter(employee_id=str(self.request.principal.user_id))

class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [permissions.IsAuthenticated, HasModuleGrant("leave_cell")]

    def get_permissions(self):
        permission = ("leave_cell.requests.create" if self.request.method == "POST"
                      else "leave_cell.requests.view")
        return [permissions.IsAuthenticated(), HasModuleGrant("leave_cell")(),
                HasPermission(permission)()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return LeaveRequest.objects.filter(employee_id=str(self.request.principal.user_id))

    def perform_create(self, serializer):
        serializer.save(employee_id=str(self.request.principal.user_id))
