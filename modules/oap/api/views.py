from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from modules.oap.models import (
    StudentLeave, BonafideRequest, NoDuesRequest, NoDuesAuthorityClearance,
    ThesisSupervisorAssignment, TAAssignment, AssistantshipClaim,
    GraduateSeminarRequest, OAPNotification
)
from modules.oap.api.serializers import (
    StudentLeaveSerializer, BonafideRequestSerializer, NoDuesRequestSerializer,
    NoDuesAuthorityClearanceSerializer, ThesisSupervisorAssignmentSerializer,
    TAAssignmentSerializer, AssistantshipClaimSerializer,
    GraduateSeminarRequestSerializer, OAPNotificationSerializer
)
from modules.oap.services import oap_service

class StudentLeaveViewSet(viewsets.ModelViewSet):
    queryset = StudentLeave.objects.all()
    serializer_class = StudentLeaveSerializer

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        instance = self.get_object()
        oap_service.decide_student_leave(instance)
        return Response({"status": "Decision made"}, status=status.HTTP_200_OK)

class BonafideRequestViewSet(viewsets.ModelViewSet):
    queryset = BonafideRequest.objects.all()
    serializer_class = BonafideRequestSerializer

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        instance = self.get_object()
        oap_service.decide_bonafide_request(instance)
        return Response({"status": "Decision made"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download_certificate(self, request, pk=None):
        instance = self.get_object()
        if oap_service.can_download_bonafide(instance):
            return Response(oap_service.get_certificate_data(instance), status=status.HTTP_200_OK)
        else:
            return Response({"error": "Cannot download certificate"}, status=status.HTTP_403_FORBIDDEN)

class NoDuesRequestViewSet(viewsets.ModelViewSet):
    queryset = NoDuesRequest.objects.all()
    serializer_class = NoDuesRequestSerializer

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        oap_service.initiate_no_dues_clearance()
        return Response({"status": "No Dues Clearance Initiated"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def verify_domain(self, request, pk=None):
        instance = self.get_object()
        oap_service.verify_no_dues_domain(instance)
        return Response({"status": "Domain Verified"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        instance = self.get_object()
        oap_service.finalize_no_dues_clearance(instance)
        return Response({"status": "No Dues Clearance Finalized"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download_certificate(self, request, pk=None):
        instance = self.get_object()
        if oap_service.can_download_no_dues_certificate(instance):
            return Response(oap_service.get_certificate_data(instance), status=status.HTTP_200_OK)
        else:
            return Response({"error": "Cannot download certificate"}, status=status.HTTP_403_FORBIDDEN)

class ThesisSupervisorAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ThesisSupervisorAssignment.objects.all()
    serializer_class = ThesisSupervisorAssignmentSerializer

class TAAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TAAssignment.objects.all()
    serializer_class = TAAssignmentSerializer

class AssistantshipClaimViewSet(viewsets.ModelViewSet):
    queryset = AssistantshipClaim.objects.all()
    serializer_class = AssistantshipClaimSerializer

    @action(detail=True, methods=['post'])
    def verify_supervisor(self, request, pk=None):
        instance = self.get_object()
        oap_service.verify_assistantship_supervisor(instance)
        return Response({"status": "Supervisor Verified"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def review_forward(self, request, pk=None):
        instance = self.get_object()
        oap_service.review_and_forward_assistantship(instance)
        return Response({"status": "Review and Forward Completed"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def decide_hod(self, request, pk=None):
        instance = self.get_object()
        oap_service.decide_assistantship_hod(instance)
        return Response({"status": "HOD Decision Made"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def process_stipend(self, request, pk=None):
        instance = self.get_object()
        oap_service.process_stipend_disbursement(instance)
        return Response({"status": "Stipend Processed"}, status=status.HTTP_200_OK)

class GraduateSeminarRequestViewSet(viewsets.ModelViewSet):
    queryset = GraduateSeminarRequest.objects.all()
    serializer_class = GraduateSeminarRequestSerializer

    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        instance = self.get_object()
        oap_service.schedule_graduate_seminar(instance)
        return Response({"status": "Seminar Scheduled"}, status=status.HTTP_200_OK)

class OAPNotificationViewSet(viewsets.ModelViewSet):
    queryset = OAPNotification.objects.all()
    serializer_class = OAPNotificationSerializer
