from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from modules.oap.models import (
    OAPAuditTrail, StudentLeave, BonafideRequest, NoDuesRequest, NoDuesAuthorityClearance,
    ThesisSupervisorAssignment, TAAssignment, AssistantshipClaim,
    GraduateSeminarRequest, OAPNotification
)
from modules.oap.api.serializers import (
    OAPAuditTrailSerializer, StudentLeaveSerializer, BonafideRequestSerializer, NoDuesRequestSerializer,
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
        decision = request.data.get('decision', 'APPROVED')
        remarks = request.data.get('remarks')
        hod_user_id = request.data.get('hod_user_id', request.user.id if hasattr(request, 'user') else 1)
        res = oap_service.decide_student_leave(instance.id, hod_user_id, decision, remarks)
        return Response({"status": f"Decision made: {res.status}"}, status=status.HTTP_200_OK)


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
        decision = request.data.get('decision', 'APPROVED')
        remarks = request.data.get('remarks')
        admin_user_id = request.data.get('admin_user_id', request.user.id if hasattr(request, 'user') else 1)
        res = oap_service.decide_bonafide_request(instance.id, admin_user_id, decision, remarks)
        return Response({"status": f"Decision made: {res.status}", "certificate_number": res.certificate_number}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download_certificate(self, request, pk=None):
        instance = self.get_object()
        if oap_service.can_download_bonafide(instance.id):
            return Response(oap_service.get_certificate_data(instance), status=status.HTTP_200_OK)
        else:
            return Response({"error": "Cannot download certificate: not approved or expired."}, status=status.HTTP_403_FORBIDDEN)


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
        student_id = request.data.get('student_user_id', request.user.id if hasattr(request, 'user') else 1)
        program = request.data.get('program', 'UG')
        department = request.data.get('department', 'CSE')
        req = oap_service.initiate_no_dues_clearance(student_id, program, department)
        return Response(NoDuesRequestSerializer(req).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def verify_domain(self, request, pk=None):
        instance = self.get_object()
        domain = request.data.get('domain')
        status_val = request.data.get('status', 'CLEARED')
        dues_amount = Decimal(str(request.data.get('dues_amount', '0.00')))
        fine_details = request.data.get('fine_details')
        receipt_ref = request.data.get('receipt_reference')
        remarks = request.data.get('remarks')
        verifier_role = request.data.get('verifier_role')
        verifier_id = request.data.get('verifier_user_id', request.user.id if hasattr(request, 'user') else 1)
        clearance = oap_service.verify_no_dues_domain(
            instance.id, domain, verifier_id, status_val,
            verifier_role=verifier_role, dues_amount=dues_amount,
            fine_details=fine_details, receipt_reference=receipt_ref, remarks=remarks
        )
        return Response(NoDuesAuthorityClearanceSerializer(clearance).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        instance = self.get_object()
        admin_id = request.data.get('admin_user_id', request.user.id if hasattr(request, 'user') else 1)
        remarks = request.data.get('remarks')
        finalized = oap_service.finalize_no_dues_clearance(instance.id, admin_id, remarks)
        return Response(NoDuesRequestSerializer(finalized).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download_certificate(self, request, pk=None):
        instance = self.get_object()
        if oap_service.can_download_no_dues_certificate(instance.id):
            return Response(oap_service.get_certificate_data(instance), status=status.HTTP_200_OK)
        else:
            return Response({"error": "Cannot download certificate: clearance not finalized."}, status=status.HTTP_403_FORBIDDEN)


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
        role = request.data.get('supervisor_role', 'THESIS')
        supervisor_id = request.data.get('supervisor_user_id', 1)
        remarks = request.data.get('remarks')
        updated = oap_service.verify_assistantship_supervisor(instance.id, role, supervisor_id, remarks)
        return Response(AssistantshipClaimSerializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def review_forward(self, request, pk=None):
        instance = self.get_object()
        admin_id = request.data.get('dept_admin_user_id', 1)
        remarks = request.data.get('remarks')
        updated = oap_service.review_and_forward_assistantship(instance.id, admin_id, remarks)
        return Response(AssistantshipClaimSerializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def decide_hod(self, request, pk=None):
        instance = self.get_object()
        decision = request.data.get('decision', 'APPROVED')
        hod_id = request.data.get('hod_user_id', 1)
        remarks = request.data.get('remarks')
        updated = oap_service.decide_assistantship_hod(instance.id, hod_id, decision, remarks)
        return Response(AssistantshipClaimSerializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def process_stipend(self, request, pk=None):
        instance = self.get_object()
        admin_id = request.data.get('admin_user_id', 1)
        ref = request.data.get('disbursement_reference', 'STIPEND-REF-001')
        updated = oap_service.process_stipend_disbursement(instance.id, admin_id, ref)
        return Response(AssistantshipClaimSerializer(updated).data, status=status.HTTP_200_OK)


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
        admin_id = request.data.get('dept_admin_user_id', 1)
        date = request.data.get('scheduled_date')
        time = request.data.get('scheduled_time')
        venue = request.data.get('venue')
        res = oap_service.schedule_graduate_seminar(instance.id, admin_id, date, time, venue)
        return Response(GraduateSeminarRequestSerializer(res).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        instance = self.get_object()
        faculty_id = request.data.get('faculty_user_id', 1)
        result = request.data.get('result', 'SATISFACTORY')
        remarks = request.data.get('remarks')
        res = oap_service.evaluate_graduate_seminar(instance.id, faculty_id, result, remarks)
        return Response(GraduateSeminarRequestSerializer(res).data, status=status.HTTP_200_OK)


class OAPNotificationViewSet(viewsets.ModelViewSet):
    queryset = OAPNotification.objects.all()
    serializer_class = OAPNotificationSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "retrieve": "oap.procedure.view",
    }


class OAPAuditTrailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OAPAuditTrail.objects.all()
    serializer_class = OAPAuditTrailSerializer
    required_permissions = {
        "list": "oap.procedure.view",
        "retrieve": "oap.procedure.view",
    }
