from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models.leave import LeaveApplication, LeaveStatusMaster
from .serializers import LeaveApplicationSerializer

class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', '') == 'UnitHead' or user.is_staff:
            return self.queryset.all()
        return self.queryset.filter(applicant=user)

    @action(detail=True, methods=['post'])
    def recommend(self, request, pk=None):
        application = self.get_object()
        status_rec, _ = LeaveStatusMaster.objects.get_or_create(status_code='RECOMMENDED')
        application.status = status_rec
        application.reviewer_comments = request.data.get('remarks', 'Recommended by Unit Head')
        application.save()
        return Response({'message': 'Application recommended successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        application = self.get_object()
        status_app, _ = LeaveStatusMaster.objects.get_or_create(status_code='APPROVED')
        application.status = status_app
        application.reviewer_comments = request.data.get('remarks', 'Approved by Sanctioning Authority')
        application.save()
        return Response({'message': 'Application approved successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        application = self.get_object()
        status_rej, _ = LeaveStatusMaster.objects.get_or_create(status_code='REJECTED')
        application.status = status_rej
        application.reviewer_comments = request.data.get('remarks', 'Rejected')
        application.save()
        return Response({'message': 'Application rejected'}, status=status.HTTP_200_OK)