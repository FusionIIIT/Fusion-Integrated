"""RSPC API Views.
Delegates all reads to selectors and all writes to services.
Enforces module grant and fine-grained permissions on every endpoint.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.rspc.api import serializers as s
from modules.rspc.domain.errors import RspcDomainError
from modules.rspc.selectors import (
    visible_agency_trackings,
    visible_audit_trails,
    visible_closure_records,
    visible_consultancies,
    visible_consultancy_settlements,
    visible_financial_requests,
    visible_notifications,
    visible_procurement_requests,
    visible_progress_reports,
    visible_projects,
    visible_proposals,
    visible_staff_appointments,
)
from modules.rspc.services import (
    record_agency_tracking,
    record_consultancy_settlement,
    register_consultancy,
    request_staff_appointment,
    submit_financial_request,
    submit_procurement_request,
    submit_progress_report,
    submit_project_closure,
    submit_research_proposal,
    sync_role_assignment,
    transition_consultancy,
    transition_financial_request,
    transition_procurement_request,
    transition_project_closure,
    transition_proposal,
    transition_staff_appointment,
    update_project_lifecycle,
)

MODULE = HasModuleGrant("rspc")


# ---------------------------------------------------------------------------
# Research Proposal Views (UC-002..006, CW-RSPC-01)
# ---------------------------------------------------------------------------
class ProposalListCreateView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("rspc.proposal.create", "rspc.proposal.view_self", "rspc.proposal.view"),
    ]

    @extend_schema(
        summary="List research proposals visible to caller",
        responses={200: s.ResearchProposalSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_proposals(request.principal)
        return Response(s.ResearchProposalSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit a new research proposal",
        request=s.ResearchProposalCreateSerializer,
        responses={201: s.ResearchProposalSerializer},
    )
    def post(self, request):
        serializer = s.ResearchProposalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = submit_research_proposal(
                faculty_user_id=request.principal.user_id,
                principal=request.principal,
                **serializer.validated_data,
            )
            return Response(
                s.ResearchProposalSerializer(proposal).data, status=status.HTTP_201_CREATED
            )
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProposalDetailView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.view_self", "rspc.proposal.view")]

    @extend_schema(
        summary="Retrieve proposal detail", responses={200: s.ResearchProposalSerializer}
    )
    def get(self, request, pk: int):
        proposal = visible_proposals(request.principal).filter(pk=pk).first()
        if not proposal:
            return Response(
                {"error": {"code": "not_found", "message": "Proposal not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(s.ResearchProposalSerializer(proposal).data)


class ProposalRecommendDeptView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.recommend_dept")]

    @extend_schema(
        summary="HoD recommendation on research proposal",
        request=s.TransitionActionSerializer,
        responses={200: s.ResearchProposalSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = transition_proposal(
                proposal_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ResearchProposalSerializer(proposal).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProposalVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.verify")]

    @extend_schema(
        summary="RSPC Admin verification of proposal",
        request=s.TransitionActionSerializer,
        responses={200: s.ResearchProposalSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = transition_proposal(
                proposal_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                is_eligible=serializer.validated_data.get("is_eligible", True),
            )
            return Response(s.ResearchProposalSerializer(proposal).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProposalDeanDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.approve_dean")]

    @extend_schema(
        summary="Dean-RSPC decision on proposal",
        request=s.TransitionActionSerializer,
        responses={200: s.ResearchProposalSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = transition_proposal(
                proposal_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ResearchProposalSerializer(proposal).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProposalDirectorAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.authorize_director")]

    @extend_schema(
        summary="Director authorization for proposal",
        request=s.TransitionActionSerializer,
        responses={200: s.ResearchProposalSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = transition_proposal(
                proposal_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ResearchProposalSerializer(proposal).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# Consultancy Project Views (UC-007, 008, CW-RSPC-02)
# ---------------------------------------------------------------------------
class ConsultancyListCreateView(APIView):
    permission_classes = [
        MODULE,
        HasPermission(
            "rspc.consultancy.create", "rspc.consultancy.view_self", "rspc.consultancy.view"
        ),
    ]

    @extend_schema(
        summary="List registered consultancy projects",
        responses={200: s.ConsultancyProjectSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_consultancies(request.principal)
        return Response(s.ConsultancyProjectSerializer(qs, many=True).data)

    @extend_schema(
        summary="Register a new consultancy project",
        request=s.ConsultancyCreateSerializer,
        responses={201: s.ConsultancyProjectSerializer},
    )
    def post(self, request):
        serializer = s.ConsultancyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consultancy = register_consultancy(
                faculty_user_id=request.principal.user_id,
                principal=request.principal,
                **serializer.validated_data,
            )
            return Response(
                s.ConsultancyProjectSerializer(consultancy).data, status=status.HTTP_201_CREATED
            )
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ConsultancyRecommendDeptView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.consultancy.recommend_dept")]

    @extend_schema(
        summary="HoD recommendation on consultancy",
        request=s.TransitionActionSerializer,
        responses={200: s.ConsultancyProjectSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consultancy = transition_consultancy(
                consultancy_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ConsultancyProjectSerializer(consultancy).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ConsultancyVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.consultancy.verify")]

    @extend_schema(
        summary="RSPC Admin verification of consultancy",
        request=s.TransitionActionSerializer,
        responses={200: s.ConsultancyProjectSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consultancy = transition_consultancy(
                consultancy_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                is_eligible=serializer.validated_data.get("is_eligible", True),
            )
            return Response(s.ConsultancyProjectSerializer(consultancy).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ConsultancyDeanDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.consultancy.approve_dean")]

    @extend_schema(
        summary="Dean-RSPC decision on consultancy",
        request=s.TransitionActionSerializer,
        responses={200: s.ConsultancyProjectSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consultancy = transition_consultancy(
                consultancy_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ConsultancyProjectSerializer(consultancy).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ConsultancyDirectorAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.consultancy.authorize_director")]

    @extend_schema(
        summary="Director authorization for consultancy",
        request=s.TransitionActionSerializer,
        responses={200: s.ConsultancyProjectSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consultancy = transition_consultancy(
                consultancy_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ConsultancyProjectSerializer(consultancy).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ConsultancySettlementView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("rspc.consultancy.view_self", "rspc.consultancy.view"),
    ]

    @extend_schema(
        summary="List consultancy settlements",
        responses={200: s.ConsultancySettlementSerializer(many=True)},
    )
    def get(self, request, pk: int):
        qs = visible_consultancy_settlements(request.principal, consultancy_id=pk)
        return Response(s.ConsultancySettlementSerializer(qs, many=True).data)

    @extend_schema(
        summary="Record consultancy milestone settlement",
        request=s.ConsultancySettlementSerializer,
        responses={201: s.ConsultancySettlementSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.ConsultancySettlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = record_consultancy_settlement(
            consultancy_id=pk,
            principal=request.principal,
            **serializer.validated_data,
        )
        return Response(
            s.ConsultancySettlementSerializer(settlement).data, status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------------------------
# Project Portfolio Views (UC-001, UC-021)
# ---------------------------------------------------------------------------
class ProjectPortfolioListView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.project.view_self", "rspc.project.view")]

    @extend_schema(
        summary="List RSPC project portfolio", responses={200: s.RSPCProjectSerializer(many=True)}
    )
    def get(self, request):
        qs = visible_projects(request.principal)
        return Response(s.RSPCProjectSerializer(qs, many=True).data)


class ProjectDetailView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.project.view_self", "rspc.project.view")]

    @extend_schema(summary="Retrieve project details", responses={200: s.RSPCProjectSerializer})
    def get(self, request, pk: int):
        project = visible_projects(request.principal).filter(pk=pk).first()
        if not project:
            return Response(
                {"error": {"code": "not_found", "message": "Project not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(s.RSPCProjectSerializer(project).data)


class ProjectUpdateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.project.update")]

    @extend_schema(
        summary="Update project milestones and progress info",
        request=s.ProjectUpdateSerializer,
        responses={200: s.RSPCProjectSerializer},
    )
    def patch(self, request, pk: int):
        serializer = s.ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            project = update_project_lifecycle(
                project_id=pk,
                milestones=serializer.validated_data.get("milestones"),
                progress_info=serializer.validated_data.get("progress_info"),
                principal=request.principal,
            )
            return Response(s.RSPCProjectSerializer(project).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# Project Staff Appointment Views (UC-009, 010, 022, 023, CW-RSPC-03)
# ---------------------------------------------------------------------------
class StaffAppointmentListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.staff.request", "rspc.staff.view")]

    @extend_schema(
        summary="List staff appointment requests",
        responses={200: s.StaffAppointmentRequestSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_staff_appointments(request.principal)
        return Response(s.StaffAppointmentRequestSerializer(qs, many=True).data)

    @extend_schema(
        summary="Request project-based staff appointment",
        request=s.StaffAppointmentCreateSerializer,
        responses={201: s.StaffAppointmentRequestSerializer},
    )
    def post(self, request):
        serializer = s.StaffAppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        project = data.pop("project")
        req = request_staff_appointment(
            project_id=project.id,
            principal=request.principal,
            **data,
        )
        return Response(
            s.StaffAppointmentRequestSerializer(req).data, status=status.HTTP_201_CREATED
        )


class StaffAppointmentVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.staff.verify")]

    @extend_schema(
        summary="RSPC Admin verification of staff appointment",
        request=s.TransitionActionSerializer,
        responses={200: s.StaffAppointmentRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_staff_appointment(
                appointment_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                is_eligible=serializer.validated_data.get("is_eligible", True),
            )
            return Response(s.StaffAppointmentRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class StaffAppointmentRecommendView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.staff.recommend")]

    @extend_schema(
        summary="Record selection participation and recommendation",
        request=s.TransitionActionSerializer,
        responses={200: s.StaffAppointmentRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_staff_appointment(
                appointment_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                recommendation=serializer.validated_data.get("recommendation", ""),
                recommended_candidate_name=serializer.validated_data.get(
                    "recommended_candidate_name", ""
                ),
            )
            return Response(s.StaffAppointmentRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class StaffAppointmentDeanDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.staff.approve_dean")]

    @extend_schema(
        summary="Dean-RSPC decision on staff appointment",
        request=s.TransitionActionSerializer,
        responses={200: s.StaffAppointmentRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_staff_appointment(
                appointment_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.StaffAppointmentRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class StaffAppointmentDirectorAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.staff.authorize_director")]

    @extend_schema(
        summary="Director authorization on staff appointment",
        request=s.TransitionActionSerializer,
        responses={200: s.StaffAppointmentRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_staff_appointment(
                appointment_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.StaffAppointmentRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# Financial & Fund Request Views (UC-011, 012, 024, CW-RSPC-04)
# ---------------------------------------------------------------------------
class FinancialRequestListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.finance.request", "rspc.finance.view")]

    @extend_schema(
        summary="List financial requests", responses={200: s.FinancialRequestSerializer(many=True)}
    )
    def get(self, request):
        qs = visible_financial_requests(request.principal)
        return Response(s.FinancialRequestSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit fund utilization or expenditure request",
        request=s.FinancialRequestCreateSerializer,
        responses={201: s.FinancialRequestSerializer},
    )
    def post(self, request):
        serializer = s.FinancialRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        project = data.pop("project")
        try:
            req = submit_financial_request(
                project_id=project.id,
                principal=request.principal,
                **data,
            )
            return Response(s.FinancialRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class FinancialRequestVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.finance.verify")]

    @extend_schema(
        summary="RSPC Admin verification of financial request",
        request=s.TransitionActionSerializer,
        responses={200: s.FinancialRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_financial_request(
                request_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                is_eligible=serializer.validated_data.get("is_eligible", True),
            )
            return Response(s.FinancialRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class FinancialRequestDeanDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.finance.approve_dean")]

    @extend_schema(
        summary="Dean-RSPC approval of financial request",
        request=s.TransitionActionSerializer,
        responses={200: s.FinancialRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_financial_request(
                request_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.FinancialRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class FinancialRequestDirectorAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.finance.authorize_director")]

    @extend_schema(
        summary="Director authorization of financial request",
        request=s.TransitionActionSerializer,
        responses={200: s.FinancialRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_financial_request(
                request_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.FinancialRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# Procurement Request Views (UC-013, 025, 026, CW-RSPC-05)
# ---------------------------------------------------------------------------
class ProcurementRequestListCreateView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("rspc.procurement.request", "rspc.procurement.view"),
    ]

    @extend_schema(
        summary="List procurement requests",
        responses={200: s.ProcurementRequestSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_procurement_requests(request.principal)
        return Response(s.ProcurementRequestSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit procurement request",
        request=s.ProcurementRequestCreateSerializer,
        responses={201: s.ProcurementRequestSerializer},
    )
    def post(self, request):
        serializer = s.ProcurementRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        project = data.pop("project")
        try:
            req = submit_procurement_request(
                project_id=project.id,
                principal=request.principal,
                **data,
            )
            return Response(
                s.ProcurementRequestSerializer(req).data, status=status.HTTP_201_CREATED
            )
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProcurementRequestVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.procurement.verify")]

    @extend_schema(
        summary="RSPC Admin verification of procurement",
        request=s.TransitionActionSerializer,
        responses={200: s.ProcurementRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_procurement_request(
                request_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                is_eligible=serializer.validated_data.get("is_eligible", True),
            )
            return Response(s.ProcurementRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProcurementRequestDeanDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.procurement.approve_dean")]

    @extend_schema(
        summary="Dean-RSPC approval of procurement",
        request=s.TransitionActionSerializer,
        responses={200: s.ProcurementRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_procurement_request(
                request_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ProcurementRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProcurementRequestDirectorAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.procurement.authorize_director")]

    @extend_schema(
        summary="Director authorization of procurement",
        request=s.TransitionActionSerializer,
        responses={200: s.ProcurementRequestSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = transition_procurement_request(
                request_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ProcurementRequestSerializer(req).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# Progress & Utilization Reporting Views (UC-014)
# ---------------------------------------------------------------------------
class ProgressReportListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.report.submit", "rspc.report.view")]

    @extend_schema(
        summary="List progress reports", responses={200: s.ProgressReportSerializer(many=True)}
    )
    def get(self, request):
        qs = visible_progress_reports(request.principal)
        return Response(s.ProgressReportSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit progress/utilization report",
        request=s.ProgressReportCreateSerializer,
        responses={201: s.ProgressReportSerializer},
    )
    def post(self, request):
        serializer = s.ProgressReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        project = data.pop("project")
        rep = submit_progress_report(
            project_id=project.id,
            principal=request.principal,
            **data,
        )
        return Response(s.ProgressReportSerializer(rep).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Project Closure Views (UC-015, 027, 028, CW-RSPC-06)
# ---------------------------------------------------------------------------
class ProjectClosureListCreateView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("rspc.closure.submit", "rspc.closure.approve_dean", "rspc.closure.verify"),
    ]

    @extend_schema(
        summary="List project closure records",
        responses={200: s.ProjectClosureRecordSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_closure_records(request.principal)
        return Response(s.ProjectClosureRecordSerializer(qs, many=True).data)

    @extend_schema(
        summary="Submit project closure record",
        request=s.ProjectClosureCreateSerializer,
        responses={201: s.ProjectClosureRecordSerializer},
    )
    def post(self, request):
        serializer = s.ProjectClosureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        project = data.pop("project")
        try:
            closure = submit_project_closure(
                project_id=project.id,
                principal=request.principal,
                **data,
            )
            return Response(
                s.ProjectClosureRecordSerializer(closure).data, status=status.HTTP_201_CREATED
            )
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProjectClosureVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.closure.verify")]

    @extend_schema(
        summary="RSPC Admin verification of closure",
        request=s.TransitionActionSerializer,
        responses={200: s.ProjectClosureRecordSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            closure = transition_project_closure(
                closure_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
                is_eligible=serializer.validated_data.get("is_eligible", True),
                settlement_verified=serializer.validated_data.get("settlement_verified", True),
                assets_verified=serializer.validated_data.get("assets_verified", True),
            )
            return Response(s.ProjectClosureRecordSerializer(closure).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProjectClosureDeanDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.closure.approve_dean")]

    @extend_schema(
        summary="Dean-RSPC decision on closure",
        request=s.TransitionActionSerializer,
        responses={200: s.ProjectClosureRecordSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            closure = transition_project_closure(
                closure_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ProjectClosureRecordSerializer(closure).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


class ProjectClosureDirectorAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.closure.authorize_director")]

    @extend_schema(
        summary="Director authorization on closure",
        request=s.TransitionActionSerializer,
        responses={200: s.ProjectClosureRecordSerializer},
    )
    def post(self, request, pk: int):
        serializer = s.TransitionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            closure = transition_project_closure(
                closure_id=pk,
                to_status=serializer.validated_data["to_status"],
                principal=request.principal,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.ProjectClosureRecordSerializer(closure).data)
        except RspcDomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )


# ---------------------------------------------------------------------------
# Notifications, Audit & Integrations Views (UC-016, 017, 018, 029, 030)
# ---------------------------------------------------------------------------
class NotificationListView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.notification.view_self")]

    @extend_schema(
        summary="List in-app notifications",
        responses={200: s.RSPCNotificationSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_notifications(request.principal)
        return Response(s.RSPCNotificationSerializer(qs, many=True).data)


class AuditTrailListView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.audit.view")]

    @extend_schema(
        summary="List RSPC audit trail records",
        responses={200: s.RSPCAuditTrailSerializer(many=True)},
    )
    def get(self, request):
        rec_type = request.query_params.get("record_type")
        rec_id = request.query_params.get("record_id")
        qs = visible_audit_trails(
            request.principal, record_type=rec_type, record_id=int(rec_id) if rec_id else None
        )
        return Response(s.RSPCAuditTrailSerializer(qs, many=True).data)


class IntegrationExchangeView(APIView):
    serializer_class = s.IntegrationExchangeSerializer
    permission_classes = [MODULE, HasPermission("rspc.integration.exchange")]

    @extend_schema(
        summary="Exchange integration records with Fusion modules", responses={200: dict}
    )
    def post(self, request):
        source = request.data.get("source_module", "external")
        payload = request.data.get("payload", {})
        return Response(
            {"status": "acknowledged", "source": source, "received_records": len(payload)}
        )


class AgencyTrackingView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.agency.track")]

    @extend_schema(
        summary="List external agency trackings",
        responses={200: s.ExternalAgencyTrackingSerializer(many=True)},
    )
    def get(self, request):
        qs = visible_agency_trackings(request.principal)
        return Response(s.ExternalAgencyTrackingSerializer(qs, many=True).data)

    @extend_schema(
        summary="Record external funding agency update",
        request=s.ExternalAgencyTrackingSerializer,
        responses={201: s.ExternalAgencyTrackingSerializer},
    )
    def post(self, request):
        serializer = s.ExternalAgencyTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tracking = record_agency_tracking(
            principal=request.principal,
            **serializer.validated_data,
        )
        return Response(
            s.ExternalAgencyTrackingSerializer(tracking).data, status=status.HTTP_201_CREATED
        )


class RoleSyncView(APIView):
    serializer_class = s.RSPCRoleSyncSerializer
    permission_classes = [MODULE, HasPermission("rspc.role.sync")]

    @extend_schema(
        summary="Synchronize RSPC role assignment", responses={201: s.RSPCRoleSyncSerializer}
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        new_role = request.data.get("new_role")
        prev_role = request.data.get("previous_role", "")
        mechanism = request.data.get("source_mechanism", "Fusion Role Management")
        if not user_id or not new_role:
            return Response(
                {"error": {"code": "bad_request", "message": "user_id and new_role required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log = sync_role_assignment(
            user_id=int(user_id),
            new_role=str(new_role),
            previous_role=str(prev_role),
            source_mechanism=str(mechanism),
            principal=request.principal,
        )
        return Response(s.RSPCRoleSyncSerializer(log).data, status=status.HTTP_201_CREATED)
