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

# OAP Permission Definitions
P_PROCEDURE_VIEW = "oap.procedure.view"
P_LEAVE_APPLY = "oap.leave.apply"
P_LEAVE_REVIEW_HOD = "oap.leave.review_hod"
P_BONAFIDE_REQUEST = "oap.bonafide.request"
P_BONAFIDE_DECIDE = "oap.bonafide.decide"
P_NODUES_INITIATE = "oap.nodues.initiate"
P_NODUES_VERIFY_AUTHORITY = "oap.nodues.verify_authority"
P_NODUES_FINALIZE = "oap.nodues.finalize"
P_ASSISTANTSHIP_SUBMIT = "oap.assistantship.submit"
P_ASSISTANTSHIP_VERIFY_SUPERVISOR = "oap.assistantship.verify_supervisor"
P_ASSISTANTSHIP_REVIEW_DEPT = "oap.assistantship.review_dept"
P_ASSISTANTSHIP_DECIDE_HOD = "oap.assistantship.decide_hod"
P_ASSISTANTSHIP_DISBURSE_STIPEND = "oap.assistantship.disburse_stipend"
P_ASSIGNMENT_MANAGE = "oap.assignment.manage"
P_SEMINAR_REQUEST = "oap.seminar.request"
P_SEMINAR_SCHEDULE = "oap.seminar.schedule"
P_SEMINAR_VIEW = "oap.seminar.view"


class StudentLeaveViewSet(viewsets.ModelViewSet):
    queryset = StudentLeave.objects.all()
    serializer_class = StudentLeaveSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "retrieve": "oap.procedure.view",
        "create": "oap.leave.apply",
        "decide": "oap.leave.review_hod",
    }

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        instance = self.get_object()
        oap_service.decide_student_leave(instance)
        return Response({"status": "Decision made"}, status=status.HTTP_200_OK)


class BonafideRequestViewSet(viewsets.ModelViewSet):
    queryset = BonafideRequest.objects.all()
    serializer_class = BonafideRequestSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "retrieve": "oap.procedure.view",
        "create": "oap.bonafide.request",
        "decide": "oap.bonafide.decide",
        "download_certificate": "oap.procedure.view",
    }

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
    required_permissions = {
        "list": "oap.procedure.view",
        "retrieve": "oap.procedure.view",
        "initiate": "oap.nodues.initiate",
        "verify_domain": "oap.nodues.verify_authority",
        "finalize": "oap.nodues.finalize",
        "download_certificate": "oap.procedure.view",
    }

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
    required_permissions = {
        "list": "oap.procedure.view",
        "create": "oap.assignment.manage",
        "update": "oap.assignment.manage",
    }


class TAAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TAAssignment.objects.all()
    serializer_class = TAAssignmentSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "create": "oap.assignment.manage",
        "update": "oap.assignment.manage",
    }


class AssistantshipClaimViewSet(viewsets.ModelViewSet):
    queryset = AssistantshipClaim.objects.all()
    serializer_class = AssistantshipClaimSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "create": "oap.assistantship.submit",
        "verify_supervisor": "oap.assistantship.verify_supervisor",
        "review_forward": "oap.assistantship.review_dept",
        "decide_hod": "oap.assistantship.decide_hod",
        "process_stipend": "oap.assistantship.disburse_stipend",
    }

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
    required_permissions = {
        "list": "oap.seminar.view",
        "retrieve": "oap.seminar.view",
        "create": "oap.seminar.request",
        "schedule": "oap.seminar.schedule",
    }

    @action(detail=True, methods=['post'])
    def schedule(self, request, pk=None):
        instance = self.get_object()
        oap_service.schedule_graduate_seminar(instance)
        return Response({"status": "Seminar Scheduled"}, status=status.HTTP_200_OK)


class OAPNotificationViewSet(viewsets.ModelViewSet):
    queryset = OAPNotification.objects.all()
    serializer_class = OAPNotificationSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "retrieve": "oap.procedure.view",
    }
