"""API Views for Patent Management System.

Every view enforces:
- HasModuleGrant("pms")
- HasPermission(...)
- Row-level scoping via selectors to guarantee zero horizontal privilege escalation.
- Domain services for all state changes, transitions and audit records.
"""

from __future__ import annotations

from typing import Any

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.pms.api import serializers as s
from modules.pms.domain.exceptions import (
    ActorNotAllowedError,
    ConflictOfInterestError,
    DeadlineExpiredError,
    DomainRuleError,
    InvalidTransitionError,
    ValidationError,
)
from modules.pms.models import (
    AttorneyAssignment,
    LicensingRequest,
    MaintenanceSchedule,
    OfficeAction,
    OfficeActionResponse,
    PatentAppeal,
    PriorArtSearchRecord,
)
from modules.pms.selectors import scoping
from modules.pms.selectors.applications import get_application_or_404, list_applications_for_actor
from modules.pms.selectors.attorneys import (
    get_attorney_assignments_for_actor,
    list_attorney_panel,
)
from modules.pms.selectors.reports import get_portfolio_summary_stats
from modules.pms.services import (
    applications as app_service,
)
from modules.pms.services import (
    attorneys as attorney_service,
)
from modules.pms.services import (
    budget as budget_service,
)
from modules.pms.services import (
    documents as doc_service,
)
from modules.pms.services import (
    filings as filing_service,
)
from modules.pms.services import (
    licensing_appeals as appeal_service,
)
from modules.pms.services import (
    maintenance as maint_service,
)
from modules.pms.services import (
    office_actions as oa_service,
)
from modules.pms.services import (
    reviews as review_service,
)

MODULE = HasModuleGrant("pms")

DOMAIN_EXCEPTIONS = (
    ValidationError,
    ConflictOfInterestError,
    DeadlineExpiredError,
    InvalidTransitionError,
    ActorNotAllowedError,
    DomainRuleError,
)


def _actor(request: Any) -> Any:
    return getattr(request, "principal", None) or getattr(request, "user", None)


def _actor_id(request: Any) -> int:
    return scoping.get_actor_user_id(_actor(request))


def _handle_domain_error(e: DomainRuleError) -> Response:
    if isinstance(e, ValidationError):
        return Response(
            {"detail": str(e), "rule_id": getattr(e, "rule_id", None)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(e, (ConflictOfInterestError, DeadlineExpiredError, InvalidTransitionError)):
        return Response(
            {"detail": str(e), "error": type(e).__name__},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(e, ActorNotAllowedError):
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Application Endpoints ---


class ApplicationListView(APIView):
    """GET /api/v1/pms/applications - List scoped patent applications.
    POST /api/v1/pms/applications - Submit new patent application.
    """

    permission_classes = [MODULE, HasPermission("pms.application.view")]

    def get(self, request: Any) -> Response:
        actor = _actor(request)
        apps = list_applications_for_actor(
            actor=actor,
            status=request.query_params.get("status"),
            domain=request.query_params.get("domain"),
            search=request.query_params.get("search"),
        )
        serializer = s.PatentApplicationListSerializer(apps, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})

    def post(self, request: Any) -> Response:
        if not scoping.has_permission(_actor(request), "pms.application.create"):
            return Response(
                {"detail": "Permission 'pms.application.create' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = s.SubmitApplicationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            app = app_service.submit_patent_application(
                user_id=_actor_id(request),
                title=data["title"],
                abstract=data["abstract"],
                description=data["description"],
                claims=data["claims"],
                domain=data["domain"],
                keywords=data.get("keywords", ""),
                inventors_data=data.get("inventors"),
            )
            return Response(
                s.PatentApplicationDetailSerializer(app).data,
                status=status.HTTP_201_CREATED,
            )
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class ApplicationDetailView(APIView):
    """GET /api/v1/pms/applications/<pk> - Get application details.
    PATCH /api/v1/pms/applications/<pk> - Update / revise draft application.
    """

    permission_classes = [MODULE, HasPermission("pms.application.view")]

    def get(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        return Response(s.PatentApplicationDetailSerializer(app).data)

    def patch(self, request: Any, pk: int) -> Response:
        if not scoping.has_permission(_actor(request), "pms.application.update"):
            return Response(
                {"detail": "Permission 'pms.application.update' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        app = get_application_or_404(_actor(request), pk)
        serializer = s.ReviseApplicationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated_app = app_service.revise_and_resubmit_application(
                application=app,
                user_id=_actor_id(request),
                title=data.get("title"),
                abstract=data.get("abstract"),
                description=data.get("description"),
                claims=data.get("claims"),
                domain=data.get("domain"),
                keywords=data.get("keywords"),
                revision_notes=data.get("revision_notes", ""),
            )
            return Response(s.PatentApplicationDetailSerializer(updated_app).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class ApplicationResubmitView(APIView):
    """POST /api/v1/pms/applications/<pk>/resubmit - Resubmit revised application."""

    permission_classes = [MODULE, HasPermission("pms.application.update")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.ReviseApplicationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated_app = app_service.revise_and_resubmit_application(
                application=app,
                user_id=_actor_id(request),
                title=data.get("title"),
                abstract=data.get("abstract"),
                description=data.get("description"),
                claims=data.get("claims"),
                domain=data.get("domain"),
                keywords=data.get("keywords"),
                revision_notes=data.get("revision_notes", ""),
            )
            return Response(s.PatentApplicationDetailSerializer(updated_app).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class ApplicationWithdrawView(APIView):
    """POST /api/v1/pms/applications/<pk>/withdraw - Withdraw pre-filing patent application."""

    permission_classes = [MODULE, HasPermission("pms.application.delete")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.WithdrawApplicationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            withdrawn_app = app_service.withdraw_patent_application(
                application=app,
                user_id=_actor_id(request),
                reason=serializer.validated_data["reason"],
            )
            return Response(s.PatentApplicationDetailSerializer(withdrawn_app).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class ApplicationHistoryView(APIView):
    """GET /api/v1/pms/applications/<pk>/history - Audit trail timeline."""

    permission_classes = [MODULE, HasPermission("pms.application.view")]

    def get(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        logs = scoping.scoped_audit_logs(_actor(request), application=app)
        serializer = s.PatentAuditLogSerializer(logs, many=True)
        return Response({"results": serializer.data})


# --- Reviews & Director Endpoints ---


class AssignDirectorView(APIView):
    """POST /api/v1/pms/applications/<pk>/assign-director - PCC Admin assigns Director."""

    permission_classes = [MODULE, HasPermission("pms.application.assign")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.AssignDirectorInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = review_service.assign_director_to_application(
                application=app,
                director_user_id=serializer.validated_data["director_user_id"],
                assigned_by_user_id=_actor_id(request),
            )
            return Response(s.DirectorAssignmentSerializer(assignment).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class DirectorReviewView(APIView):
    """POST /api/v1/pms/applications/<pk>/review - Director records review outcome."""

    permission_classes = [MODULE, HasPermission("pms.application.review")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.DirectorReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            rev = review_service.record_director_review(
                application=app,
                director_user_id=_actor_id(request),
                decision=data["decision"],
                justification=data["justification"],
            )
            return Response(s.DirectorReviewSerializer(rev).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


# --- Document Upload & Download ---


class ApplicationDocumentListView(APIView):
    """GET /api/v1/pms/applications/<pk>/documents - List documents.
    POST /api/v1/pms/applications/<pk>/documents - Upload document (PDF <=50MB).
    """

    permission_classes = [MODULE, HasPermission("pms.document.view")]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        docs = scoping.scoped_documents(_actor(request), application=app)
        return Response({"results": s.ApplicationDocumentSerializer(docs, many=True).data})

    def post(self, request: Any, pk: int) -> Response:
        if not scoping.has_permission(_actor(request), "pms.document.create"):
            return Response(
                {"detail": "Permission 'pms.document.create' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        app = get_application_or_404(_actor(request), pk)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        doc_type = request.data.get("document_type", "specification")
        sensitivity = request.data.get("sensitivity", "confidential")

        try:
            doc = doc_service.upload_application_document(
                application=app,
                uploaded_file=file_obj,
                document_type=doc_type,
                title=request.data.get("title") or file_obj.name,
                uploaded_by_user_id=_actor_id(request),
                sensitivity=sensitivity,
            )
            return Response(
                s.ApplicationDocumentSerializer(doc).data,
                status=status.HTTP_201_CREATED,
            )
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class DocumentDownloadView(APIView):
    """GET /api/v1/pms/documents/<pk>/download - Secure file download."""

    permission_classes = [MODULE, HasPermission("pms.document.view")]

    def get(self, request: Any, pk: int) -> Any:
        docs = scoping.scoped_documents(_actor(request))
        doc = docs.filter(pk=pk).first()
        if not doc or not doc.file:
            raise Http404("Document not found or access denied.")

        response = FileResponse(
            doc.file.open("rb"), content_type=doc.mime_type or "application/pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="{doc.title}"'
        return response


# --- Attorney Panels & Assignments ---


class AttorneyPanelView(APIView):
    """GET /api/v1/pms/attorney-panel - List active attorney panel.
    POST /api/v1/pms/attorney-panel - Add new attorney to panel.
    """

    permission_classes = [MODULE, HasPermission("pms.attorney_panel.view")]

    def get(self, request: Any) -> Response:
        panel = list_attorney_panel(active_only=True)
        return Response({"results": s.AttorneyPanelSerializer(panel, many=True).data})

    def post(self, request: Any) -> Response:
        if not scoping.has_permission(_actor(request), "pms.attorney_panel.manage"):
            return Response(
                {"detail": "Permission 'pms.attorney_panel.manage' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = s.AttorneyPanelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        return Response(s.AttorneyPanelSerializer(entry).data, status=status.HTTP_201_CREATED)


class AssignAttorneyView(APIView):
    """POST /api/v1/pms/applications/<pk>/assign-attorney - Offer attorney assignment."""

    permission_classes = [MODULE, HasPermission("pms.attorney.assign")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.AssignAttorneyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = attorney_service.assign_attorney_to_application(
                application=app,
                attorney_user_id=serializer.validated_data["attorney_user_id"],
                assigned_by_user_id=_actor_id(request),
            )
            return Response(s.AttorneyAssignmentSerializer(assignment).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class AttorneyAssignmentListView(APIView):
    """GET /api/v1/pms/attorney/assignments - List assignments for current attorney."""

    permission_classes = [MODULE, HasPermission("pms.attorney.review")]

    def get(self, request: Any) -> Response:
        assignments = get_attorney_assignments_for_actor(_actor(request))
        return Response({"results": s.AttorneyAssignmentSerializer(assignments, many=True).data})


class AttorneyAssignmentRespondView(APIView):
    """POST /api/v1/pms/attorney/assignments/<pk>/respond - Accept or decline assignment."""

    permission_classes = [MODULE, HasPermission("pms.attorney.review")]

    def post(self, request: Any, pk: int) -> Response:
        assignment = AttorneyAssignment.objects.filter(pk=pk).first()
        if not assignment:
            raise Http404("Assignment not found.")

        serializer = s.AttorneyRespondInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated = attorney_service.respond_to_attorney_assignment(
                assignment=assignment,
                attorney_user_id=_actor_id(request),
                accept=data["accept"],
                remarks=data.get("remarks", ""),
            )
            return Response(s.AttorneyAssignmentSerializer(updated).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class PatentabilityAssessmentView(APIView):
    """POST /api/v1/pms/applications/<pk>/assessment - Record patentability assessment."""

    permission_classes = [MODULE, HasPermission("pms.attorney.review")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.PatentabilityAssessmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        utility = data.get("utility_analysis") or data.get("industrial_applicability", "")
        prior_art = data.get("prior_art_summary") or data.get("prior_art_findings", "")
        opinion = data.get("opinion_text") or data.get("detailed_opinion", "")

        try:
            assessment = attorney_service.record_patentability_assessment(
                application=app,
                attorney_user_id=_actor_id(request),
                recommendation=data["recommendation"],
                novelty_analysis=data["novelty_analysis"],
                inventive_step_analysis=data["inventive_step_analysis"],
                utility_analysis=utility,
                prior_art_summary=prior_art,
                opinion_text=opinion,
            )
            return Response(s.PatentabilityAssessmentSerializer(assessment).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class PatentLegalAdviceView(APIView):
    """POST /api/v1/pms/applications/<pk>/legal-advice - Record attorney legal advice."""

    permission_classes = [MODULE, HasPermission("pms.attorney.review")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.PatentLegalAdviceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        topic = data.get("topic") or data.get("summary") or data.get("advice_type") or "Advice"

        try:
            advice = attorney_service.record_patent_legal_advice(
                application=app,
                attorney_user_id=_actor_id(request),
                topic=topic,
                advice_text=data["advice_text"],
            )
            return Response(s.PatentLegalAdviceSerializer(advice).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


# --- Budget Management ---


class BudgetView(APIView):
    """GET /api/v1/pms/applications/<pk>/budget - View budget.
    POST /api/v1/pms/applications/<pk>/budget - Create or update budget.
    """

    permission_classes = [MODULE, HasPermission("pms.budget.view")]

    def get(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        if not hasattr(app, "budget") or not app.budget:
            raise Http404("No budget recorded for this application.")
        return Response(s.PatentBudgetSerializer(app.budget).data)

    def post(self, request: Any, pk: int) -> Response:
        if not scoping.has_permission(_actor(request), "pms.budget.manage"):
            return Response(
                {"detail": "Permission 'pms.budget.manage' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        app = get_application_or_404(_actor(request), pk)
        serializer = s.BudgetCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            budget = budget_service.create_or_update_budget(
                application=app,
                filing_fees=data["filing_fees"],
                attorney_fees=data["attorney_fees"],
                administrative_costs=data["administrative_costs"],
                user_id=_actor_id(request),
            )
            return Response(s.PatentBudgetSerializer(budget).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class BudgetDecideView(APIView):
    """POST /api/v1/pms/applications/<pk>/budget/decide - Director decides budget."""

    permission_classes = [MODULE, HasPermission("pms.budget.approve")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.BudgetDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            budget = budget_service.decide_patent_budget(
                application=app,
                director_user_id=_actor_id(request),
                decision=data["decision"],
                justification=data.get("justification", ""),
            )
            return Response(s.PatentBudgetSerializer(budget).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


# --- Filings & Office Actions ---


class ExternalFilingView(APIView):
    """POST /api/v1/pms/applications/<pk>/filing - Record external patent filing."""

    permission_classes = [MODULE, HasPermission("pms.filing.create")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.ExternalFilingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            record = filing_service.record_external_patent_filing(
                application=app,
                attorney_user_id=_actor_id(request),
                jurisdiction=data["jurisdiction"],
                filing_number=data["filing_number"],
                filing_date=data["filing_date"],
                patent_office=data["patent_office"],
                confirmation_details=data["confirmation_details"],
                international_justification=data.get("international_justification", ""),
            )
            return Response(
                s.ExternalFilingRecordSerializer(record).data,
                status=status.HTTP_201_CREATED,
            )
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class OfficeActionListView(APIView):
    """GET /api/v1/pms/office-actions - List office actions.
    POST /api/v1/pms/applications/<pk>/office-actions - Record office action.
    """

    permission_classes = [MODULE, HasPermission("pms.office_action.view")]

    def get(self, request: Any) -> Response:
        oas = scoping.scoped_office_actions(_actor(request))
        return Response({"results": s.OfficeActionSerializer(oas, many=True).data})

    def post(self, request: Any, pk: int) -> Response:
        if not scoping.has_permission(_actor(request), "pms.office_action.create"):
            return Response(
                {"detail": "Permission 'pms.office_action.create' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        app = get_application_or_404(_actor(request), pk)
        serializer = s.OfficeActionCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            oa = oa_service.record_office_action(
                application=app,
                attorney_user_id=_actor_id(request),
                action_number=data["action_number"],
                issue_date=data["issue_date"],
                response_deadline=data["response_deadline"],
                action_type=data["action_type"],
                description=data["description"],
            )
            return Response(s.OfficeActionSerializer(oa).data, status=status.HTTP_201_CREATED)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class OfficeActionResponseView(APIView):
    """POST /api/v1/pms/office-actions/<pk>/response - Prepare draft response."""

    permission_classes = [MODULE, HasPermission("pms.office_action.create")]

    def post(self, request: Any, pk: int) -> Response:
        oa = OfficeAction.objects.filter(pk=pk).first()
        if not oa:
            raise Http404("Office action not found.")

        serializer = s.OfficeActionResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        draft_text = data.get("draft_text") or data.get("response_text", "")
        req_approval = (
            data.get("requires_applicant_approval")
            if "requires_applicant_approval" in data
            else data.get("requires_applicant_review", True)
        )

        try:
            resp = oa_service.prepare_office_action_response(
                office_action=oa,
                attorney_user_id=_actor_id(request),
                draft_text=draft_text,
                requires_applicant_approval=req_approval,
            )
            return Response(s.OfficeActionResponseSerializer(resp).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class OfficeActionApproveView(APIView):
    """POST /api/v1/pms/office-actions/responses/<pk>/approve - Applicant approves response."""

    permission_classes = [MODULE, HasPermission("pms.office_action.approve")]

    def post(self, request: Any, pk: int) -> Response:
        resp = OfficeActionResponse.objects.filter(pk=pk).first()
        if not resp:
            raise Http404("Response not found.")

        try:
            approved = oa_service.approve_office_action_response(
                response=resp,
                applicant_user_id=_actor_id(request),
            )
            return Response(s.OfficeActionResponseSerializer(approved).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class OfficeActionSubmitView(APIView):
    """POST /api/v1/pms/office-actions/responses/<pk>/submit - Submit response to patent office."""

    permission_classes = [MODULE, HasPermission("pms.office_action.update")]

    def post(self, request: Any, pk: int) -> Response:
        resp = OfficeActionResponse.objects.filter(pk=pk).first()
        if not resp:
            raise Http404("Response not found.")

        serializer = s.OfficeActionSubmitInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            submitted = oa_service.submit_office_action_response(
                response=resp,
                attorney_user_id=_actor_id(request),
                submission_details=serializer.validated_data.get("submission_details", ""),
            )
            return Response(s.OfficeActionResponseSerializer(submitted).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class OfficeActionExtensionView(APIView):
    """POST /api/v1/pms/office-actions/<pk>/extension - Request deadline extension."""

    permission_classes = [MODULE, HasPermission("pms.office_action.update")]

    def post(self, request: Any, pk: int) -> Response:
        oa = OfficeAction.objects.filter(pk=pk).first()
        if not oa:
            raise Http404("Office action not found.")

        serializer = s.ExtensionRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ext = oa_service.request_extension(
                office_action=oa,
                requested_by_user_id=_actor_id(request),
                requested_days=data["requested_days"],
                reason=data["reason"],
            )
            return Response(s.ExtensionRequestSerializer(ext).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


# --- Post-Grant Maintenance & Licensing ---


class PostGrantInitView(APIView):
    """POST /api/v1/pms/applications/<pk>/grant - Initialize post-grant patent."""

    permission_classes = [MODULE, HasPermission("pms.maintenance.manage")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.PostGrantInitInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        patent_number = data.get("patent_number") or data.get("grant_number")

        try:
            pg = maint_service.initialize_post_grant_patent(
                application=app,
                patent_number=patent_number,
                grant_date=data["grant_date"],
                attorney_user_id=_actor_id(request),
            )
            return Response(s.PostGrantPatentSerializer(pg).data, status=status.HTTP_201_CREATED)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class MaintenanceScheduleListView(APIView):
    """GET /api/v1/pms/maintenance - List maintenance renewal schedules."""

    permission_classes = [MODULE, HasPermission("pms.maintenance.view")]

    def get(self, request: Any) -> Response:
        schedules = MaintenanceSchedule.objects.select_related("post_grant__application").all()
        return Response({"results": s.MaintenanceScheduleSerializer(schedules, many=True).data})


class MaintenanceRequestDecisionView(APIView):
    """POST /api/v1/pms/maintenance/<pk>/request-decision - Request renewal decision."""

    permission_classes = [MODULE, HasPermission("pms.maintenance.manage")]

    def post(self, request: Any, pk: int) -> Response:
        sched = MaintenanceSchedule.objects.filter(pk=pk).first()
        if not sched:
            raise Http404("Maintenance schedule not found.")

        try:
            updated = maint_service.request_maintenance_renewal_decision(
                schedule=sched,
                attorney_user_id=_actor_id(request),
            )
            return Response(s.MaintenanceScheduleSerializer(updated).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class MaintenanceDecideView(APIView):
    """POST /api/v1/pms/maintenance/<pk>/decide - Director records renewal decision."""

    permission_classes = [MODULE, HasPermission("pms.maintenance.review")]

    def post(self, request: Any, pk: int) -> Response:
        sched = MaintenanceSchedule.objects.filter(pk=pk).first()
        if not sched:
            raise Http404("Maintenance schedule not found.")

        serializer = s.MaintenanceDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            dec = maint_service.record_maintenance_renewal_decision(
                schedule=sched,
                director_user_id=_actor_id(request),
                decision=data["decision"],
                justification=data["justification"],
            )
            return Response(s.MaintenanceScheduleSerializer(dec.schedule).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class MaintenancePaymentView(APIView):
    """POST /api/v1/pms/maintenance/<pk>/pay - Record renewal fee payment."""

    permission_classes = [MODULE, HasPermission("pms.maintenance.manage")]

    def post(self, request: Any, pk: int) -> Response:
        sched = MaintenanceSchedule.objects.filter(pk=pk).first()
        if not sched:
            raise Http404("Maintenance schedule not found.")

        serializer = s.MaintenancePaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated = maint_service.record_maintenance_payment(
                schedule=sched,
                attorney_user_id=_actor_id(request),
                payment_reference=data["payment_reference"],
            )
            return Response(s.MaintenanceScheduleSerializer(updated).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class LicensingRequestListView(APIView):
    """GET /api/v1/pms/licensing - List licensing requests.
    POST /api/v1/pms/applications/<pk>/licensing - Submit licensing request.
    """

    permission_classes = [MODULE, HasPermission("pms.licensing.view")]

    def get(self, request: Any) -> Response:
        reqs = LicensingRequest.objects.select_related("application").all()
        return Response({"results": s.LicensingRequestSerializer(reqs, many=True).data})

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.LicensingRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            req = appeal_service.submit_licensing_request(
                application=app,
                requested_by_user_id=_actor_id(request),
                licensee_name=data["licensee_name"],
                licensee_contact=data["licensee_contact"],
                license_type=data["license_type"],
                proposed_terms=data["proposed_terms"],
                royalty_rate=data.get("royalty_rate"),
                financial_terms=data.get("financial_terms", ""),
            )
            return Response(
                s.LicensingRequestSerializer(req).data,
                status=status.HTTP_201_CREATED,
            )
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class LicensingReviewView(APIView):
    """POST /api/v1/pms/licensing/<pk>/review - Review licensing request."""

    permission_classes = [MODULE, HasPermission("pms.licensing.manage")]

    def post(self, request: Any, pk: int) -> Response:
        req = LicensingRequest.objects.filter(pk=pk).first()
        if not req:
            raise Http404("Licensing request not found.")

        serializer = s.LicensingReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated = appeal_service.review_licensing_request(
                licensing_request=req,
                reviewed_by_user_id=_actor_id(request),
                decision=data["decision"],
                review_notes=data["review_notes"],
            )
            return Response(s.LicensingRequestSerializer(updated).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


# --- Appeals & Prior Art ---


class PatentAppealView(APIView):
    """POST /api/v1/pms/applications/<pk>/appeal - File appeal against rejection."""

    permission_classes = [MODULE, HasPermission("pms.appeal.create")]

    def post(self, request: Any, pk: int) -> Response:
        app = get_application_or_404(_actor(request), pk)
        serializer = s.AppealCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            appeal = appeal_service.file_patent_appeal(
                application=app,
                applicant_user_id=_actor_id(request),
                grounds=data["grounds"],
                justification=data["justification"],
            )
            return Response(s.PatentAppealSerializer(appeal).data, status=status.HTTP_201_CREATED)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class AppealReviewView(APIView):
    """POST /api/v1/pms/appeals/<pk>/review - Director decides appeal."""

    permission_classes = [MODULE, HasPermission("pms.appeal.review")]

    def post(self, request: Any, pk: int) -> Response:
        appeal = PatentAppeal.objects.filter(pk=pk).first()
        if not appeal:
            raise Http404("Appeal not found.")

        serializer = s.AppealReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            appeal_service.review_patent_appeal(
                appeal=appeal,
                director_user_id=_actor_id(request),
                decision=data["decision"],
                justification=data["justification"],
            )
            return Response(s.PatentAppealSerializer(appeal).data)
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class PriorArtSearchListView(APIView):
    """GET /api/v1/pms/prior-art - List prior art searches.
    POST /api/v1/pms/prior-art - Record prior art search.
    """

    permission_classes = [MODULE, HasPermission("pms.prior_art.view")]

    def get(self, request: Any) -> Response:
        searches = PriorArtSearchRecord.objects.all().order_by("-search_date")
        return Response({"results": s.PriorArtSearchRecordSerializer(searches, many=True).data})

    def post(self, request: Any) -> Response:
        if not scoping.has_permission(_actor(request), "pms.prior_art.manage"):
            return Response(
                {"detail": "Permission 'pms.prior_art.manage' required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = s.PriorArtSearchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        query_str = data.get("query_string") or data.get("keywords", "")
        notes = data.get("session_notes") or data.get("results_summary", "")
        count = int(data.get("results_count", 0))

        try:
            search = appeal_service.record_prior_art_search(
                user_id=_actor_id(request),
                query_string=query_str,
                databases_searched=data["databases_searched"],
                results_count=count,
                session_notes=notes,
            )
            return Response(
                s.PriorArtSearchRecordSerializer(search).data,
                status=status.HTTP_201_CREATED,
            )
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


class PriorArtAttachView(APIView):
    """POST /api/v1/pms/prior-art/<pk>/attach - Attach prior art search to application."""

    permission_classes = [MODULE, HasPermission("pms.prior_art.manage")]

    def post(self, request: Any, pk: int) -> Response:
        search = PriorArtSearchRecord.objects.filter(pk=pk).first()
        if not search:
            raise Http404("Prior art search not found.")

        serializer = s.PriorArtAttachInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        app = get_application_or_404(_actor(request), data["application_id"])

        try:
            attachment = appeal_service.attach_prior_art_to_application(
                search_record=search,
                application=app,
                relevance_notes=data.get("relevance_notes", ""),
            )
            return Response(
                s.PriorArtAttachmentSerializer(attachment).data,
                status=status.HTTP_201_CREATED,
            )
        except DOMAIN_EXCEPTIONS as e:
            return _handle_domain_error(e)


# --- Reports & Audit Logs ---


class PortfolioSummaryView(APIView):
    """GET /api/v1/pms/reports/summary - Portfolio summary analytics."""

    permission_classes = [MODULE, HasPermission("pms.report.view")]

    def get(self, request: Any) -> Response:
        stats = get_portfolio_summary_stats(_actor(request))
        return Response(stats)


class AuditLogListView(APIView):
    """GET /api/v1/pms/audit-logs - Compliance audit log viewer."""

    permission_classes = [MODULE, HasPermission("pms.audit.view")]

    def get(self, request: Any) -> Response:
        logs = scoping.scoped_audit_logs(_actor(request))
        return Response({"results": s.PatentAuditLogSerializer(logs[:200], many=True).data})
