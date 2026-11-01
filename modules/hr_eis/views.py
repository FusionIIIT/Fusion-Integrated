# modules/hr_eis/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import EmployeeProfile, WorkExperience
from .serializers import EmployeeProfileSerializer, WorkExperienceSerializer


class EmployeeProfileViewSet(viewsets.ModelViewSet):
    queryset = EmployeeProfile.objects.all()
    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return EmployeeProfile.objects.all()
        return EmployeeProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='me')
    def my_profile(self, request):
        try:
            profile = EmployeeProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except EmployeeProfile.DoesNotExist:
            return Response({"detail": "Profile not found for logged in user."}, status=status.HTTP_404_NOT_FOUND)


class WorkExperienceViewSet(viewsets.ModelViewSet):
    queryset = WorkExperience.objects.all()
    serializer_class = WorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkExperience.objects.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        profile = EmployeeProfile.objects.get(user=self.request.user)
        serializer.save(employee=profile)