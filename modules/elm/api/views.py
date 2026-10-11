from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import LeaveApplication
from .serializers import LeaveApplicationSerializer

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'UnitHead':
            return self.queryset.all()
        elif self.request.user.role == 'Staff':
            return self.queryset.filter(applicant=self.request.user)
        else:
            return self.queryset.none()

    @action(detail=True, methods=['post'])
    def recommend(self, request, pk=None):
        leave_application = self.get_object()
        leave_application.status = 'recommended'
        leave_application.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave_application = self.get_object()
        leave_application.status = 'approved'
        leave_application.save()
        # Call the deduct_balance function
        leave_application.deduct_balance()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave_application = self.get_object()
        leave_application.status = 'rejected'
        leave_application.save()
        return Response(status=status.HTTP_200_OK)