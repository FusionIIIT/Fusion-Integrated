from rest_framework import generics, permissions

from .models import LeaveRequest
from .permissions import IsLeaveRequestOwner
from .serializers import LeaveRequestSerializer


class LeaveRequestCreateView(generics.CreateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        actor_id = getattr(getattr(self.request, "principal", None), "user_id", None)
        if actor_id is None:
            actor_id = getattr(self.request.user, "user_id", getattr(self.request.user, "id", None))
        serializer.save(user_id=actor_id)


class LeaveRequestListView(generics.ListAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        actor_id = getattr(getattr(self.request, "principal", None), "user_id", None)
        if actor_id is None:
            actor_id = getattr(self.request.user, "user_id", getattr(self.request.user, "id", None))
        if actor_id is not None:
            return LeaveRequest.objects.filter(user_id=actor_id)
        return LeaveRequest.objects.all()


class LeaveRequestDetailView(generics.RetrieveUpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsLeaveRequestOwner]


class LeaveRequestApproveView(generics.UpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsLeaveRequestOwner]

    def perform_update(self, serializer):
        serializer.save(status="approved")


class LeaveRequestRejectView(generics.UpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsLeaveRequestOwner]

    def perform_update(self, serializer):
        serializer.save(status="rejected")


class LeaveRequestCancelView(generics.UpdateAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsLeaveRequestOwner]

    def perform_update(self, serializer):
        serializer.save(status="cancelled")
