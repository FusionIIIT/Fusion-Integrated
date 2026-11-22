"""API Views for RSPC module."""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.rspc.api import serializers as s
from modules.rspc.domain.rules import (
    can_update_project,
    validate_workflow_transition,
)
from modules.rspc.models import (
    ConsultancyProject,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectClosure,
    ProjectStaffAppointment,
    ResearchProposal,
    RSPCAuditTrail,
)

MODULE = HasModuleGrant("rspc")


# --- Research Proposals ---
class ProposalListCreateView(generics.ListCreateAPIView):
    queryset = ResearchProposal.objects.all()
    serializer_class = s.ResearchProposalSerializer
    permission_classes = [MODULE, HasPermission("rspc.proposal.view")]

    def perform_create(self, serializer):
        proposal = serializer.save()
        principal = getattr(self.request, "principal", None)
        actor_id = principal.get("user_id", 0) if isinstance(principal, dict) else 0
        RSPCAuditTrail.objects.create(
            entity_type="proposal",
            entity_id=proposal.id,
            actor_id=actor_id or proposal.pi_id,
            action=proposal.status,
            remarks="Proposal created/submitted",
        )


class ProposalDetailView(generics.RetrieveUpdateAPIView):
    queryset = ResearchProposal.objects.all()
    serializer_class = s.ResearchProposalSerializer
    permission_classes = [MODULE, HasPermission("rspc.proposal.view")]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not can_update_project(instance):
            return Response(
                {"detail": "Cannot update proposal in current archived lifecycle state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)


class ProposalTransitionView(generics.GenericAPIView):
    queryset = ResearchProposal.objects.all()
    serializer_class = s.ResearchProposalSerializer
    permission_classes = [MODULE, HasPermission("rspc.proposal.view")]

    def post(self, request, pk: int):
        try:
            proposal = ResearchProposal.objects.get(pk=pk)
        except ResearchProposal.DoesNotExist:
            return Response({"detail": "Proposal not found."}, status=status.HTTP_404_NOT_FOUND)

        target_status = request.data.get("status")
        remarks = request.data.get("remarks", "")
        if not target_status:
            return Response(
                {"detail": "Target status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not validate_workflow_transition(proposal.status, target_status):
            return Response(
                {"detail": f"Illegal transition from {proposal.status} to {target_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proposal.status = target_status
        proposal.save()

        principal = getattr(request, "principal", None)
        actor_id = principal.get("user_id", 0) if isinstance(principal, dict) else 0
        RSPCAuditTrail.objects.create(
            entity_type="proposal",
            entity_id=proposal.id,
            actor_id=actor_id or proposal.pi_id,
            action=target_status,
            remarks=remarks,
        )

        return Response(s.ResearchProposalSerializer(proposal).data, status=status.HTTP_200_OK)


# --- Consultancy Projects ---
class ConsultancyListCreateView(generics.ListCreateAPIView):
    queryset = ConsultancyProject.objects.all()
    serializer_class = s.ConsultancyProjectSerializer
    permission_classes = [MODULE, HasPermission("rspc.consultancy.view")]

    def perform_create(self, serializer):
        consultancy = serializer.save()
        principal = getattr(self.request, "principal", None)
        actor_id = principal.get("user_id", 0) if isinstance(principal, dict) else 0
        RSPCAuditTrail.objects.create(
            entity_type="consultancy",
            entity_id=consultancy.id,
            actor_id=actor_id or consultancy.pi_id,
            action=consultancy.status,
            remarks="Consultancy project registered",
        )


class ConsultancyDetailView(generics.RetrieveUpdateAPIView):
    queryset = ConsultancyProject.objects.all()
    serializer_class = s.ConsultancyProjectSerializer
    permission_classes = [MODULE, HasPermission("rspc.consultancy.view")]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not can_update_project(instance):
            return Response(
                {"detail": "Cannot update consultancy project in current lifecycle state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)


# --- Staff Appointments ---
class StaffAppointmentListCreateView(generics.ListCreateAPIView):
    queryset = ProjectStaffAppointment.objects.all()
    serializer_class = s.ProjectStaffAppointmentSerializer
    permission_classes = [MODULE, HasPermission("rspc.staff.request")]


class StaffAppointmentDetailView(generics.RetrieveUpdateAPIView):
    queryset = ProjectStaffAppointment.objects.all()
    serializer_class = s.ProjectStaffAppointmentSerializer
    permission_classes = [MODULE, HasPermission("rspc.staff.request")]


# --- Financial Requests ---
class FinancialRequestListCreateView(generics.ListCreateAPIView):
    queryset = FinancialRequest.objects.all()
    serializer_class = s.FinancialRequestSerializer
    permission_classes = [MODULE, HasPermission("rspc.financial.request")]


class FinancialRequestDetailView(generics.RetrieveUpdateAPIView):
    queryset = FinancialRequest.objects.all()
    serializer_class = s.FinancialRequestSerializer
    permission_classes = [MODULE, HasPermission("rspc.financial.request")]


# --- Procurement Requests ---
class ProcurementRequestListCreateView(generics.ListCreateAPIView):
    queryset = ProcurementRequest.objects.all()
    serializer_class = s.ProcurementRequestSerializer
    permission_classes = [MODULE, HasPermission("rspc.procurement.request")]


class ProcurementRequestDetailView(generics.RetrieveUpdateAPIView):
    queryset = ProcurementRequest.objects.all()
    serializer_class = s.ProcurementRequestSerializer
    permission_classes = [MODULE, HasPermission("rspc.procurement.request")]


# --- Progress Reports ---
class ProgressReportListCreateView(generics.ListCreateAPIView):
    queryset = ProgressReport.objects.all()
    serializer_class = s.ProgressReportSerializer
    permission_classes = [MODULE, HasPermission("rspc.report.submit")]


class ProgressReportDetailView(generics.RetrieveAPIView):
    queryset = ProgressReport.objects.all()
    serializer_class = s.ProgressReportSerializer
    permission_classes = [MODULE, HasPermission("rspc.report.submit")]


# --- Project Closure ---
class ProjectClosureListCreateView(generics.ListCreateAPIView):
    queryset = ProjectClosure.objects.all()
    serializer_class = s.ProjectClosureSerializer
    permission_classes = [MODULE, HasPermission("rspc.closure.submit")]


class ProjectClosureDetailView(generics.RetrieveUpdateAPIView):
    queryset = ProjectClosure.objects.all()
    serializer_class = s.ProjectClosureSerializer
    permission_classes = [MODULE, HasPermission("rspc.closure.submit")]


# --- Audit Trails ---
class AuditTrailListView(generics.ListAPIView):
    queryset = RSPCAuditTrail.objects.all()
    serializer_class = s.RSPCAuditTrailSerializer
    permission_classes = [MODULE, HasPermission("rspc.audit.view")]
