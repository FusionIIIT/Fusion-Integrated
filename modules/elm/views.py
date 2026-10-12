from rest_framework import generics, permissions
from .models import LeaveRequest, LeaveApproval
from .serializers import LeaveRequestSerializer, LeaveApprovalSerializer

class LeaveRequestList(generics.ListCreateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class LeaveRequestDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

class LeaveApprovalList(generics.ListCreateAPIView):
    queryset = LeaveApproval.objects.all()
    serializer_class = LeaveApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]

class LeaveApprovalDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveApproval.objects.all()
    serializer_class = LeaveApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]