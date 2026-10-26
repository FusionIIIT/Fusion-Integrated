from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import LeaveApplication
from .serializers import LeaveApplicationSerializer

class ApplyForLeaveView(generics.CreateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

class ApproveRejectLeaveView(generics.UpdateAPIView):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        if not self.request.user.has_perm('leave_elm.application.approve'):
            return Response({"detail": "You do not have permission to approve/reject leave."}, status=status.HTTP_403_FORBIDDEN)
        
        if not self.request.user.groups.filter(name='Leave Approver').exists():
            return Response({"detail": "You do not have the 'Leave Approver' role."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer.save()
