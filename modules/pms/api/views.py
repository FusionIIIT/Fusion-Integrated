"""PMS API Views.

Implements all PMS endpoints with strict authorization and domain service delegation.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasPermission
from modules.pms.api import permissions as p
from modules.pms.api import serializers as s
from modules.pms.models import (
    AttorneyPanel,
    LicensingRequest,
    OfficeAction,
    PatentLegalAdvice,
    PmsAuditTrail,
)
from modules.pms.selectors.applications import visible_applications
from modules.pms.services import (
    approve_office_action_response,
    assign_attorney,
    assign_director,
    attach_prior_art,
    decide_budget,
    decide_renewal,
    draft_office_action_response,
    file_appeal,
    record_consent_and_agreement,
    record_external_filing,
    record_legal_advice,
    record_maintenance_action,
    record_office_action,
    record_patent_grant,
    record_withdrawal_consent,
    request_office_action_extension,
    request_renewal_decision,
    respond_to_attorney_assignment,
    review_appeal,
    review_licensing_request,
    revise_and_resubmit_application,
    search_prior_art,
    submit_application,
    submit_director_review,
    submit_licensing_request,
    submit_office_action_response,
    submit_or_update_budget,
    submit_patentability_assessment,
    upload_document_version,
    withdraw_application,
)


class PatentApplicationListCreateView(APIView):
    """List applications visible to caller or submit a new application (UC-PMS-001, CFR-PMS-001, CFR-PMS-005)."""

    permission_classes = [p.MODULE]

    @extend_schema(responses=s.PatentApplicationReadSerializer(many=True))
    def get(self, request):
        qs = visible_applications(request.principal)
        domain = request.query_params.get("domain")
        status_filter = request.query_params.get("status")
        if domain:
            qs = qs.filter(domain=domain)
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = s.PatentApplicationReadSerializer(qs[:100], many=True)
        return Response(serializer.data)

    @extend_schema(
        request=s.SubmitApplicationWriteSerializer, responses=s.PatentApplicationReadSerializer
    )
    def post(self, request):
        if not request.principal.has_permission(p.P_CREATE):
            raise PermissionDeniedError("You do not have permission to submit patent applications.")

        serializer = s.SubmitApplicationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        app = submit_application(
            applicant_user_id=request.principal.user_id,
            title=d["title"],
            abstract=d["abstract"],
            detailed_description=d["detailed_description"],
            claims=d["claims"],
            domain=d["domain"],
            jurisdiction=d.get("jurisdiction", "IN"),
            is_international=d.get("is_international", False),
            international_justification=d.get("international_justification", ""),
            preferred_attorney_id=d.get("preferred_attorney_id"),
            coinventors_data=d.get("coinventors"),
            documents_data=d.get("documents"),
        )
        return Response(s.PatentApplicationReadSerializer(app).data, status=status.HTTP_201_CREATED)


class PatentApplicationDetailView(APIView):
    """Retrieve full application details (UC-PMS-002, CFR-PMS-001)."""

    permission_classes = [p.MODULE]

    @extend_schema(responses=s.PatentApplicationReadSerializer)
    def get(self, request, pk: int):
        qs = visible_applications(request.principal)
        app = qs.filter(pk=pk).first()
        if not app:
            raise NotFoundError(f"Patent application {pk} not found or inaccessible.")
        return Response(s.PatentApplicationReadSerializer(app).data)


class PatentApplicationReviseView(APIView):
    """Revise and resubmit an application (UC-PMS-005, CFR-PMS-008)."""

    permission_classes = [p.MODULE, HasPermission(p.P_REVISE)]

    @extend_schema(
        request=s.ReviseApplicationSerializer, responses=s.PatentApplicationReadSerializer
    )
    def post(self, request, pk: int):
        serializer = s.ReviseApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        app = revise_and_resubmit_application(
            application_id=pk,
            applicant_user_id=request.principal.user_id,
            feedback_response=d["feedback_response"],
            title=d.get("title"),
            abstract=d.get("abstract"),
            detailed_description=d.get("detailed_description"),
            claims=d.get("claims"),
            new_documents_data=d.get("documents"),
        )
        return Response(s.PatentApplicationReadSerializer(app).data)


class PatentApplicationWithdrawView(APIView):
    """Withdraw an application before filing (UC-PMS-006, CFR-PMS-015)."""

    permission_classes = [p.MODULE, HasPermission(p.P_WITHDRAW)]

    @extend_schema(
        request=s.WithdrawApplicationSerializer, responses=s.PatentApplicationReadSerializer
    )
    def post(self, request, pk: int):
        serializer = s.WithdrawApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        app = withdraw_application(
            application_id=pk,
            applicant_user_id=request.principal.user_id,
            reason=reason,
        )
        return Response(s.PatentApplicationReadSerializer(app).data)


class PatentApplicationAssignDirectorView(APIView):
    """Assign an application to a Director for review (UC-PMS-007, CFR-PMS-006)."""

    permission_classes = [p.MODULE, HasPermission(p.P_ASSIGN_DIRECTOR)]

    @extend_schema(request=s.AssignDirectorSerializer, responses=s.PatentApplicationReadSerializer)
    def post(self, request, pk: int):
        serializer = s.AssignDirectorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        director_id = serializer.validated_data["director_user_id"]

        app = assign_director(
            application_id=pk,
            director_user_id=director_id,
            assigned_by_user_id=request.principal.user_id,
        )
        return Response(s.PatentApplicationReadSerializer(app).data)


class PatentApplicationReviewView(APIView):
    """Submit a Director technical review decision (UC-PMS-008, CFR-PMS-007)."""

    permission_classes = [p.MODULE, HasPermission(p.P_REVIEW)]

    @extend_schema(request=s.SubmitReviewSerializer, responses=s.DirectorReviewSerializer)
    def post(self, request, pk: int):
        serializer = s.SubmitReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        review = submit_director_review(
            application_id=pk,
            director_user_id=request.principal.user_id,
            decision=d["decision"],
            justification=d["justification"],
            feedback=d.get("feedback", ""),
        )
        return Response(s.DirectorReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class PatentApplicationAppealView(APIView):
    """File an appeal against application rejection (UC-PMS-022, CFR-PMS-020)."""

    permission_classes = [p.MODULE, HasPermission(p.P_APPEAL)]

    @extend_schema(request=s.FileAppealSerializer, responses=s.PatentAppealSerializer)
    def post(self, request, pk: int):
        serializer = s.FileAppealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        appeal = file_appeal(
            application_id=pk,
            applicant_user_id=request.principal.user_id,
            grounds=d["grounds"],
            justification=d["justification"],
        )
        return Response(s.PatentAppealSerializer(appeal).data, status=status.HTTP_201_CREATED)


class PatentAppealReviewView(APIView):
    """Review and decide an appeal (UC-PMS-023, CFR-PMS-020)."""

    permission_classes = [p.MODULE, HasPermission(p.P_REVIEW_APPEAL)]

    @extend_schema(request=s.ReviewAppealSerializer, responses=s.PatentAppealSerializer)
    def post(self, request, appeal_id: int):
        serializer = s.ReviewAppealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        appeal = review_appeal(
            appeal_id=appeal_id,
            director_user_id=request.principal.user_id,
            outcome=d["outcome"],
            outcome_justification=d["outcome_justification"],
        )
        return Response(s.PatentAppealSerializer(appeal).data)


class PatentBudgetView(APIView):
    """Submit budget line items or decide budget (UC-PMS-009, CFR-PMS-011)."""

    permission_classes = [p.MODULE]

    @extend_schema(request=s.BudgetLineItemsSerializer, responses=s.PatentBudgetSerializer)
    def put(self, request, pk: int):
        serializer = s.BudgetLineItemsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        budget = submit_or_update_budget(
            application_id=pk,
            filing_fees=d["filing_fees"],
            attorney_fees=d["attorney_fees"],
            administrative_costs=d["administrative_costs"],
            threshold_limit=d.get("threshold_limit", Decimal("100000.00")),
            actor_user_id=request.principal.user_id,
        )
        return Response(s.PatentBudgetSerializer(budget).data)

    @extend_schema(request=s.DecideBudgetSerializer, responses=s.PatentBudgetSerializer)
    def post(self, request, pk: int):
        if not request.principal.has_permission(p.P_BUDGET_REVIEW):
            raise PermissionDeniedError("You do not have permission to review or decide budgets.")

        serializer = s.DecideBudgetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        budget = decide_budget(
            application_id=pk,
            director_user_id=request.principal.user_id,
            decision=d["decision"],
            justification=d.get("justification", ""),
        )
        return Response(s.PatentBudgetSerializer(budget).data)


class PatentApplicationAssignAttorneyView(APIView):
    """PCC_ADMIN assigns an Attorney to an approved application (UC-PMS-010, CFR-PMS-009)."""

    permission_classes = [p.MODULE, HasPermission(p.P_ASSIGN_ATTORNEY)]

    @extend_schema(request=s.AssignAttorneySerializer, responses=s.AttorneyAssignmentSerializer)
    def post(self, request, pk: int):
        serializer = s.AssignAttorneySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        assignment = assign_attorney(
            application_id=pk,
            attorney_user_id=d["attorney_user_id"],
            assigned_by_user_id=request.principal.user_id,
            institutional_exception=d.get("institutional_exception", False),
        )
        return Response(
            s.AttorneyAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED
        )


class AttorneyAssignmentRespondView(APIView):
    """Attorney accepts or declines assignment (UC-PMS-011, CFR-PMS-009)."""

    permission_classes = [p.MODULE, HasPermission(p.P_RESPOND_ASSIGNMENT)]

    @extend_schema(
        request=s.RespondAttorneyAssignmentSerializer, responses=s.AttorneyAssignmentSerializer
    )
    def post(self, request, assignment_id: int):
        serializer = s.RespondAttorneyAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        assignment = respond_to_attorney_assignment(
            assignment_id=assignment_id,
            attorney_user_id=request.principal.user_id,
            accept=d["accept"],
            decline_reason=d.get("decline_reason", ""),
        )
        return Response(s.AttorneyAssignmentSerializer(assignment).data)


class PatentabilityAssessmentView(APIView):
    """Conduct patentability assessment (UC-PMS-012, CFR-PMS-010)."""

    permission_classes = [p.MODULE, HasPermission(p.P_PATENTABILITY_ASSESS)]

    @extend_schema(
        request=s.PatentabilityAssessmentCreateSerializer,
        responses=s.PatentabilityAssessmentSerializer,
    )
    def post(self, request, pk: int):
        serializer = s.PatentabilityAssessmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        assessment = submit_patentability_assessment(
            application_id=pk,
            attorney_user_id=request.principal.user_id,
            recommendation=d["recommendation"],
            opinion_text=d["opinion_text"],
            novelty_score=d.get("novelty_score", 0),
            non_obviousness_score=d.get("non_obviousness_score", 0),
            utility_score=d.get("utility_score", 0),
        )
        return Response(
            s.PatentabilityAssessmentSerializer(assessment).data, status=status.HTTP_201_CREATED
        )


class PatentFilingView(APIView):
    """Prepare and record external patent filing (UC-PMS-013, CFR-PMS-012)."""

    permission_classes = [p.MODULE, HasPermission(p.P_FILING_RECORD)]

    @extend_schema(request=s.RecordFilingSerializer, responses=s.PatentApplicationReadSerializer)
    def post(self, request, pk: int):
        serializer = s.RecordFilingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        app = record_external_filing(
            application_id=pk,
            attorney_user_id=request.principal.user_id,
            external_filing_id=d["external_filing_id"],
            external_filing_date=d["external_filing_date"],
            filing_confirmation=d["filing_confirmation"],
            is_international=d.get("is_international", False),
            international_justification=d.get("international_justification", ""),
        )
        return Response(s.PatentApplicationReadSerializer(app).data)


class PatentGrantView(APIView):
    """Record patent grant and initialize maintenance tracking (UC-PMS-014, CFR-PMS-013)."""

    permission_classes = [p.MODULE, HasPermission(p.P_FILING_RECORD)]

    @extend_schema(request=s.RecordGrantSerializer, responses=s.PatentApplicationReadSerializer)
    def post(self, request, pk: int):
        serializer = s.RecordGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        app = record_patent_grant(
            application_id=pk,
            attorney_user_id=request.principal.user_id,
            patent_number=d["patent_number"],
            grant_date=d["grant_date"],
        )
        return Response(s.PatentApplicationReadSerializer(app).data)


class OfficeActionListCreateView(APIView):
    """List or record office actions (UC-PMS-014, CFR-PMS-014)."""

    permission_classes = [p.MODULE]

    @extend_schema(responses=s.OfficeActionSerializer(many=True))
    def get(self, request, pk: int):
        oas = OfficeAction.objects.filter(application_id=pk).order_by("-issue_date")
        return Response(s.OfficeActionSerializer(oas, many=True).data)

    @extend_schema(request=s.RecordOfficeActionSerializer, responses=s.OfficeActionSerializer)
    def post(self, request, pk: int):
        if not request.principal.has_permission(p.P_OA_RECORD):
            raise PermissionDeniedError("Permission denied to record office actions.")

        serializer = s.RecordOfficeActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        oa = record_office_action(
            application_id=pk,
            attorney_user_id=request.principal.user_id,
            action_type=d["action_type"],
            issue_date=d["issue_date"],
            due_date=d["due_date"],
            details=d["details"],
            requires_applicant_review=d.get("requires_applicant_review", True),
        )
        return Response(s.OfficeActionSerializer(oa).data, status=status.HTTP_201_CREATED)


class OfficeActionDraftResponseView(APIView):
    """Attorney drafts response to office action (UC-PMS-015, CFR-PMS-014)."""

    permission_classes = [p.MODULE, HasPermission(p.P_OA_RESPOND)]

    @extend_schema(
        request=s.DraftOfficeActionResponseSerializer, responses=s.OfficeActionSerializer
    )
    def post(self, request, oa_id: int):
        serializer = s.DraftOfficeActionResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        oa = draft_office_action_response(
            office_action_id=oa_id,
            attorney_user_id=request.principal.user_id,
            draft_response=serializer.validated_data["draft_response"],
        )
        return Response(s.OfficeActionSerializer(oa).data)


class OfficeActionApproveResponseView(APIView):
    """Applicant approves draft response (UC-PMS-029, BR-PMS-146)."""

    permission_classes = [p.MODULE, HasPermission(p.P_OA_REVIEW)]

    @extend_schema(request=None, responses=s.OfficeActionSerializer)
    def post(self, request, oa_id: int):
        oa = approve_office_action_response(
            office_action_id=oa_id,
            applicant_user_id=request.principal.user_id,
        )
        return Response(s.OfficeActionSerializer(oa).data)


class OfficeActionSubmitResponseView(APIView):
    """Attorney submits finalized response (UC-PMS-015, BR-PMS-065)."""

    permission_classes = [p.MODULE, HasPermission(p.P_OA_RESPOND)]

    @extend_schema(
        request=s.SubmitOfficeActionResponseSerializer, responses=s.OfficeActionSerializer
    )
    def post(self, request, oa_id: int):
        serializer = s.SubmitOfficeActionResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        oa = submit_office_action_response(
            office_action_id=oa_id,
            attorney_user_id=request.principal.user_id,
            submission_details=serializer.validated_data["submission_details"],
        )
        return Response(s.OfficeActionSerializer(oa).data)


class OfficeActionExtensionView(APIView):
    """Attorney files extension request (UC-PMS-015)."""

    permission_classes = [p.MODULE, HasPermission(p.P_OA_RESPOND)]

    @extend_schema(request=s.OfficeActionExtensionSerializer, responses=s.OfficeActionSerializer)
    def post(self, request, oa_id: int):
        serializer = s.OfficeActionExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        oa = request_office_action_extension(
            office_action_id=oa_id,
            attorney_user_id=request.principal.user_id,
            extension_months=serializer.validated_data["extension_months"],
        )
        return Response(s.OfficeActionSerializer(oa).data)


class MaintenanceRequestRenewalView(APIView):
    """Attorney initiates renewal decision request (UC-PMS-017, BR-PMS-061)."""

    permission_classes = [p.MODULE, HasPermission(p.P_MAINTENANCE_MANAGE)]

    @extend_schema(request=None, responses=s.PostGrantMaintenanceSerializer)
    def post(self, request, maintenance_id: int):
        maint = request_renewal_decision(
            maintenance_id=maintenance_id,
            attorney_user_id=request.principal.user_id,
        )
        return Response(s.PostGrantMaintenanceSerializer(maint).data)


class MaintenanceDecideRenewalView(APIView):
    """Director decides renewal: Renew or Do Not Renew (UC-PMS-018, BR-PMS-061)."""

    permission_classes = [p.MODULE, HasPermission(p.P_MAINTENANCE_DECIDE)]

    @extend_schema(request=s.DecideRenewalSerializer, responses=s.PostGrantMaintenanceSerializer)
    def post(self, request, maintenance_id: int):
        serializer = s.DecideRenewalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        maint = decide_renewal(
            maintenance_id=maintenance_id,
            director_user_id=request.principal.user_id,
            decision=serializer.validated_data["decision"],
        )
        return Response(s.PostGrantMaintenanceSerializer(maint).data)


class MaintenanceRecordActionView(APIView):
    """Attorney records completed renewal action (UC-PMS-017, BW-PMS-14)."""

    permission_classes = [p.MODULE, HasPermission(p.P_MAINTENANCE_MANAGE)]

    @extend_schema(
        request=s.RecordMaintenanceActionSerializer, responses=s.PostGrantMaintenanceSerializer
    )
    def post(self, request, maintenance_id: int):
        serializer = s.RecordMaintenanceActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        maint = record_maintenance_action(
            maintenance_id=maintenance_id,
            attorney_user_id=request.principal.user_id,
            transaction_reference=serializer.validated_data["transaction_reference"],
        )
        return Response(s.PostGrantMaintenanceSerializer(maint).data)


class PriorArtSearchView(APIView):
    """Search prior art across external databases (UC-PMS-004, CFR-PMS-017)."""

    permission_classes = [p.MODULE, HasPermission(p.P_PRIOR_ART)]

    @extend_schema(request=None, responses=s.PriorArtSearchResponseSerializer)
    def get(self, request):
        query = request.query_params.get("q", "")
        domain = request.query_params.get("domain", "")
        results = search_prior_art(
            query=query,
            domain=domain,
            actor_user_id=request.principal.user_id,
        )
        return Response({"results": results})


class PriorArtAttachView(APIView):
    """Attach prior-art reference to an application (UC-PMS-004, CFR-PMS-017)."""

    permission_classes = [p.MODULE, HasPermission(p.P_PRIOR_ART)]

    @extend_schema(request=s.AttachPriorArtSerializer, responses=s.PriorArtReferenceSerializer)
    def post(self, request, pk: int):
        serializer = s.AttachPriorArtSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        ref = attach_prior_art(
            application_id=pk,
            user_id=request.principal.user_id,
            source=d["source"],
            reference_id=d["reference_id"],
            title=d["title"],
            authors=d.get("authors", ""),
            relevance=d.get("relevance", "high"),
            notes=d.get("notes", ""),
        )
        return Response(s.PriorArtReferenceSerializer(ref).data, status=status.HTTP_201_CREATED)


class DocumentUploadView(APIView):
    """Upload a new document version (UC-PMS-019, CFR-PMS-018)."""

    permission_classes = [p.MODULE, HasPermission(p.P_DOC_MANAGE)]

    @extend_schema(request=s.UploadDocumentSerializer, responses=s.ApplicationDocumentSerializer)
    def post(self, request, pk: int):
        serializer = s.UploadDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        role = "Applicant" if request.principal.has_permission(p.P_VIEW_SELF) else "Staff"
        doc = upload_document_version(
            application_id=pk,
            user_id=request.principal.user_id,
            user_role=role,
            doc_type=d["doc_type"],
            title=d["title"],
            filename=d["filename"],
            file_size_bytes=d["file_size_bytes"],
            sensitivity=d.get("sensitivity", "confidential"),
            file_url=d.get("file_url", ""),
        )
        return Response(s.ApplicationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class LicensingRequestListCreateView(APIView):
    """Submit or list licensing requests (UC-PMS-020, CFR-PMS-019)."""

    permission_classes = [p.MODULE]

    @extend_schema(responses=s.LicensingRequestSerializer(many=True))
    def get(self, request, pk: int):
        reqs = LicensingRequest.objects.filter(application_id=pk)
        return Response(s.LicensingRequestSerializer(reqs, many=True).data)

    @extend_schema(
        request=s.LicensingRequestCreateSerializer, responses=s.LicensingRequestSerializer
    )
    def post(self, request, pk: int):
        if not request.principal.has_permission(p.P_LICENSING_SUBMIT):
            raise PermissionDeniedError("Permission denied to submit licensing requests.")

        serializer = s.LicensingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        req = submit_licensing_request(
            application_id=pk,
            requested_by_user_id=request.principal.user_id,
            licensee_name=d["licensee_name"],
            request_type=d["request_type"],
            commercial_terms=d["commercial_terms"],
        )
        return Response(s.LicensingRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LicensingRequestReviewView(APIView):
    """Review licensing request (UC-PMS-021, CFR-PMS-019)."""

    permission_classes = [p.MODULE, HasPermission(p.P_LICENSING_REVIEW)]

    @extend_schema(request=s.LicensingReviewSerializer, responses=s.LicensingRequestSerializer)
    def post(self, request, request_id: int):
        serializer = s.LicensingReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        req = review_licensing_request(
            request_id=request_id,
            director_user_id=request.principal.user_id,
            status=d["status"],
            negotiation_notes=d.get("negotiation_notes", ""),
            agreement_reference=d.get("agreement_reference", ""),
        )
        return Response(s.LicensingRequestSerializer(req).data)


class CoInventorConsentView(APIView):
    """Record inventor agreement and signature (UC-PMS-003, CFR-PMS-016)."""

    permission_classes = [p.MODULE]

    @extend_schema(request=s.CoInventorConsentWriteSerializer, responses=s.CoInventorSerializer)
    def post(self, request, coinventor_id: int):
        serializer = s.CoInventorConsentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        coinv = record_consent_and_agreement(
            coinventor_id=coinventor_id,
            user_id=request.principal.user_id,
            consent_given=data.get("consent_given", True),
            agreement_signed=data.get("agreement_signed", True),
            electronic_signature=data.get("electronic_signature", ""),
        )
        return Response(s.CoInventorSerializer(coinv).data)


class CoInventorWithdrawalConsentView(APIView):
    """Record co-inventor consent for withdrawal (UC-PMS-003, BR-PMS-070)."""

    permission_classes = [p.MODULE]

    @extend_schema(
        request=s.CoInventorWithdrawalConsentWriteSerializer,
        responses=s.CoInventorSerializer,
    )
    def post(self, request, coinventor_id: int):
        serializer = s.CoInventorWithdrawalConsentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coinv = record_withdrawal_consent(
            coinventor_id=coinventor_id,
            user_id=request.principal.user_id,
            consent_given=serializer.validated_data.get("withdrawal_consent_given", True),
        )
        return Response(s.CoInventorSerializer(coinv).data)


class LegalAdviceListCreateView(APIView):
    """Record or view patent legal advice (UC-PMS-033, CFR-PMS-004)."""

    permission_classes = [p.MODULE]

    @extend_schema(responses=s.PatentLegalAdviceSerializer(many=True))
    def get(self, request, pk: int):
        advices = PatentLegalAdvice.objects.filter(application_id=pk)
        return Response(s.PatentLegalAdviceSerializer(advices, many=True).data)

    @extend_schema(request=s.LegalAdviceCreateSerializer, responses=s.PatentLegalAdviceSerializer)
    def post(self, request, pk: int):
        if not request.principal.has_permission(p.P_ADVICE_RECORD):
            raise PermissionDeniedError("Permission denied to record legal advice.")

        serializer = s.LegalAdviceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        advice = record_legal_advice(
            application_id=pk,
            attorney_user_id=request.principal.user_id,
            stage=d["stage"],
            advice_text=d["advice_text"],
        )
        return Response(s.PatentLegalAdviceSerializer(advice).data, status=status.HTTP_201_CREATED)


class AuditTrailListView(APIView):
    """View audit trail and compliance logs (UC-PMS-028, CFR-PMS-024)."""

    permission_classes = [p.MODULE, HasPermission(p.P_AUDIT_VIEW)]

    @extend_schema(responses=s.PmsAuditTrailSerializer(many=True))
    def get(self, request):
        qs = PmsAuditTrail.objects.all().order_by("-timestamp")
        app_id = request.query_params.get("application_id")
        action_type = request.query_params.get("action_type")
        if app_id:
            qs = qs.filter(application_id=app_id)
        if action_type:
            qs = qs.filter(action_type=action_type)
        return Response(s.PmsAuditTrailSerializer(qs[:100], many=True).data)


class ReportsView(APIView):
    """Reports, dashboards, and workload analytics (UC-PMS-024, 030, 031, 032, CFR-PMS-022)."""

    permission_classes = [p.MODULE]

    @extend_schema(request=None, responses=s.PmsReportResponseSerializer)
    def get(self, request):
        p_obj = request.principal
        # Log report access (CFR-PMS-022)
        PmsAuditTrail.objects.create(
            actor_user_id=p_obj.user_id,
            action_type="report_viewed",
            details={"scope": p_obj.active_role or "unknown"},
        )

        qs = visible_applications(p_obj)
        status_counts = dict(
            qs.values("status").annotate(count=Count("id")).values_list("status", "count")
        )
        domain_counts = dict(
            qs.values("domain").annotate(count=Count("id")).values_list("domain", "count")
        )

        return Response(
            {
                "total_applications": qs.count(),
                "status_distribution": status_counts,
                "domain_distribution": domain_counts,
            }
        )


class AttorneyPanelListView(generics.ListCreateAPIView):
    """Attorney panel maintenance and expertise mappings (UC-PMS-026, CFR-PMS-003)."""

    permission_classes = [p.MODULE, HasPermission(p.P_PANEL_MANAGE, p.P_ASSIGN_ATTORNEY)]
    queryset = AttorneyPanel.objects.all().order_by("name")
    serializer_class = s.AttorneyPanelSerializer
