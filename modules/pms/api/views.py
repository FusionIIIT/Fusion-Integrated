import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db.models import Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from rest_framework import parsers, status, views
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.files.validators import sanitise_filename
from fusion_auth.permissions import HasModuleGrant
from modules.pms import services
from modules.pms.api.serializers import (
    ApplicationDocumentSerializer,
    ApplicationSerializer,
    AttorneyAssignmentSerializer,
    AttorneyProfileSerializer,
    BudgetProposalSerializer,
    DirectorProfileSerializer,
    InventorAgreementSerializer,
    OfficeActionResponseSerializer,
    PatentabilityOpinionSerializer,
    PatentAppealSerializer,
    PatentOfficeCommunicationSerializer,
    PmsAuditEventSerializer,
    PmsConfigurationSerializer,
)
from modules.pms.models import (
    Application,
    ApplicationDocument,
    ApplicationInventorAgreement,
    AttorneyProfile,
    Deadline,
    DirectorProfile,
    Inventor,
    LegalAdviceRecord,
    LicensingRequest,
    MaintenanceCycle,
    OfficeActionResponse,
    PatentOfficeCommunication,
    PmsAuditEvent,
    PmsConfiguration,
    PmsNotification,
    PriorArtReference,
    PriorArtSearchSession,
)

PMS = [IsAuthenticated, HasModuleGrant("pms")]


class PmsAutoSchema(AutoSchema):
    """Describe APIView payloads as JSON objects and keep operation IDs unique."""

    def get_request_serializer(self):
        return OpenApiTypes.OBJECT

    def get_response_serializers(self):
        return OpenApiTypes.OBJECT

    def get_operation_id(self):
        view_name = self.view.__class__.__name__.removesuffix("View")
        view_name = re.sub(r"(?<!^)(?=[A-Z])", "_", view_name).lower()
        path_name = re.sub(r"[^a-zA-Z0-9]+", "_", self.path).strip("_").lower()
        return f"pms_{view_name}_{self.method.lower()}_{path_name}"


class PmsAPIView(views.APIView):
    # PMS endpoints return workflow dictionaries rather than ModelViewSet serializers.
    schema = PmsAutoSchema()


def _p(request):
    return request.principal


def _need(request, *codes):
    if not _p(request).has_any_permission(*codes):
        raise PermissionDenied("You do not have permission to perform this PMS action.")


def _need_pcc_admin(request):
    principal = _p(request)
    active_role = (principal.active_role or "").casefold()
    if active_role != "pcc_admin":
        raise PermissionDenied("The active PMS role must be PCC_ADMIN.")
    row = PmsConfiguration.objects.filter(key="pcc_admin_user_id").first()
    if not row or int(row.value) != principal.user_id:
        raise PermissionDenied("This user is not the single configured active PCC_ADMIN.")


def _application(request, app_id, *, write=False):
    app = get_object_or_404(Application, pk=app_id)
    principal = _p(request)
    assigned = principal.user_id in (app.assigned_director_user_id, app.assigned_attorney_user_id)
    elevated = principal.has_permission("pms.workflow.manage")
    if elevated:
        _need_pcc_admin(request)
    if app.applicant_user_id != principal.user_id and not assigned and not elevated:
        raise PermissionDenied("You may not access this application.")
    if (
        write
        and app.applicant_user_id != principal.user_id
        and not assigned
        and not principal.has_permission("pms.workflow.manage")
    ):
        raise PermissionDenied("You may not change this application.")
    return app


class ApplicationListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        principal = _p(request)
        if principal.has_permission("pms.workflow.manage"):
            _need_pcc_admin(request)
        qs = Application.objects.none()
        if principal.has_permission("pms.application.view_self"):
            qs = qs | Application.objects.filter(applicant_user_id=principal.user_id)
        if principal.has_permission("pms.application.review"):
            qs = qs | Application.objects.filter(assigned_director_user_id=principal.user_id)
        if principal.has_any_permission(
            "pms.legal_opinion.create", "pms.office_action.record", "pms.filing.record"
        ):
            qs = qs | Application.objects.filter(assigned_attorney_user_id=principal.user_id)
        if principal.has_permission("pms.workflow.manage"):
            _need_pcc_admin(request)
            qs = Application.objects.all()
        qs = qs.distinct().order_by("-created_at")
        return Response(ApplicationSerializer(qs[:200], many=True).data)

    def post(self, request):
        _need(request, "pms.application.create")
        serializer = ApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = serializer.save(
            applicant_user_id=_p(request).user_id, status=Application.Status.DRAFT
        )
        services._audit(app, _p(request).user_id, "application_draft_created", "", app.status)
        return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        return Response(ApplicationSerializer(_application(request, app_id)).data)


class ApplicationHistoryView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        rows = app.transitions.all()
        return Response(
            [
                {
                    "from_status": row.from_status,
                    "to_status": row.to_status,
                    "action": row.action,
                    "justification": row.justification,
                    "actor_user_id": row.actor_user_id,
                    "occurred_at": row.occurred_at,
                }
                for row in rows
            ]
        )


class InventorConsentView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, agreement_id):
        _need(request, "pms.inventor.consent")
        agreement = get_object_or_404(
            ApplicationInventorAgreement.objects.select_related("inventor", "application"),
            pk=agreement_id,
        )
        if agreement.inventor.user_id != _p(request).user_id:
            raise PermissionDenied(
                "Only the listed inventor may record consent for this agreement."
            )
        if agreement.agreement_status != "pending":
            raise ValidationError({"detail": "This inventor agreement is no longer pending."})
        if request.data.get("consent") is not True:
            raise ValidationError(
                {"consent": "Provide explicit consent to the inventor agreement."}
            )
        agreement.agreement_status = "accepted"
        agreement.consent_recorded_at = timezone.now()
        agreement.signature_reference = (request.data.get("signature_reference") or "")[:255]
        agreement.save(
            update_fields=["agreement_status", "consent_recorded_at", "signature_reference"]
        )
        services._audit(
            agreement.application,
            _p(request).user_id,
            "inventor_agreement_consent_recorded",
            agreement.application.status,
            agreement.application.status,
            {"agreement_id": agreement.pk},
        )
        return Response(
            {
                "id": agreement.pk,
                "agreement_status": agreement.agreement_status,
                "consent_recorded_at": agreement.consent_recorded_at,
            }
        )


class ApplicationSubmitView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.application.submit")
        app = services.submit_application(app_id, _p(request).user_id)
        return Response(ApplicationSerializer(app).data)


class DirectorAssignmentView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.workflow.assign_director")
        _need_pcc_admin(request)
        director_id = request.data.get("director_user_id")
        if not director_id:
            raise ValidationError({"director_user_id": "This field is required."})
        app = services.assign_director(app_id, int(director_id), _p(request).user_id)
        return Response(ApplicationSerializer(app).data)


class ReviewDecisionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.application.review")
        app = services.review_application(
            app_id,
            _p(request).user_id,
            request.data.get("decision", ""),
            request.data.get("justification", ""),
        )
        return Response(ApplicationSerializer(app).data)


class RevisionResubmissionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.application.resubmit")
        app = services.resubmit_revision(
            app_id, _p(request).user_id, request.data.get("feedback_response", "")
        )
        return Response(ApplicationSerializer(app).data)


class ApplicationWithdrawalView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.application.withdraw")
        app = services.withdraw_application(
            app_id,
            _p(request).user_id,
            request.data.get("reason", ""),
            bool(request.data.get("co_inventor_consents_recorded", False)),
        )
        return Response(ApplicationSerializer(app).data)


class InventorListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        rows = app.inventor_agreements.select_related("inventor").all()
        return Response(
            [
                {
                    "id": row.pk,
                    "user_id": row.inventor.user_id,
                    "full_name": row.inventor.full_name,
                    "email": row.inventor.email,
                    "affiliation": row.inventor.affiliation,
                    "ownership_percent": row.ownership_percent,
                    "agreement_status": row.agreement_status,
                    "consent_recorded_at": row.consent_recorded_at,
                }
                for row in rows
            ]
        )

    def post(self, request, app_id):
        _need(request, "pms.inventor.manage")
        app = _application(request, app_id, write=True)
        if app.status not in (Application.Status.DRAFT, Application.Status.NEEDS_REVISION):
            raise ValidationError(
                {
                    "detail": (
                        "Inventor information can only be changed for drafts or applications "
                        "needing revision."
                    )
                }
            )
        name = (request.data.get("full_name") or "").strip()
        if not name:
            raise ValidationError({"full_name": "This field is required."})
        try:
            share = Decimal(str(request.data.get("ownership_percent")))
        except (InvalidOperation, TypeError):
            raise ValidationError({"ownership_percent": "Enter a valid percentage."}) from None
        if share < 0 or share > 100:
            raise ValidationError({"ownership_percent": "Ownership must be between 0 and 100."})
        inventor = Inventor.objects.create(
            user_id=request.data.get("user_id") or None,
            full_name=name,
            email=request.data.get("email", ""),
            affiliation=request.data.get("affiliation", ""),
        )
        row = ApplicationInventorAgreement.objects.create(
            application=app,
            inventor=inventor,
            ownership_percent=share,
        )
        services._audit(
            app,
            _p(request).user_id,
            "inventor_added",
            app.status,
            app.status,
            {"inventor_id": inventor.pk},
        )
        if inventor.user_id and inventor.user_id != _p(request).user_id:
            PmsNotification.objects.get_or_create(
                dedupe_key=f"application:{app.pk}:inventor:{inventor.pk}:agreement",
                defaults={
                    "recipient_user_id": inventor.user_id,
                    "application": app,
                    "event": "inventor.agreement_requested",
                    "subject": "Patent inventor agreement requires your consent",
                    "body": (
                        f"You were listed as an inventor on {app.application_number or app.title}. "
                        "Review the agreement in PMS."
                    ),
                },
            )
        return Response(InventorAgreementSerializer(row).data, status=status.HTTP_201_CREATED)


class DocumentUploadView(PmsAPIView):
    permission_classes = PMS
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        docs = app.documents.all()
        may_view_sensitive = app.applicant_user_id == _p(request).user_id or _p(
            request
        ).has_any_permission("pms.document.view_confidential", "pms.workflow.manage")
        if not may_view_sensitive:
            docs = docs.exclude(
                sensitivity__in=[
                    ApplicationDocument.Sensitivity.CONFIDENTIAL,
                    ApplicationDocument.Sensitivity.RESTRICTED,
                ]
            )
        return Response(ApplicationDocumentSerializer(docs, many=True).data)

    def post(self, request, app_id):
        _need(request, "pms.document.upload")
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            raise ValidationError({"file": "A PDF file is required."})
        doc = services.add_document(
            app_id,
            _p(request).user_id,
            uploaded_file,
            request.data.get("document_type", "other"),
            request.data.get("sensitivity", "internal"),
        )
        services._audit(
            doc.application,
            _p(request).user_id,
            "document_version_uploaded",
            doc.application.status,
            doc.application.status,
            {"document_id": doc.pk, "version": doc.version},
        )
        return Response(ApplicationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentDownloadView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id, document_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        doc = get_object_or_404(ApplicationDocument, pk=document_id, application=app)
        principal = _p(request)
        may_view_sensitive = (
            app.applicant_user_id == principal.user_id
            or principal.has_any_permission("pms.document.view_confidential", "pms.workflow.manage")
        )
        if (
            doc.sensitivity
            in (
                ApplicationDocument.Sensitivity.CONFIDENTIAL,
                ApplicationDocument.Sensitivity.RESTRICTED,
            )
            and not may_view_sensitive
        ):
            raise PermissionDenied(
                "This document's sensitivity classification is outside your access scope."
            )
        if doc.malware_scan_status != "clean":
            raise ValidationError(
                {"detail": "The document is unavailable until its malware scan is clean."}
            )
        services._audit(
            app,
            principal.user_id,
            "document_version_accessed",
            app.status,
            app.status,
            {"document_id": doc.pk, "version": doc.version},
        )
        return FileResponse(
            doc.file.open("rb"),
            as_attachment=True,
            filename=sanitise_filename(doc.original_filename, fallback="patent-document.pdf"),
            content_type="application/pdf",
        )


class AttorneyAssignmentView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.workflow.assign_attorney")
        _need_pcc_admin(request)
        attorney_id = request.data.get("attorney_user_id")
        app = get_object_or_404(Application, pk=app_id)
        if not attorney_id:
            attorney_id = app.preferred_attorney_user_id
        if not attorney_id:
            raise ValidationError({"attorney_user_id": "This field is required."})
        assignment = services.assign_attorney(
            app_id,
            int(attorney_id),
            _p(request).user_id,
            request.data.get("panel_exception", ""),
        )
        return Response(
            AttorneyAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED
        )


class AttorneyAssignmentResponseView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, assignment_id):
        _need(request, "pms.attorney_assignment.respond")
        accepted = request.data.get("accept")
        if not isinstance(accepted, bool):
            raise ValidationError({"accept": "Provide a boolean acceptance decision."})
        assignment = services.respond_to_attorney_assignment(
            assignment_id, _p(request).user_id, accepted
        )
        return Response(AttorneyAssignmentSerializer(assignment).data)


class BudgetListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        return Response(BudgetProposalSerializer(app.budgets.all(), many=True).data)

    def post(self, request, app_id):
        _need(request, "pms.budget.propose")
        serializer = BudgetProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal = services.propose_budget(app_id, _p(request).user_id, serializer.validated_data)
        return Response(BudgetProposalSerializer(proposal).data, status=status.HTTP_201_CREATED)


class BudgetDecisionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, budget_id):
        _need(request, "pms.budget.decide")
        budget = services.decide_budget(
            budget_id,
            _p(request).user_id,
            request.data.get("decision", ""),
            request.data.get("justification", ""),
            bool(request.data.get("availability_confirmed", False)),
        )
        return Response(BudgetProposalSerializer(budget).data)


class PatentabilityOpinionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.legal_opinion.create")
        app = _application(request, app_id, write=True)
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may record an opinion.")
        serializer = PatentabilityOpinionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opinion = serializer.save(application=app, attorney_user_id=_p(request).user_id)
        services._audit(
            app,
            _p(request).user_id,
            "patentability_opinion_recorded",
            app.status,
            app.status,
            {"opinion_id": opinion.pk},
        )
        return Response(
            PatentabilityOpinionSerializer(opinion).data, status=status.HTTP_201_CREATED
        )


class FilingRecordView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.filing.record")
        try:
            filing_date = date.fromisoformat(request.data.get("filing_date", ""))
        except (TypeError, ValueError):
            raise ValidationError({"filing_date": "Enter a valid ISO date."}) from None
        filing = services.record_filing(
            app_id,
            _p(request).user_id,
            jurisdiction=request.data.get("jurisdiction", ""),
            external_filing_id=request.data.get("external_filing_id", ""),
            filing_date=filing_date,
            international_justification=request.data.get("international_justification", ""),
            confirmation_reference=request.data.get("confirmation_reference", ""),
            format_validation_available=bool(
                request.data.get("format_validation_available", False)
            ),
            format_compliant=bool(request.data.get("format_compliant", False)),
        )
        return Response(
            {
                "id": filing.pk,
                "external_filing_id": filing.external_filing_id,
                "filing_date": filing.filing_date,
                "recorded_at": filing.recorded_at,
            },
            status=status.HTTP_201_CREATED,
        )


class AppealListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        return Response(PatentAppealSerializer(app.appeals.all(), many=True).data)

    def post(self, request, app_id):
        _need(request, "pms.appeal.file")
        appeal = services.file_appeal(
            app_id,
            _p(request).user_id,
            request.data.get("grounds", ""),
            request.data.get("justification", ""),
        )
        return Response(PatentAppealSerializer(appeal).data, status=status.HTTP_201_CREATED)


class AppealDecisionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, appeal_id):
        _need(request, "pms.appeal.review")
        appeal = services.decide_appeal(
            appeal_id,
            _p(request).user_id,
            request.data.get("outcome", ""),
            request.data.get("justification", ""),
        )
        return Response(PatentAppealSerializer(appeal).data)


class OfficeActionListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.application.view_self", "pms.application.view_all", "pms.workflow.manage"
        )
        app = _application(request, app_id)
        return Response(
            PatentOfficeCommunicationSerializer(app.office_communications.all(), many=True).data
        )

    def post(self, request, app_id):
        _need(request, "pms.office_action.record")
        app = _application(request, app_id, write=True)
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied(
                "Only the assigned Attorney may record patent-office communications."
            )
        serializer = PatentOfficeCommunicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if (
            request.data.get("kind") == PatentOfficeCommunication.Kind.GRANT
            and app.status != Application.Status.FILED
        ):
            raise ValidationError(
                {"detail": "A patent grant can only be recorded for a filed application."}
            )
        communication = serializer.save(application=app, recorded_by_user_id=_p(request).user_id)
        if communication.kind == PatentOfficeCommunication.Kind.GRANT:
            app.grant_date = communication.received_date
            services._transition(
                app,
                _p(request).user_id,
                "patent_granted",
                Application.Status.GRANTED,
                metadata={"communication_id": communication.pk},
            )
            app.save(update_fields=["grant_date", "updated_at"])
            services._notify(
                app,
                app.applicant_user_id,
                "patent.granted",
                "Patent grant recorded",
                f"{app.application_number} was recorded as granted.",
            )
        if communication.response_due_date:
            Deadline.objects.create(
                application=app,
                kind="office_action_response",
                due_at=timezone.make_aware(
                    datetime.combine(communication.response_due_date, datetime.max.time())
                ),
                responsible_user_id=app.assigned_attorney_user_id,
                source=communication.deadline_source or communication.external_reference,
            )
        services._audit(
            app,
            _p(request).user_id,
            "office_action_recorded",
            app.status,
            app.status,
            {"communication_id": communication.pk},
        )
        return Response(
            PatentOfficeCommunicationSerializer(communication).data, status=status.HTTP_201_CREATED
        )


class OfficeActionResponseView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, communication_id):
        _need(request, "pms.office_action.respond")
        communication = get_object_or_404(
            PatentOfficeCommunication.objects.select_related("application"), pk=communication_id
        )
        app = communication.application
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may prepare a response.")
        body = (request.data.get("response_text") or "").strip()
        if not body:
            raise ValidationError({"response_text": "A response draft is required."})
        review_policy = PmsConfiguration.objects.filter(
            key="office_action_applicant_review_required"
        ).first()
        if not review_policy:
            raise ValidationError(
                {
                    "detail": (
                        "Configure whether the applicable office-action process requires "
                        "Applicant review."
                    )
                }
            )
        required = bool(review_policy.value)
        response = OfficeActionResponse.objects.create(
            communication=communication,
            prepared_by_user_id=_p(request).user_id,
            response_text=body,
            applicant_review_required=required,
            status=OfficeActionResponse.Status.AWAITING_APPLICANT
            if required
            else OfficeActionResponse.Status.READY,
        )
        services._audit(
            app,
            _p(request).user_id,
            "office_action_response_prepared",
            app.status,
            app.status,
            {"response_id": response.pk},
        )
        return Response(
            OfficeActionResponseSerializer(response).data, status=status.HTTP_201_CREATED
        )


class OfficeActionApprovalView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, response_id):
        _need(request, "pms.office_action_response.review")
        response = get_object_or_404(
            OfficeActionResponse.objects.select_related("communication__application"),
            pk=response_id,
        )
        app = response.communication.application
        if app.applicant_user_id != _p(request).user_id:
            raise PermissionDenied("Only the Applicant may approve this response.")
        if (
            not response.applicant_review_required
            or response.status != OfficeActionResponse.Status.AWAITING_APPLICANT
        ):
            raise ValidationError({"detail": "This response does not require Applicant approval."})
        if not request.data.get("approved"):
            raise ValidationError(
                {
                    "detail": (
                        "Record the approval outcome before submission; a declined response "
                        "requires an Attorney revision."
                    )
                }
            )
        response.status = OfficeActionResponse.Status.READY
        response.applicant_decision_by_user_id = _p(request).user_id
        response.applicant_approved_at = timezone.now()
        response.save(
            update_fields=["status", "applicant_decision_by_user_id", "applicant_approved_at"]
        )
        services._audit(
            app,
            _p(request).user_id,
            "office_action_response_approved",
            app.status,
            app.status,
            {"response_id": response.pk},
        )
        return Response(OfficeActionResponseSerializer(response).data)


class OfficeActionSubmissionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, response_id):
        _need(request, "pms.office_action.respond")
        response = get_object_or_404(
            OfficeActionResponse.objects.select_related("communication__application"),
            pk=response_id,
        )
        app = response.communication.application
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may record response submission.")
        if response.status != OfficeActionResponse.Status.READY:
            raise ValidationError({"detail": "Applicant approval is required before submission."})
        reference = (request.data.get("external_submission_reference") or "").strip()
        if not reference:
            raise ValidationError(
                {"external_submission_reference": "Record the external submission reference."}
            )
        response.status = OfficeActionResponse.Status.SUBMITTED
        response.external_submission_reference = reference
        response.submitted_at = timezone.now()
        response.save(update_fields=["status", "external_submission_reference", "submitted_at"])
        services._audit(
            app,
            _p(request).user_id,
            "office_action_response_submitted",
            app.status,
            app.status,
            {"response_id": response.pk},
        )
        return Response(OfficeActionResponseSerializer(response).data)


class PmsConfigurationView(PmsAPIView):
    permission_classes = PMS
    ALLOWED = {
        "withdrawal_eligible_statuses",
        "appeal_period_days",
        "budget_escalation_threshold",
        "budget_availability_required",
        "deadline_alert_days",
        "deadline_escalation_user_ids",
        "pcc_admin_user_id",
        "maintenance_schedule",
        "office_action_applicant_review_required",
        "withdrawal_requires_co_inventor_consent",
        "budget_escalation_user_ids",
    }

    def get(self, request):
        _need(request, "pms.configuration.manage", "pms.workflow.manage")
        return Response(
            PmsConfigurationSerializer(PmsConfiguration.objects.order_by("key"), many=True).data
        )

    def put(self, request):
        _need(request, "pms.configuration.manage")
        key, value = request.data.get("key"), request.data.get("value")
        if (request.principal.active_role or "").casefold() != "pcc_admin":
            raise PermissionDenied("The active PMS role must be PCC_ADMIN.")
        current_admin = PmsConfiguration.objects.filter(key="pcc_admin_user_id").first()
        if current_admin and int(current_admin.value) != request.principal.user_id:
            raise PermissionDenied("Only the configured PCC_ADMIN may change PMS configuration.")
        if (
            key == "pcc_admin_user_id"
            and not current_admin
            and int(value or 0) != request.principal.user_id
        ):
            raise ValidationError(
                {"value": "The initial PCC_ADMIN must configure their own active user ID."}
            )
        if key not in self.ALLOWED:
            raise ValidationError({"key": "This PMS configuration key is not supported."})
        pre_filing = {
            Application.Status.DRAFT,
            Application.Status.SUBMITTED,
            Application.Status.UNDER_REVIEW,
            Application.Status.RESUBMITTED,
            Application.Status.NEEDS_REVISION,
            Application.Status.REJECTED,
            Application.Status.APPROVED,
            Application.Status.ATTORNEY_ASSIGNED,
            Application.Status.PENDING_REVIEW,
        }
        if key == "withdrawal_eligible_statuses" and (
            not isinstance(value, list) or any(v not in pre_filing for v in value)
        ):
            raise ValidationError(
                {"value": "Configure only valid pre-filing application statuses."}
            )
        if key == "appeal_period_days" and (
            not isinstance(value, int) or value < 1 or value > 3650
        ):
            raise ValidationError({"value": "Provide an allowed period in days."})
        if key == "deadline_alert_days" and (
            not isinstance(value, list) or any(not isinstance(v, int) or v < 1 for v in value)
        ):
            raise ValidationError({"value": "Provide positive alert intervals in days."})
        if key in {
            "budget_availability_required",
            "office_action_applicant_review_required",
            "withdrawal_requires_co_inventor_consent",
        } and not isinstance(value, bool):
            raise ValidationError({"value": "Provide a boolean value."})
        if key in {"deadline_escalation_user_ids", "budget_escalation_user_ids"} and (
            not isinstance(value, list) or any(not isinstance(v, int) or v < 1 for v in value)
        ):
            raise ValidationError({"value": "Provide a list of positive IAM user IDs."})
        if key == "pcc_admin_user_id" and (not isinstance(value, int) or value < 1):
            raise ValidationError({"value": "Provide one positive IAM user ID."})
        if key == "budget_escalation_threshold":
            try:
                threshold = Decimal(str(value))
            except (InvalidOperation, TypeError):
                raise ValidationError({"value": "Provide a non-negative amount."}) from None
            if threshold < 0:
                raise ValidationError({"value": "Provide a non-negative amount."})
        row, _ = PmsConfiguration.objects.update_or_create(
            key=key, defaults={"value": value, "updated_by_user_id": _p(request).user_id}
        )
        PmsAuditEvent.objects.create(
            actor_user_id=_p(request).user_id, action="configuration_updated", metadata={"key": key}
        )
        return Response(PmsConfigurationSerializer(row).data)


class PanelProfilesView(PmsAPIView):
    permission_classes = PMS

    def get(self, request):
        _need(request, "pms.panel.manage", "pms.workflow.manage", "pms.application.view_all")
        if _p(request).has_permission("pms.panel.manage") or _p(request).has_permission(
            "pms.workflow.manage"
        ):
            _need_pcc_admin(request)
        return Response(
            {
                "directors": DirectorProfileSerializer(
                    DirectorProfile.objects.order_by("user_id"), many=True
                ).data,
                "attorneys": AttorneyProfileSerializer(
                    AttorneyProfile.objects.order_by("user_id"), many=True
                ).data,
            }
        )

    def post(self, request):
        _need(request, "pms.panel.manage")
        _need_pcc_admin(request)
        kind = request.data.get("kind")
        serializer_cls = (
            DirectorProfileSerializer
            if kind == "director"
            else AttorneyProfileSerializer
            if kind == "attorney"
            else None
        )
        if not serializer_cls:
            raise ValidationError({"kind": "Use director or attorney."})
        serializer = serializer_cls(data=request.data.get("profile", {}))
        serializer.is_valid(raise_exception=True)
        profile, _ = serializer_cls.Meta.model.objects.update_or_create(
            user_id=serializer.validated_data["user_id"], defaults=serializer.validated_data
        )
        return Response(serializer_cls(profile).data, status=status.HTTP_200_OK)


class AuditTrailView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id=None):
        _need(request, "pms.audit.view", "pms.workflow.manage")
        if _p(request).has_permission("pms.workflow.manage"):
            _need_pcc_admin(request)
        qs = PmsAuditEvent.objects.all()
        if app_id:
            app = _application(request, app_id)
            qs = qs.filter(application=app)
        elif not _p(request).has_permission("pms.workflow.manage"):
            qs = qs.filter(actor_user_id=_p(request).user_id)
        return Response(PmsAuditEventSerializer(qs[:500], many=True).data)


class ReportsView(PmsAPIView):
    permission_classes = PMS

    def get(self, request):
        _need(request, "pms.report.view", "pms.report.view_self")
        principal = _p(request)
        if principal.has_permission("pms.workflow.manage"):
            _need_pcc_admin(request)
            qs = Application.objects.all()
        elif principal.has_permission("pms.application.review"):
            qs = Application.objects.filter(assigned_director_user_id=principal.user_id)
        elif principal.has_any_permission("pms.legal_opinion.create", "pms.office_action.record"):
            qs = Application.objects.filter(assigned_attorney_user_id=principal.user_id)
        else:
            qs = Application.objects.filter(applicant_user_id=principal.user_id)
        PmsAuditEvent.objects.create(
            actor_user_id=principal.user_id,
            action="report_accessed",
            metadata={"scope_count": qs.count()},
        )
        return Response(
            {
                "total": qs.count(),
                "by_status": list(
                    qs.values("status").annotate(count=Count("id")).order_by("status")
                ),
                "applications": ApplicationSerializer(
                    qs.order_by("-created_at")[:200], many=True
                ).data,
            }
        )


class LegalAdviceView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, app_id):
        _need(request, "pms.legal_opinion.create")
        app = _application(request, app_id, write=True)
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may record legal advice.")
        advice = (request.data.get("advice") or "").strip()
        stage = (request.data.get("lifecycle_stage") or "").strip()
        if not advice or not stage:
            raise ValidationError({"detail": "Advice and lifecycle stage are required."})
        row = LegalAdviceRecord.objects.create(
            application=app,
            attorney_user_id=_p(request).user_id,
            advice=advice,
            lifecycle_stage=stage,
        )
        services._audit(
            app,
            _p(request).user_id,
            "legal_advice_recorded",
            app.status,
            app.status,
            {"advice_id": row.pk},
        )
        return Response(
            {
                "id": row.pk,
                "lifecycle_stage": row.lifecycle_stage,
                "advice": row.advice,
                "created_at": row.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class PriorArtSearchView(PmsAPIView):
    permission_classes = PMS

    def post(self, request):
        _need(request, "pms.prior_art.search")
        query = (request.data.get("query") or "").strip()
        app_id = request.data.get("application_id")
        if not query:
            raise ValidationError({"query": "Enter a search query."})
        app = _application(request, app_id) if app_id else None
        session = PriorArtSearchSession.objects.create(
            application=app,
            user_id=_p(request).user_id,
            query=query[:500],
            source=request.data.get("source", ""),
        )
        references = request.data.get("references", [])
        if not isinstance(references, list):
            raise ValidationError({"references": "Provide a list of selected external references."})
        created = []
        for item in references[:50]:
            if not isinstance(item, dict) or not (
                item.get("title") and item.get("external_reference")
            ):
                raise ValidationError(
                    {"references": "Each reference needs a title and external reference ID."}
                )
            ref = PriorArtReference.objects.create(
                session=session,
                title=str(item["title"])[:500],
                external_reference=str(item["external_reference"])[:255],
                source_url=item.get("source_url", ""),
                relevance_score=item.get("relevance_score"),
            )
            created.append(
                {"id": ref.pk, "title": ref.title, "external_reference": ref.external_reference}
            )
        if app:
            services._audit(
                app,
                _p(request).user_id,
                "prior_art_search_recorded",
                app.status,
                app.status,
                {"search_session_id": session.pk},
            )
        return Response(
            {
                "id": session.pk,
                "query": session.query,
                "source": session.source,
                "results": created,
                "integration_available": False,
                "message": "Search session recorded. No external prior-art source is configured.",
            },
            status=status.HTTP_201_CREATED,
        )


class PriorArtReferenceAttachView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, reference_id):
        _need(request, "pms.prior_art.search")
        reference = get_object_or_404(PriorArtReference, pk=reference_id)
        app_id = request.data.get("application_id")
        app = _application(request, app_id, write=True)
        reference.attached_to_application = app
        reference.save(update_fields=["attached_to_application"])
        services._audit(
            app,
            _p(request).user_id,
            "prior_art_reference_attached",
            app.status,
            app.status,
            {"prior_art_reference_id": reference.pk},
        )
        return Response(
            {
                "id": reference.pk,
                "application_id": app.pk,
                "external_reference": reference.external_reference,
            }
        )


class LicensingRequestListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(request, "pms.licensing.submit", "pms.licensing.review", "pms.workflow.manage")
        app = _application(request, app_id)
        rows = app.licensing_requests.all()
        return Response(
            [
                {
                    "id": row.pk,
                    "status": row.status,
                    "request_details": row.request_details,
                    "confidentiality": row.confidentiality,
                    "agreement_reference": row.agreement_reference,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        )

    def post(self, request, app_id):
        _need(request, "pms.licensing.submit")
        app = _application(request, app_id, write=True)
        details = (request.data.get("request_details") or "").strip()
        if not details:
            raise ValidationError(
                {"request_details": "Describe the licensing or technology-transfer request."}
            )
        row = LicensingRequest.objects.create(
            application=app,
            submitted_by_user_id=_p(request).user_id,
            request_details=details,
            confidentiality=request.data.get("confidentiality", "confidential"),
        )
        services._audit(
            app,
            _p(request).user_id,
            "licensing_request_submitted",
            app.status,
            app.status,
            {"licensing_request_id": row.pk},
        )
        return Response(
            {"id": row.pk, "status": row.status, "created_at": row.created_at},
            status=status.HTTP_201_CREATED,
        )


class LicensingRequestReviewView(PmsAPIView):
    permission_classes = PMS

    def patch(self, request, request_id):
        _need(request, "pms.licensing.review")
        row = get_object_or_404(
            LicensingRequest.objects.select_related("application"), pk=request_id
        )
        if (
            not _p(request).has_permission("pms.workflow.manage")
            and row.application.assigned_director_user_id != _p(request).user_id
        ):
            raise PermissionDenied(
                "Only the assigned Director or PCC_ADMIN may review this request."
            )
        transitions = {
            "submitted": {"under_review", "closed"},
            "under_review": {"negotiating", "agreement_recorded", "closed"},
            "negotiating": {"agreement_recorded", "closed"},
            "agreement_recorded": {"closed"},
        }
        new_status = request.data.get("status")
        if new_status not in transitions.get(row.status, set()):
            raise ValidationError({"status": "Choose a valid next licensing-request status."})
        row.status = new_status
        if "negotiation_notes" in request.data:
            row.negotiation_notes = request.data["negotiation_notes"]
        if "agreement_reference" in request.data:
            row.agreement_reference = request.data["agreement_reference"]
        if (
            new_status == LicensingRequest.Status.AGREEMENT_RECORDED
            and not row.agreement_reference.strip()
        ):
            raise ValidationError({"agreement_reference": "Record the final agreement reference."})
        row.save(update_fields=["status", "negotiation_notes", "agreement_reference", "updated_at"])
        services._audit(
            row.application,
            _p(request).user_id,
            "licensing_request_updated",
            row.application.status,
            row.application.status,
            {"licensing_request_id": row.pk, "status": new_status},
        )
        return Response(
            {"id": row.pk, "status": row.status, "agreement_reference": row.agreement_reference}
        )


class MaintenanceCycleListCreateView(PmsAPIView):
    permission_classes = PMS

    def get(self, request, app_id):
        _need(
            request, "pms.maintenance.manage", "pms.maintenance.decide", "pms.application.view_self"
        )
        app = _application(request, app_id)
        return Response(
            [
                {
                    "id": row.pk,
                    "jurisdiction": row.jurisdiction,
                    "due_date": row.due_date,
                    "schedule_source": row.schedule_source,
                    "status": row.status,
                    "next_cycle_due_date": row.next_cycle_due_date,
                }
                for row in app.maintenance_cycles.order_by("due_date")
            ]
        )

    def post(self, request, app_id):
        _need(request, "pms.maintenance.manage")
        app = _application(request, app_id, write=True)
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may create maintenance cycles.")
        if app.status != Application.Status.GRANTED:
            raise ValidationError(
                {"detail": "Post-grant tracking is available only for granted patents."}
            )
        try:
            due = date.fromisoformat(request.data.get("due_date", ""))
        except (TypeError, ValueError):
            raise ValidationError({"due_date": "Enter a valid ISO date."}) from None
        jurisdiction = (request.data.get("jurisdiction") or "").strip()
        if not jurisdiction:
            raise ValidationError({"jurisdiction": "This field is required."})
        schedule_source = (request.data.get("schedule_source") or "").strip()
        if not schedule_source:
            raise ValidationError(
                {
                    "schedule_source": (
                        "Record the source used to determine this maintenance deadline."
                    )
                }
            )
        row = MaintenanceCycle.objects.create(
            application=app,
            jurisdiction=jurisdiction,
            due_date=due,
            schedule_source=schedule_source,
        )
        services._audit(
            app,
            _p(request).user_id,
            "maintenance_cycle_created",
            app.status,
            app.status,
            {"maintenance_cycle_id": row.pk},
        )
        return Response(
            {"id": row.pk, "status": row.status, "due_date": row.due_date},
            status=status.HTTP_201_CREATED,
        )


class MaintenanceDecisionRequestView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, cycle_id):
        _need(request, "pms.maintenance.manage")
        row = get_object_or_404(MaintenanceCycle.objects.select_related("application"), pk=cycle_id)
        app = row.application
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may request renewal decisions.")
        if app.status != Application.Status.GRANTED or row.status != MaintenanceCycle.Status.ACTIVE:
            raise ValidationError(
                {"detail": "This maintenance cycle is not active for a granted patent."}
            )
        row.status = MaintenanceCycle.Status.DECISION_REQUESTED
        row.save(update_fields=["status"])
        if app.assigned_director_user_id:
            PmsNotification.objects.get_or_create(
                dedupe_key=f"maintenance:{row.pk}:decision-request:{app.assigned_director_user_id}",
                defaults={
                    "recipient_user_id": app.assigned_director_user_id,
                    "application": app,
                    "event": "maintenance.decision_requested",
                    "subject": "Patent maintenance decision requested",
                    "body": (f"Decide whether to renew the patent before {row.due_date}."),
                },
            )
        services._audit(
            app,
            _p(request).user_id,
            "maintenance_decision_requested",
            app.status,
            app.status,
            {"maintenance_cycle_id": row.pk},
        )
        return Response({"id": row.pk, "status": row.status})


class MaintenanceDecisionView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, cycle_id):
        _need(request, "pms.maintenance.decide")
        row = get_object_or_404(MaintenanceCycle.objects.select_related("application"), pk=cycle_id)
        app = row.application
        if app.assigned_director_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Director may decide this renewal.")
        if row.status != MaintenanceCycle.Status.DECISION_REQUESTED:
            raise ValidationError({"detail": "A maintenance decision has not been requested."})
        choice = request.data.get("decision")
        if choice not in ("renew", "do_not_renew"):
            raise ValidationError({"decision": "Choose renew or do_not_renew."})
        row.status = (
            MaintenanceCycle.Status.RENEWAL_APPROVED
            if choice == "renew"
            else MaintenanceCycle.Status.DO_NOT_RENEW
        )
        row.decision_by_user_id = _p(request).user_id
        row.decision_at = timezone.now()
        row.save(update_fields=["status", "decision_by_user_id", "decision_at"])
        services._audit(
            app,
            _p(request).user_id,
            "maintenance_decision_recorded",
            app.status,
            app.status,
            {"maintenance_cycle_id": row.pk, "decision": choice},
        )
        return Response({"id": row.pk, "status": row.status})


class MaintenanceActionRecordView(PmsAPIView):
    permission_classes = PMS

    def post(self, request, cycle_id):
        _need(request, "pms.maintenance.manage")
        row = get_object_or_404(MaintenanceCycle.objects.select_related("application"), pk=cycle_id)
        app = row.application
        if app.assigned_attorney_user_id != _p(request).user_id:
            raise PermissionDenied("Only the assigned Attorney may record the maintenance action.")
        if row.status != MaintenanceCycle.Status.RENEWAL_APPROVED:
            raise ValidationError({"detail": "A Director renewal approval is required first."})
        reference = (request.data.get("transaction_reference") or "").strip()
        if not reference:
            raise ValidationError(
                {"transaction_reference": "Record the maintenance transaction reference."}
            )
        next_due = request.data.get("next_cycle_due_date")
        if next_due:
            try:
                row.next_cycle_due_date = date.fromisoformat(next_due)
            except ValueError:
                raise ValidationError({"next_cycle_due_date": "Enter a valid ISO date."}) from None
        row.transaction_reference = reference
        row.status = MaintenanceCycle.Status.RENEWED
        row.save(update_fields=["transaction_reference", "next_cycle_due_date", "status"])
        if row.next_cycle_due_date:
            MaintenanceCycle.objects.create(
                application=app, jurisdiction=row.jurisdiction, due_date=row.next_cycle_due_date
            )
        services._audit(
            app,
            _p(request).user_id,
            "maintenance_action_recorded",
            app.status,
            app.status,
            {"maintenance_cycle_id": row.pk, "transaction_reference": reference},
        )
        return Response(
            {"id": row.pk, "status": row.status, "next_cycle_due_date": row.next_cycle_due_date}
        )


class DeadlineListView(PmsAPIView):
    permission_classes = PMS

    def get(self, request):
        _need(request, "pms.deadline.view", "pms.workflow.manage", "pms.application.view_self")
        principal = _p(request)
        rows = Deadline.objects.select_related("application")
        if principal.has_permission("pms.workflow.manage"):
            _need_pcc_admin(request)
        elif principal.has_permission("pms.application.review"):
            rows = rows.filter(application__assigned_director_user_id=principal.user_id)
        elif principal.has_any_permission("pms.legal_opinion.create", "pms.office_action.respond"):
            rows = rows.filter(application__assigned_attorney_user_id=principal.user_id)
        else:
            rows = rows.filter(application__applicant_user_id=principal.user_id)
        return Response(
            [
                {
                    "id": row.pk,
                    "application_id": row.application_id,
                    "application_number": row.application.application_number,
                    "kind": row.kind,
                    "due_at": row.due_at,
                    "status": row.status,
                    "source": row.source,
                }
                for row in rows.order_by("due_at")[:500]
            ]
        )
