from rest_framework import generics
from modules.leave.models import LeaveApplication, LeaveType, LeaveBalance
from modules.leave.serializers import (
    LeaveApplicationSerializer,
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
)


class LeaveApplicationListView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        qs = LeaveApplication.objects.all().order_by("-id")
        if p and getattr(p, "user_id", None):
            return qs.filter(user_id=p.user_id)
        return qs

    def perform_create(self, serializer):
        p = getattr(self.request, "principal", None) or getattr(self.request, "user", None)
        user_id = getattr(p, "user_id", None) or getattr(p, "id", None) or 1
        serializer.save(user_id=user_id)


class LeaveApplicationDetailView(generics.RetrieveUpdateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer


class LeaveTypeListView(generics.ListCreateAPIView):
    queryset = LeaveType.objects.all().order_by("name")
    serializer_class = LeaveTypeSerializer


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        qs = LeaveBalance.objects.all()
        if p and getattr(p, "user_id", None):
            return qs.filter(user_id=p.user_id)
        return qs
