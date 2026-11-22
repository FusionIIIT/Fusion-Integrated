from decimal import Decimal
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.pms.api.permissions import HasPmsPermission
from modules.pms.api.serializers import (
    CoInventorSerializer,
    InternalReviewSerializer,
    MaintenanceRenewalSerializer,
    OfficeActionSerializer,
    PatentApplicationSerializer,
    PatentBudgetSerializer,
    PatentFinancialTransactionSerializer,
)
from modules.pms.domain.state_machine import IllegalTransitionError
from modules.pms.domain.validation import ValidationError
from modules.pms.models.application import PatentApplication
from modules.pms.selectors.applications import list_applications
from modules.pms.selectors.finance import list_transactions_for_application
from modules.pms.selectors.reporting import get_pms_summary_statistics
from modules.pms.selectors.scoping import get_application_scoped
from modules.pms.services.applications import (
    create_draft,
    submit_application,
    withdraw_application,
)
from modules.pms.services.attorney import (
    assign_attorney,
    respond_assignment,
)
from modules.pms.services.budget import review_budget
from modules.pms.services.filing import (
    record_external_filing,
    record_grant,
)
from modules.pms.services.finance import record_transaction
from modules.pms.services.inventors import sign_agreement, update_inventors
from modules.pms.services.maintenance import record_maintenance_decision
from modules.pms.services.office_actions import (
    record_office_action,
    submit_office_action_response,
)
from modules.pms.services.reviews import (
    assign_director,
    file_appeal,
    submit_review,
)


def _get_user_info(request: Request) -> tuple[int, list[str]]:
    """Helper to extract user_id and active roles from request context."""
    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None) or int(request.headers.get("X-User-Id", 101))
    roles_header = request.headers.get("X-User-Roles", "student")
    roles = [r.strip() for r in roles_header.split(",") if r.strip()]
    return user_id, roles


class ApplicationListCreateView(APIView):
    permission_classes = [HasPmsPermission]

    def get(self, request: Request) -> Response:
        user_id, roles = _get_user_info(request)
        qs = list_applications(
            user_id=user_id,
            roles=roles,
            status=request.query_params.get("status"),
            filing_type=request.query_params.get("filing_type"),
            search=request.query_params.get("search"),
        )
        serializer = PatentApplicationSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        user_id, _ = _get_user_info(request)
        data = request.data
        try:
            app = create_draft(
                applicant_user_id=user_id,
                title=data.get("title", ""),
                abstract=data.get("abstract", ""),
                detailed_description=data.get("detailed_description", ""),
                claims=data.get("claims", ""),
                field_of_invention=data.get("field_of_invention", ""),
                filing_type=data.get("filing_type", "provisional"),
                inventors=data.get("inventors"),
            )
            serializer = PatentApplicationSerializer(app)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(APIView):
    permission_classes = [HasPmsPermission]

    def get(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        app = get_application_scoped(pk, user_id, roles)
        serializer = PatentApplicationSerializer(app)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApplicationSubmitView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        try:
            app = submit_application(pk, user_id, roles)
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class ApplicationWithdrawView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        reason = request.data.get("reason", "")
        try:
            app = withdraw_application(pk, user_id, roles, reason)
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class AssignDirectorView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        director_id = int(request.data.get("director_id", 0))
        try:
            app = assign_director(pk, user_id, director_id, roles)
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class ReviewSubmitView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        data = request.data
        try:
            review = submit_review(
                app_id=pk,
                reviewer_user_id=user_id,
                verdict=data.get("verdict", ""),
                comments=data.get("comments", ""),
                scores=data.get("scores", {}),
                roles=roles,
            )
            return Response(InternalReviewSerializer(review).data, status=status.HTTP_200_OK)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class AppealView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        statement = request.data.get("statement", "")
        try:
            app = file_appeal(pk, user_id, statement, roles)
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except (ValidationError, IllegalTransitionError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BudgetReviewView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        data = request.data
        approved_amt = Decimal(str(data["approved_amount"])) if "approved_amount" in data else None
        budget = review_budget(
            app_id=pk,
            user_id=user_id,
            decision=data.get("decision", "approved"),
            approved_amount=approved_amt,
            roles=roles,
            notes=data.get("notes", ""),
        )
        return Response(PatentBudgetSerializer(budget).data, status=status.HTTP_200_OK)


class AssignAttorneyView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        attorney_id = int(request.data.get("attorney_id", 0))
        try:
            app = assign_attorney(pk, user_id, attorney_id, roles)
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class RespondAttorneyView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        accepted = bool(request.data.get("accepted", True))
        try:
            app = respond_assignment(pk, user_id, accepted, roles, request.data.get("notes", ""))
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class RecordFilingView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        data = request.data
        try:
            app = record_external_filing(
                app_id=pk,
                user_id=user_id,
                official_filing_number=data.get("filing_number", ""),
                filing_date=data.get("filing_date"),
                roles=roles,
            )
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class RecordGrantView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        data = request.data
        try:
            app = record_grant(
                app_id=pk,
                user_id=user_id,
                grant_number=data.get("grant_number", ""),
                grant_date=data.get("grant_date"),
                roles=roles,
            )
            return Response(PatentApplicationSerializer(app).data, status=status.HTTP_200_OK)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class OfficeActionListCreateView(APIView):
    permission_classes = [HasPmsPermission]

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        data = request.data
        try:
            oa = record_office_action(
                app_id=pk,
                attorney_user_id=user_id,
                action_type=data.get("action_type", "fer"),
                issue_date=data.get("issue_date"),
                objections=data.get("objections", ""),
                roles=roles,
            )
            return Response(OfficeActionSerializer(oa).data, status=status.HTTP_201_CREATED)
        except IllegalTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)


class FinancialTransactionListView(APIView):
    permission_classes = [HasPmsPermission]

    def get(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        # Verify access
        get_application_scoped(pk, user_id, roles)
        txns = list_transactions_for_application(pk)
        return Response(PatentFinancialTransactionSerializer(txns, many=True).data, status=status.HTTP_200_OK)

    def post(self, request: Request, pk: int) -> Response:
        user_id, roles = _get_user_info(request)
        data = request.data
        txn = record_transaction(
            app_id=pk,
            user_id=user_id,
            transaction_type=data.get("transaction_type", "filing_fee"),
            amount=Decimal(str(data.get("amount", "0.00"))),
            reference_no=data.get("reference_no", ""),
            roles=roles,
            description=data.get("description", ""),
        )
        return Response(PatentFinancialTransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class SystemSummaryReportView(APIView):
    permission_classes = [HasPmsPermission]

    def get(self, request: Request) -> Response:
        stats = get_pms_summary_statistics()
        return Response(stats, status=status.HTTP_200_OK)
