from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import LeaveRequest
from .serializers import LeaveRequestSerializer

class LeaveRequestListCreateView(generics.ListCreateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

class LeaveRequestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
