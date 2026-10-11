from rest_framework import viewsets, permissions
from .models import LeaveType, LeaveBalance, LeaveApplication
from .serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveApplicationSerializer

class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return LeaveBalance.objects.all()
        else:
            return LeaveBalance.objects.filter(user=self.request.user)


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return LeaveApplication.objects.all()
        else:
            return LeaveApplication.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)