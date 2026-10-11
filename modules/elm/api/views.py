from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Leave
from .serializers import LeaveSerializer

class LeaveListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveSerializer

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

class LeaveDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveSerializer

    def get_queryset(self):
        return Leave.objects.filter(creator=self.request.user)