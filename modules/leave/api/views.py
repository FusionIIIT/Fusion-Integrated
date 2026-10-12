from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import LeaveRequest
from .serializers import LeaveRequestSerializer


class LeaveRequestListView(generics.ListCreateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

class LeaveRequestDetailView(generics.RetrieveUpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
