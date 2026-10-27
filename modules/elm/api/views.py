from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from modules.elm.models import LeaveApplication, LeaveCategory
from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveCategorySerializer,
)


class LeaveCategoryListView(generics.ListAPIView):
    queryset = LeaveCategory.objects.all()
    serializer_class = LeaveCategorySerializer
    permission_classes = [IsAuthenticated]


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [IsAuthenticated]


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [IsAuthenticated]