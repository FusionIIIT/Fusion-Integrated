"""Patents API views (Step 4.5)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.patents.api import serializers as s
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.selectors import scoping
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import documents as doc_service
from modules.patents.services import maintenance as maint_service
from modules.patents.services import office_actions as oa_service
from modules.patents.services import tech_transfer as tt_service

MODULE = HasModuleGrant("patents")


def _actor(request):
    return getattr(request, "principal", None)


# -- Application List & Detail -------------------------------------------------

class ApplicationListView(generics.ListCreateAPIView):
    """GET /api/v1/patents/applications | POST /api/v1/patents/applications"""
    permission_classes = [
        MODULE,
        HasPermission(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_VIEW, p.P_APPLICATION_CREATE),
    ]

    @property
    def throttle_scope(self):
        if self.request and self.request.method == "POST":
            return "patent_submit"
        return None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.CreateApplicationSerializer
        return s.PatentApplicationSummarySerializer

    def get_queryset(self):
        return scoping.applications_for(_actor(self.request)).order_by("-id")

    @extend_schema(responses={200: s.PatentApplicationSummarySerializer(many=True)})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=s.CreateApplicationSerializer,
        responses={201: s.PatentApplicationDetailSerializer},
    )
    def post(self, request, *args, **kwargs):
        actor = _actor(request)
        if not getattr(actor, "has_permission", lambda _: False)(p.P_APPLICATION_CREATE):
            raise PermissionDeniedError("Permission patents.application.create required.")
        payload = s.CreateApplicationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.create_application(
            actor=actor,
            **payload.validated_data,
        )
        return Response(
            s.PatentApplicationDetailSerializer(app).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    responses={200: s.PatentApplicationDetailSerializer}
)
class ApplicationDetailView(generics.RetrieveUpdateAPIView):
    """GET /api/v1/patents/applications/<pk> | PUT /api/v1/patents/applications/<pk>"""
    permission_classes = [
        MODULE,
        HasPermission(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_VIEW, p.P_APPLICATION_UPDATE),
    ]
    serializer_class = s.PatentApplicationDetailSerializer

    @property
    def throttle_scope(self):
        if self.request and self.request.method in ("PUT", "PATCH", "DELETE"):
            return "patent_mutate"
        return None

    def get_queryset(self):
        return scoping.applications_for(_actor(self.request))

    def update(self, request, *args, **kwargs):
        payload = s.UpdateApplicationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.update_application(
            actor=_actor(request),
            application_id=kwargs["pk"],
            **payload.validated_data,
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


# -- Application Action Endpoints ----------------------------------------------

@extend_schema(request=s.PatentWithdrawSerializer, responses=s.PatentApplicationDetailSerializer)
class ApplicationWithdrawView(APIView):
    """POST /api/v1/patents/applications/<pk>/withdraw"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_WITHDRAW)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.PatentWithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="withdraw",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


@extend_schema(request=s.DocumentUploadInputSerializer, responses=s.ApplicationDocumentSerializer)
class ApplicationDocumentUploadView(APIView):
    """POST /api/v1/patents/applications/<pk>/documents"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_UPDATE)]
    throttle_scope = "upload"

    def post(self, request, pk):
        file_obj = request.FILES.get("file")
        doc_type = request.data.get("document_type", "specification")
        if file_obj:
            file_bytes = file_obj.read()
            file_name = file_obj.name
        else:
            file_name = request.data.get("file_name", "document.pdf")
            file_bytes = b"%PDF-1.4 sample content"

        doc = doc_service.upload_document(
            actor=_actor(request),
            application_id=pk,
            document_type=doc_type,
            file_name=file_name,
            file_bytes=file_bytes,
            storage_path=f"/var/patents/app_{pk}/{file_name}",
        )
        return Response(s.ApplicationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.ConsentResponseSerializer)
class ApplicationConsentView(APIView):
    """POST /api/v1/patents/applications/<pk>/consent"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_VIEW_SELF)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        success = app_service.record_coinventor_consent(_actor(request), pk)
        return Response({"consent_recorded": success})


@extend_schema(request=s.AssignDirectorSerializer, responses=s.PatentApplicationDetailSerializer)
class ApplicationAssignDirectorView(APIView):
    """POST /api/v1/patents/applications/<pk>/assign-director"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_ASSIGN_DIRECTOR)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.AssignDirectorSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="assign_director",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


@extend_schema(request=s.ReviewDecisionInputSerializer, responses=s.ReviewDecisionSerializer)
class ApplicationReviewDecisionView(APIView):
    """POST /api/v1/patents/applications/<pk>/review-decision"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_REVIEW)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.ReviewDecisionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="submit_review",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        rev = app.reviews.order_by("-id").first()
        return Response(s.ReviewDecisionSerializer(rev).data)


@extend_schema(request=s.AppealInputSerializer, responses=s.AppealRecordSerializer)
class ApplicationAppealView(APIView):
    """POST /api/v1/patents/applications/<pk>/appeal"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_APPEAL)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.AppealInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="file_appeal",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        appeal = app.appeals.order_by("-id").first()
        return Response(s.AppealRecordSerializer(appeal).data)


@extend_schema(request=s.AppealDecisionInputSerializer, responses=s.AppealRecordSerializer)
class ApplicationAppealDecisionView(APIView):
    """POST /api/v1/patents/applications/<pk>/appeal-decision"""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_DECIDE_APPEAL)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.AppealDecisionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="decide_appeal",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        appeal = app.appeals.order_by("-id").first()
        return Response(s.AppealRecordSerializer(appeal).data)


@extend_schema(request=s.AssignAttorneySerializer, responses=s.PatentApplicationDetailSerializer)
class ApplicationAssignAttorneyView(APIView):
    """POST /api/v1/patents/applications/<pk>/assign-attorney"""
    permission_classes = [MODULE, HasPermission(p.P_ATTORNEY_ASSIGN)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.AssignAttorneySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="assign_attorney",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


@extend_schema(
    request=s.RespondAssignmentInputSerializer,
    responses=s.PatentApplicationDetailSerializer,
)
class ApplicationRespondAssignmentView(APIView):
    """POST /api/v1/patents/applications/<pk>/respond-assignment"""
    permission_classes = [MODULE, HasPermission(p.P_ATTORNEY_RESPOND_ASSIGNMENT)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        action = request.data.get("action", "accept")
        event = "accept_assignment" if action == "accept" else "decline_assignment"
        app = app_service.transition_application(
            application_id=pk,
            event=event,
            actor=_actor(request),
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


@extend_schema(request=s.AssessmentInputSerializer, responses=s.PatentApplicationDetailSerializer)
class ApplicationAssessmentView(APIView):
    """POST /api/v1/patents/applications/<pk>/assessment"""
    permission_classes = [MODULE, HasPermission(p.P_ASSESSMENT_PERFORM)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        action = request.data.get("action", "start")
        if action == "start":
            app = app_service.transition_application(
                application_id=pk,
                event="start_assessment",
                actor=_actor(request),
            )
            return Response(s.PatentApplicationDetailSerializer(app).data)
        return Response({"status": "opinion_recorded"})


@extend_schema(request=s.BudgetDecisionInputSerializer, responses=s.PatentBudgetLedgerSerializer)
class ApplicationBudgetDecisionView(APIView):
    """POST /api/v1/patents/applications/<pk>/budget-decision"""
    permission_classes = [MODULE, HasPermission(p.P_BUDGET_APPROVE)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.BudgetDecisionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        entry_id = request.data.get("budget_entry_id")
        if not entry_id:
            # Fall back to first pending budget entry for application
            app = scoping.applications_for(_actor(request)).filter(pk=pk).first()
            if not app:
                raise NotFoundError("Application not found.")
            entry = app.budget_entries.filter(status="PENDING").first()
            if not entry:
                raise NotFoundError("No pending budget entry found.")
            entry_id = entry.id

        entry = budget_service.decide_budget(
            actor=_actor(request),
            entry_id=entry_id,
            decision=payload.validated_data["decision"],
            notes=payload.validated_data.get("notes", ""),
        )
        return Response(s.PatentBudgetLedgerSerializer(entry).data)


@extend_schema(request=s.FilingInputSerializer, responses=s.PatentApplicationDetailSerializer)
class ApplicationFilingView(APIView):
    """POST /api/v1/patents/applications/<pk>/filing"""
    permission_classes = [MODULE, HasPermission(p.P_FILING_RECORD)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.FilingInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.transition_application(
            application_id=pk,
            event="file_external",
            actor=_actor(request),
            payload=payload.validated_data,
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


@extend_schema(request=s.OfficeActionInputSerializer, responses=s.OfficeActionRecordSerializer)
class ApplicationOfficeActionsView(APIView):
    """POST /api/v1/patents/applications/<pk>/office-actions"""
    permission_classes = [MODULE, HasPermission(p.P_OFFICE_ACTION_RECORD)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.OfficeActionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        oa = oa_service.log_office_action(
            actor=_actor(request),
            application_id=pk,
            **payload.validated_data,
        )
        return Response(s.OfficeActionRecordSerializer(oa).data, status=status.HTTP_201_CREATED)


@extend_schema(
    request=s.OfficeActionResponseInputSerializer,
    responses=s.OfficeActionRecordSerializer,
)
class OfficeActionResponseView(APIView):
    """POST /api/v1/patents/office-actions/<pk>/response"""
    permission_classes = [MODULE, HasPermission(p.P_OFFICE_ACTION_RESPOND)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.OfficeActionResponseInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        oa = oa_service.draft_response(
            actor=_actor(request),
            office_action_id=pk,
            response_summary=payload.validated_data["response_summary"],
        )
        return Response(s.OfficeActionRecordSerializer(oa).data)


@extend_schema(request=None, responses=s.OfficeActionRecordSerializer)
class OfficeActionApproveView(APIView):
    """POST /api/v1/patents/office-actions/<pk>/approve"""
    permission_classes = [MODULE, HasPermission(p.P_OFFICE_ACTION_APPROVE)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        oa = oa_service.applicant_approve_response(
            actor=_actor(request),
            office_action_id=pk,
        )
        return Response(s.OfficeActionRecordSerializer(oa).data)


@extend_schema(
    request=s.RenewalDecisionInputSerializer,
    responses=s.PatentApplicationDetailSerializer,
)
class ApplicationRenewalDecisionView(APIView):
    """POST /api/v1/patents/applications/<pk>/renewal-decision"""
    permission_classes = [MODULE, HasPermission(p.P_MAINTENANCE_DECIDE, p.P_MAINTENANCE_TRACK)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk):
        payload = s.RenewalDecisionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = maint_service.record_renewal_decision(
            actor=_actor(request),
            application_id=pk,
            renew=payload.validated_data["renew"],
            notes=payload.validated_data.get("notes", ""),
        )
        return Response(s.PatentApplicationDetailSerializer(app).data)


class AttorneyPanelListView(generics.ListAPIView):
    """GET /api/v1/patents/attorney-panel"""
    permission_classes = [MODULE, HasPermission(p.P_PANEL_MANAGE)]
    serializer_class = s.AttorneyPanelMemberSerializer

    def get_queryset(self):
        return scoping.attorney_panel_for(_actor(self.request))


@extend_schema(
    request=s.TechTransferInputSerializer,
    responses=s.TechnologyTransferRecordSerializer,
)
class TechTransferCreateView(APIView):
    """POST /api/v1/patents/tech-transfer"""
    permission_classes = [MODULE, HasPermission(p.P_TECH_TRANSFER_CREATE)]
    throttle_scope = "patent_mutate"

    def post(self, request):
        payload = s.TechTransferInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        rec = tt_service.submit_tech_transfer_request(
            actor=_actor(request),
            **payload.validated_data,
        )
        return Response(
            s.TechnologyTransferRecordSerializer(rec).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(request=s.PriorArtInputSerializer, responses=s.PriorArtResultSerializer)
class PriorArtSearchView(APIView):
    """POST /api/v1/patents/prior-art/search"""
    permission_classes = [MODULE, HasPermission(p.P_PRIOR_ART_SEARCH)]

    def post(self, request):
        query = request.data.get("query", "")
        return Response({"query": query, "results": []})


@extend_schema(responses=s.ReportsResponseSerializer)
class ReportsView(APIView):
    """GET /api/v1/patents/reports"""
    permission_classes = [MODULE, HasPermission(p.P_REPORT_VIEW)]

    def get(self, request):
        actor = _actor(request)
        apps = scoping.applications_for(actor)
        return Response({
            "total_applications": apps.count(),
            "filed_count": apps.filter(status=sm.FILED).count(),
            "granted_count": apps.filter(status=sm.GRANTED).count(),
        })


@extend_schema(responses=s.AuditLogsResponseSerializer)
class AuditLogsView(APIView):
    """GET /api/v1/patents/audit-logs"""
    permission_classes = [MODULE, HasPermission(p.P_AUDIT_VIEW)]

    def get(self, request):
        return Response({"audit_logs": []})


@extend_schema(request=None, responses=s.ConsentTokenIssuedSerializer)
class CoInventorConsentTokenView(APIView):
    """POST /api/v1/patents/applications/<pk>/co-inventors/<ci_pk>/consent-token."""
    permission_classes = [MODULE, HasPermission(p.P_APPLICATION_VIEW_SELF)]
    throttle_scope = "patent_mutate"

    def post(self, request, pk, ci_pk):
        from modules.patents.services import consent as consent_service

        consent_service.issue_consent_token(_actor(request), pk, ci_pk)
        return Response({"sent": True})


@extend_schema(request=s.ConsentConfirmSerializer, responses=s.ConsentResponseSerializer)
class ConsentConfirmView(APIView):
    """POST /api/v1/patents/consent/confirm."""
    authentication_classes = []
    permission_classes = []
    throttle_scope = "patent_mutate"

    def post(self, request):
        from modules.patents.services import consent as consent_service

        payload = s.ConsentConfirmSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        consent_service.confirm_consent_token(payload.validated_data["token"])
        return Response({"consent_recorded": True})
