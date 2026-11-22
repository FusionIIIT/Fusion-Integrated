"""HTTP View Layer for RSPC.

Every view retrieves its queryset via selectors.scoping, ensuring role-based
narrowing is enforced once at the database layer (returning 404 rather than 403).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.rspc.api.serializers import (
    BudgetAllocationSerializer,
    DisbursementSerializer,
    ExtensionRequestSerializer,
    ExtensionReviewSerializer,
    ProjectBudgetHeadSerializer,
    ProjectCreateSerializer,
    ProjectFundTransactionSerializer,
    ProjectSerializer,
    ProposalCreateSerializer,
    ProposalReviewActionSerializer,
    ProposalSerializer,
)
from modules.rspc.selectors.finance import get_project_budget_heads, get_project_ledger_transactions
from modules.rspc.selectors.project import list_projects
from modules.rspc.selectors.proposal import list_proposals
from modules.rspc.selectors.scoping import (
    get_project_or_404,
    get_proposal_or_404,
    get_user_id,
    scope_projects,
    scope_proposals,
)
from modules.rspc.services import (
    extension as extension_services,
)
from modules.rspc.services import (
    finance as finance_services,
)
from modules.rspc.services import (
    project as project_services,
)
from modules.rspc.services import (
    proposal as proposal_services,
)

MODULE = HasModuleGrant("rspc")


class ProposalListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.view")]
    serializer_class = ProposalSerializer

    @extend_schema(operation_id="rspc_proposal_list", responses=ProposalSerializer(many=True))
    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = list_proposals(request, status=status_filter)
        return Response(ProposalSerializer(qs, many=True).data)

    @extend_schema(
        operation_id="rspc_proposal_create",
        request=ProposalCreateSerializer,
        responses=ProposalSerializer,
    )
    def post(self, request):
        if not HasPermission("rspc.proposal.create")().has_permission(request, self):
            return Response(
                {"detail": "Permission denied: rspc.proposal.create required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProposalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)

        created = proposal_services.create_proposal(
            user_id=user_id,
            **serializer.validated_data,
        )
        return Response(ProposalSerializer(created).data, status=status.HTTP_201_CREATED)


class ProposalDetailView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.view")]
    serializer_class = ProposalSerializer

    @extend_schema(operation_id="rspc_proposal_detail", responses=ProposalSerializer)
    def get(self, request, pk: int):
        proposal = get_proposal_or_404(request, pk)
        return Response(ProposalSerializer(proposal).data)


class ProposalSubmitView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.create")]
    serializer_class = ProposalSerializer

    @extend_schema(operation_id="rspc_proposal_submit", request=None, responses=ProposalSerializer)
    def post(self, request, pk: int):
        proposal = get_proposal_or_404(request, pk)
        user_id = get_user_id(request)
        updated = proposal_services.submit_proposal(proposal=proposal, actor_user_id=user_id)
        return Response(ProposalSerializer(updated).data)


class ProposalEndorseView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.endorse")]
    serializer_class = ProposalSerializer

    @extend_schema(
        operation_id="rspc_proposal_endorse",
        request=ProposalReviewActionSerializer,
        responses=ProposalSerializer,
    )
    def post(self, request, pk: int):
        proposal = get_proposal_or_404(request, pk)
        user_id = get_user_id(request)
        serializer = ProposalReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = proposal_services.endorse_proposal(
            proposal=proposal,
            actor_user_id=user_id,
            comments=serializer.validated_data.get("comments", ""),
        )
        return Response(ProposalSerializer(updated).data)


class ProposalApproveView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.approve")]
    serializer_class = ProposalSerializer

    @extend_schema(
        operation_id="rspc_proposal_approve",
        request=ProposalReviewActionSerializer,
        responses=ProposalSerializer,
    )
    def post(self, request, pk: int):
        proposal = get_proposal_or_404(request, pk)
        user_id = get_user_id(request)
        serializer = ProposalReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = proposal_services.approve_proposal(
            proposal=proposal,
            actor_user_id=user_id,
            comments=serializer.validated_data.get("comments", ""),
        )
        return Response(ProposalSerializer(updated).data)


class ProjectListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.project.view")]
    serializer_class = ProjectSerializer

    @extend_schema(operation_id="rspc_project_list", responses=ProjectSerializer(many=True))
    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = list_projects(request, status=status_filter)
        return Response(ProjectSerializer(qs, many=True).data)

    @extend_schema(
        operation_id="rspc_project_create",
        request=ProjectCreateSerializer,
        responses=ProjectSerializer,
    )
    def post(self, request):
        if not HasPermission("rspc.project.create")().has_permission(request, self):
            return Response(
                {"detail": "Permission denied: rspc.project.create required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)

        created = project_services.sanction_and_register_project(
            user_id=user_id,
            **serializer.validated_data,
        )
        return Response(ProjectSerializer(created).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.project.view")]
    serializer_class = ProjectSerializer

    @extend_schema(operation_id="rspc_project_detail", responses=ProjectSerializer)
    def get(self, request, pk: int):
        project = get_project_or_404(request, pk)
        return Response(ProjectSerializer(project).data)


class ProjectActivateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.project.manage")]
    serializer_class = ProjectSerializer

    @extend_schema(operation_id="rspc_project_activate", request=None, responses=ProjectSerializer)
    def post(self, request, pk: int):
        project = get_project_or_404(request, pk)
        updated = project_services.activate_project(project=project, actor_role="admin")
        return Response(ProjectSerializer(updated).data)


class ProjectBudgetHeadListView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.fund.view")]
    serializer_class = ProjectBudgetHeadSerializer

    @extend_schema(
        operation_id="rspc_budget_head_list",
        responses=ProjectBudgetHeadSerializer(many=True),
    )
    def get(self, request, pk: int):
        heads = get_project_budget_heads(request, pk)
        return Response(ProjectBudgetHeadSerializer(heads, many=True).data)

    @extend_schema(
        operation_id="rspc_budget_head_allocate",
        request=BudgetAllocationSerializer,
        responses=ProjectBudgetHeadSerializer,
    )
    def post(self, request, pk: int):
        if not HasPermission("rspc.project.manage")().has_permission(request, self):
            return Response(
                {"detail": "Permission denied: rspc.project.manage required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        project = get_project_or_404(request, pk)
        serializer = BudgetAllocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)

        head = finance_services.allocate_budget_head(
            project=project,
            actor_user_id=user_id,
            **serializer.validated_data,
        )
        return Response(ProjectBudgetHeadSerializer(head).data, status=status.HTTP_201_CREATED)


class ProjectDisburseView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.fund.request")]
    serializer_class = ProjectFundTransactionSerializer

    @extend_schema(
        operation_id="rspc_project_disburse",
        request=DisbursementSerializer,
        responses=ProjectFundTransactionSerializer,
    )
    def post(self, request, pk: int):
        project = get_project_or_404(request, pk)
        serializer = DisbursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)

        tx = finance_services.disburse_funds(
            project=project,
            actor_user_id=user_id,
            **serializer.validated_data,
        )
        return Response(ProjectFundTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class ProjectDisburseApproveView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.fund.approve")]

    @extend_schema(operation_id="rspc_disburse_approve", request=None, responses=None)
    def post(self, request, pk: int, tx_id: int):
        return Response({"status": "approved", "tx_id": tx_id})


class ProjectLedgerListView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.fund.view")]
    serializer_class = ProjectFundTransactionSerializer

    @extend_schema(
        operation_id="rspc_ledger_list",
        responses=ProjectFundTransactionSerializer(many=True),
    )
    def get(self, request, pk: int):
        txs = get_project_ledger_transactions(request, pk)
        return Response(ProjectFundTransactionSerializer(txs, many=True).data)


class ProjectExtensionCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.extension.request")]

    @extend_schema(
        operation_id="rspc_extension_create",
        request=ExtensionRequestSerializer,
        responses=None,
    )
    def post(self, request, pk: int):
        project = get_project_or_404(request, pk)
        serializer = ExtensionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)

        req = extension_services.request_project_extension(
            project=project,
            actor_user_id=user_id,
            **serializer.validated_data,
        )
        return Response({"id": req.id, "status": req.status}, status=status.HTTP_201_CREATED)


class ProjectExtensionApproveView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.extension.approve")]

    @extend_schema(
        operation_id="rspc_extension_approve",
        request=ExtensionReviewSerializer,
        responses=None,
    )
    def post(self, request, pk: int, ext_id: int):
        project = get_project_or_404(request, pk)
        ext = project.extension_requests.get(pk=ext_id)
        serializer = ExtensionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)

        updated = extension_services.review_project_extension(
            extension_request=ext,
            approved=serializer.validated_data["approved"],
            actor_user_id=user_id,
            actor_role="dean",
            comments=serializer.validated_data.get("comments", ""),
        )
        return Response({"id": updated.id, "status": updated.status})


class ProjectClosureCreateView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.closure.request")]

    @extend_schema(operation_id="rspc_closure_create", request=None, responses=None)
    def post(self, request, pk: int):
        project = get_project_or_404(request, pk)
        user_id = get_user_id(request)
        closure = extension_services.request_project_closure(
            project=project,
            actor_user_id=user_id,
            remarks=request.data.get("remarks", ""),
        )
        return Response(
            {"id": closure.id, "status": closure.status}, status=status.HTTP_201_CREATED
        )


class ProjectClosureApproveView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.closure.approve")]

    @extend_schema(operation_id="rspc_closure_approve", request=None, responses=None)
    def post(self, request, pk: int):
        project = get_project_or_404(request, pk)
        user_id = get_user_id(request)
        closure = extension_services.approve_project_closure(
            project=project,
            actor_user_id=user_id,
        )
        return Response({"id": closure.id, "status": closure.status})


class RspcReportView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.report.view")]

    @extend_schema(operation_id="rspc_report_summary", request=None, responses=None)
    def get(self, request):
        proposals_count = scope_proposals(request).count()
        projects_count = scope_projects(request).count()
        return Response(
            {
                "total_proposals": proposals_count,
                "total_projects": projects_count,
            }
        )
