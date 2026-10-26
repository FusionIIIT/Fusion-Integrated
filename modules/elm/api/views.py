from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    SubstituteResponseSerializer,
)
from modules.elm.models import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    SubstituteResponse,
)


class LeaveTypeListView(generics.ListAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]

class LeaveRequestListView(generics.ListCreateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user_id=self.request.user.id)

class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user_id=self.request.user.id)

class LeaveBalanceListView(generics.ListAPIView):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveBalance.objects.filter(user_id=self.request.user.id)

class SubstituteResponseListView(generics.ListCreateAPIView):
    queryset = SubstituteResponse.objects.all()
    serializer_class = SubstituteResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SubstituteResponse.objects.filter(leave_request__user_id=self.request.user.id)
