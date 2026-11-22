"""HTTP layer for SPACS: parse, scope, delegate, serialise."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.spacs.api import serializers as s
from modules.spacs.selectors import applications as app_selectors
from modules.spacs.selectors import audit as audit_selectors
from modules.spacs.selectors import awards as award_selectors
from modules.spacs.selectors import catalogue as cat_selectors
from modules.spacs.services import applications as app_service
from modules.spacs.services import awards as award_service
from modules.spacs.services import catalogue as cat_service
from modules.spacs.services import documents as doc_service

MODULE = HasModuleGrant("spacs")


def _actor(request):
    return getattr(request, "principal", None)


# --- Catalogue Endpoints (CFR-SPACS-001, 002) ---

class CatalogueListView(generics.ListAPIView):
    """Browse published scholarship and award opportunities."""
    permission_classes = [MODULE, HasPermission("spacs.catalogue.view")]
    serializer_class = s.SchemeCatalogueSerializer

    def get_queryset(self):
        return cat_selectors.visible_catalogue_entries(_actor(self.request))


class CatalogueDetailView(generics.RetrieveAPIView):
    """Retrieve opportunity metadata and active policy criteria."""
    permission_classes = [MODULE, HasPermission("spacs.catalogue.view")]
    serializer_class = s.SchemeCatalogueSerializer

    def get_object(self):
        obj = cat_selectors.get_catalogue_entry(self.kwargs["pk"], _actor(self.request))
        if obj is None:
            raise NotFoundError("Catalogue entry not found.")
        return obj


class CatalogueCreateView(generics.GenericAPIView):
    """SPACS Convener creates a new draft catalogue entry (AFR-SPACS-003)."""
    permission_classes = [MODULE, HasPermission("spacs.catalogue.manage")]
    serializer_class = s.SchemeCatalogueSerializer

    def post(self, request):
        data = request.data
        code = data.get("code")
        name = data.get("name")
        scheme_type = data.get("scheme_type", "scholarship")
        description = data.get("description", "")
        if not code or not name:
            raise BadRequestError("Both 'code' and 'name' are required.")

        scheme = cat_service.create_catalogue_entry(
            code=code,
            name=name,
            scheme_type=scheme_type,
            description=description,
            actor=_actor(request),
        )
        return Response(s.SchemeCatalogueSerializer(scheme).data, status=status.HTTP_201_CREATED)


class CatalogueVersionCreateView(generics.GenericAPIView):
    """SPACS Convener creates a draft policy version for a scheme (AFR-SPACS-004)."""
    permission_classes = [MODULE, HasPermission("spacs.catalogue.manage")]
    serializer_class = s.SchemePolicyVersionSerializer

    def post(self, request, pk):
        data = request.data
        version = cat_service.create_policy_version(
            scheme_id=pk,
            title=data.get("title", ""),
            description=data.get("description", ""),
            eligibility_criteria=data.get("eligibility_criteria"),
            required_documents=data.get("required_documents"),
            candidate_source_method=data.get("candidate_source_method", "application"),
            is_renewable=data.get("is_renewable", False),
            renewal_rules=data.get("renewal_rules"),
            policy_approval_reference=data.get("policy_approval_reference", ""),
            policy_approved_by=data.get("policy_approved_by", ""),
            effective_from=data.get("effective_from"),
            effective_to=data.get("effective_to"),
            application_window_start=data.get("application_window_start"),
            application_window_end=data.get("application_window_end"),
            renewal_window_start=data.get("renewal_window_start"),
            renewal_window_end=data.get("renewal_window_end"),
            sla_verification_days=data.get("sla_verification_days", 7),
            sla_decision_days=data.get("sla_decision_days", 14),
            actor=_actor(request),
        )
        return Response(s.SchemePolicyVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class CataloguePublishView(generics.GenericAPIView):
    """SPACS Convener publishes an approved catalogue version (AFR-SPACS-005, UC-SPACS-023)."""
    permission_classes = [MODULE, HasPermission("spacs.catalogue.manage")]
    serializer_class = s.SchemePolicyVersionSerializer

    def post(self, request, pk, version_id):
        version = cat_service.publish_policy_version(
            version_id=version_id,
            actor=_actor(request),
        )
        return Response(s.SchemePolicyVersionSerializer(version).data)


class CatalogueRetireView(generics.GenericAPIView):
    """SPACS Convener retires a catalogue entry prospectively (AFR-SPACS-006, UC-SPACS-012)."""
    permission_classes = [MODULE, HasPermission("spacs.catalogue.manage")]
    serializer_class = s.CatalogueRetireSerializer

    @extend_schema(request=s.CatalogueRetireSerializer, responses={200: s.SchemeCatalogueSerializer})
    def post(self, request, pk):
        ser = s.CatalogueRetireSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = ser.validated_data.get("reason", "")
        scheme = cat_service.retire_catalogue_entry(
            scheme_id=pk,
            reason=reason,
            actor=_actor(request),
        )
        return Response(s.SchemeCatalogueSerializer(scheme).data)


# --- Scholarship Application Endpoints ---

class ApplicationListView(generics.ListAPIView):
    """List applications in caller's scope (own applications for student, assigned/queue for staff)."""
    permission_classes = [
        MODULE,
        HasPermission("spacs.application.view_self", "spacs.application.view", "spacs.application.approve"),
    ]
    serializer_class = s.ScholarshipApplicationSerializer

    def get_queryset(self):
        qs = app_selectors.visible_applications(_actor(self.request))
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class ApplicationDetailView(generics.RetrieveAPIView):
    """Retrieve full application details, documents, and transition history."""
    permission_classes = [
        MODULE,
        HasPermission("spacs.application.view_self", "spacs.application.view", "spacs.application.approve"),
    ]
    serializer_class = s.ScholarshipApplicationSerializer

    def get_object(self):
        obj = app_selectors.get_application(self.kwargs["pk"], _actor(self.request))
        if obj is None:
            raise NotFoundError("Application not found.")
        return obj


class ApplicationCreateView(generics.GenericAPIView):
    """Student creates a draft or submits a scholarship application (UC-SPACS-001)."""
    permission_classes = [MODULE, HasPermission("spacs.application.create")]
    serializer_class = s.ScholarshipApplicationCreateSerializer

    @extend_schema(request=s.ScholarshipApplicationCreateSerializer, responses={201: s.ScholarshipApplicationSerializer})
    def post(self, request):
        ser = s.ScholarshipApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        app = app_service.create_draft_application(
            scheme_id=vd["scheme_id"],
            academic_cycle=vd["academic_cycle"],
            application_data=vd["application_data"],
            actor=_actor(request),
        )

        if vd.get("submit"):
            app = app_service.submit_application(
                application_id=app.id,
                application_data=vd["application_data"],
                student_facts=vd.get("facts"),
                actor=_actor(request),
            )
        return Response(s.ScholarshipApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationSubmitView(generics.GenericAPIView):
    """Student submits an existing draft application (UC-SPACS-001)."""
    permission_classes = [MODULE, HasPermission("spacs.application.create")]
    serializer_class = s.ApplicationSubmitSerializer

    @extend_schema(request=s.ApplicationSubmitSerializer, responses={200: s.ScholarshipApplicationSerializer})
    def post(self, request, pk):
        ser = s.ApplicationSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        app = app_service.submit_application(
            application_id=pk,
            application_data=vd.get("application_data"),
            student_facts=vd.get("facts"),
            actor=_actor(request),
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


class ApplicationModifyView(generics.GenericAPIView):
    """Student modifies an application in editable/correction state (UC-SPACS-003)."""
    permission_classes = [MODULE, HasPermission("spacs.application.update")]
    serializer_class = s.ScholarshipApplicationModifySerializer

    @extend_schema(request=s.ScholarshipApplicationModifySerializer, responses={200: s.ScholarshipApplicationSerializer})
    def patch(self, request, pk):
        ser = s.ScholarshipApplicationModifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        app = app_service.modify_application(
            application_id=pk,
            updated_data=vd.get("application_data"),
            resubmit=vd.get("resubmit", False),
            actor=_actor(request),
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


class ApplicationWithdrawView(generics.GenericAPIView):
    """Student withdraws an application before final decision (UC-SPACS-004)."""
    permission_classes = [MODULE, HasPermission("spacs.application.delete")]
    serializer_class = s.ScholarshipApplicationWithdrawSerializer

    @extend_schema(request=s.ScholarshipApplicationWithdrawSerializer, responses={200: s.ScholarshipApplicationSerializer})
    def post(self, request, pk):
        ser = s.ScholarshipApplicationWithdrawSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = ser.validated_data.get("reason", "")

        app = app_service.withdraw_application(
            application_id=pk,
            reason=reason,
            actor=_actor(request),
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


class ApplicationVerifyView(generics.GenericAPIView):
    """SPACS Assistant records verification findings or concern (UC-SPACS-002, BR-SPACS-006)."""
    permission_classes = [MODULE, HasPermission("spacs.application.review")]
    serializer_class = s.ScholarshipApplicationVerifySerializer

    @extend_schema(request=s.ScholarshipApplicationVerifySerializer, responses={200: s.ScholarshipApplicationSerializer})
    def post(self, request, pk):
        ser = s.ScholarshipApplicationVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        app = app_service.verify_application(
            application_id=pk,
            action_type=vd["action"],
            findings=vd.get("findings"),
            reason=vd.get("reason", ""),
            actor=_actor(request),
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


class ApplicationDecideView(generics.GenericAPIView):
    """SPACS Convener records final decision or returns for correction (UC-SPACS-006, BR-SPACS-018)."""
    permission_classes = [MODULE, HasPermission("spacs.application.approve")]
    serializer_class = s.ScholarshipApplicationDecideSerializer

    @extend_schema(request=s.ScholarshipApplicationDecideSerializer, responses={200: s.ScholarshipApplicationSerializer})
    def post(self, request, pk):
        ser = s.ScholarshipApplicationDecideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        app = app_service.decide_application(
            application_id=pk,
            decision=vd["decision"],
            reason=vd.get("reason", ""),
            actor=_actor(request),
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


class RenewalApplicationView(generics.GenericAPIView):
    """Student applies for renewal of an awarded scholarship (UC-SPACS-015, CW-SPACS-02)."""
    permission_classes = [MODULE, HasPermission("spacs.application.create")]
    serializer_class = s.ScholarshipRenewalSerializer

    @extend_schema(request=s.ScholarshipRenewalSerializer, responses={201: s.ScholarshipApplicationSerializer})
    def post(self, request):
        ser = s.ScholarshipRenewalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        renewal = app_service.submit_renewal(
            prior_application_id=vd["prior_application_id"],
            academic_cycle=vd["academic_cycle"],
            renewal_data=vd.get("renewal_data"),
            current_facts=vd.get("facts"),
            actor=_actor(request),
        )
        return Response(s.ScholarshipApplicationSerializer(renewal).data, status=status.HTTP_201_CREATED)


class ApplicationExportView(generics.GenericAPIView):
    """Student or authorized staff downloads/exports application details (UC-SPACS-007, BR-SPACS-012)."""
    permission_classes = [
        MODULE,
        HasPermission("spacs.application.view_self", "spacs.export.view"),
    ]
    serializer_class = s.ScholarshipApplicationSerializer

    @extend_schema(responses={200: s.ScholarshipApplicationSerializer})
    def get(self, request, pk):
        app = app_selectors.get_application(pk, _actor(request))
        if app is None:
            raise NotFoundError("Application not found.")
        data = s.ScholarshipApplicationSerializer(app).data
        return Response({"export_type": "application_summary", "record": data})


class DocumentUploadView(generics.GenericAPIView):
    """Attach or upload document to application."""
    permission_classes = [MODULE, HasPermission("spacs.application.create", "spacs.application.update")]
    serializer_class = s.DocumentUploadSerializer

    @extend_schema(request=s.DocumentUploadSerializer, responses={201: s.ApplicationDocumentSerializer})
    def post(self, request, pk):
        ser = s.DocumentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        doc = doc_service.attach_document(
            application_id=pk,
            student_user_id=_actor(request).user_id,
            doc_type=vd["doc_type"],
            title=vd.get("title") or vd["doc_type"],
            file_url=vd["file_url"],
            valid_until=vd.get("valid_until"),
            actor=_actor(request),
        )
        return Response(s.ApplicationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentReuseView(generics.GenericAPIView):
    """Student reuses valid previously uploaded document (BR-SPACS-003)."""
    permission_classes = [MODULE, HasPermission("spacs.application.create", "spacs.application.update")]
    serializer_class = s.DocumentReuseSerializer

    @extend_schema(request=s.DocumentReuseSerializer, responses={201: s.ApplicationDocumentSerializer})
    def post(self, request, pk):
        ser = s.DocumentReuseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        source_doc_id = ser.validated_data["source_doc_id"]

        doc = doc_service.reuse_document(
            application_id=pk,
            student_user_id=_actor(request).user_id,
            source_doc_id=source_doc_id,
            actor=_actor(request),
        )
        return Response(s.ApplicationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


# --- Award Cycles Endpoints (CFR-SPACS-013, 014) ---

class AwardCycleListView(generics.ListAPIView):
    """List convocation award cycles visible to caller."""
    permission_classes = [
        MODULE,
        HasPermission("spacs.award.view", "spacs.award.manage"),
    ]
    serializer_class = s.AwardCycleSerializer

    def get_queryset(self):
        return award_selectors.visible_award_cycles(_actor(self.request))


class AwardCycleDetailView(generics.RetrieveAPIView):
    """Retrieve award cycle and candidate evaluations."""
    permission_classes = [
        MODULE,
        HasPermission("spacs.award.view", "spacs.award.manage"),
    ]
    serializer_class = s.AwardCycleSerializer

    def get_object(self):
        obj = award_selectors.get_award_cycle(self.kwargs["pk"], _actor(self.request))
        if obj is None:
            raise NotFoundError("Award cycle not found.")
        return obj


class AwardCycleCreateView(generics.GenericAPIView):
    """SPACS Convener opens an award cycle (UC-SPACS-017)."""
    permission_classes = [MODULE, HasPermission("spacs.award.manage")]
    serializer_class = s.AwardCycleCreateSerializer

    @extend_schema(request=s.AwardCycleCreateSerializer, responses={201: s.AwardCycleSerializer})
    def post(self, request):
        ser = s.AwardCycleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        cycle = award_service.create_award_cycle(
            scheme_id=vd["scheme_id"],
            academic_cycle=vd["academic_cycle"],
            convocation_year=vd["convocation_year"],
            evaluating_body=vd["evaluating_body"],
            committee_members=vd.get("committee_members"),
            actor=_actor(request),
        )
        return Response(s.AwardCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class AwardCandidatePoolView(generics.GenericAPIView):
    """SPACS Convener prepares/finalizes candidate pool (UC-SPACS-017, BW-SPACS-08)."""
    permission_classes = [MODULE, HasPermission("spacs.award.manage")]
    serializer_class = s.AwardCandidatePoolSerializer

    @extend_schema(request=s.AwardCandidatePoolSerializer, responses={200: s.AwardCycleSerializer})
    def post(self, request, pk):
        ser = s.AwardCandidatePoolSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cycle = award_service.prepare_candidate_pool(
            award_cycle_id=pk,
            candidates=ser.validated_data.get("candidates", []),
            actor=_actor(request),
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class AwardEvaluationView(generics.GenericAPIView):
    """Award Committee evaluates candidates and records shortlists/recommendations (UC-SPACS-018)."""
    permission_classes = [MODULE, HasPermission("spacs.award.review")]
    serializer_class = s.AwardEvaluationSerializer

    @extend_schema(request=s.AwardEvaluationSerializer, responses={200: s.AwardCycleSerializer})
    def post(self, request, pk):
        ser = s.AwardEvaluationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cycle = award_service.record_committee_evaluations(
            award_cycle_id=pk,
            evaluations=ser.validated_data.get("evaluations", []),
            actor=_actor(request),
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class AwardApprovalView(generics.GenericAPIView):
    """SPACS Convener records final institutional approval (UC-SPACS-019, BW-SPACS-09, BW-SPACS-11)."""
    permission_classes = [MODULE, HasPermission("spacs.award.approve")]
    serializer_class = s.AwardApprovalSerializer

    @extend_schema(request=s.AwardApprovalSerializer, responses={200: s.AwardCycleSerializer})
    def post(self, request, pk):
        ser = s.AwardApprovalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        cycle = award_service.record_final_approval(
            award_cycle_id=pk,
            approval_reference=vd.get("approval_reference", ""),
            approving_authority=vd.get("approving_authority", ""),
            approved_candidate_ids=vd.get("approved_candidate_ids"),
            actor=_actor(request),
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class AwardPublishView(generics.GenericAPIView):
    """SPACS Convener publishes approved award results (UC-SPACS-020, AFR-SPACS-046)."""
    permission_classes = [MODULE, HasPermission("spacs.award.publish")]
    serializer_class = s.AwardCycleSerializer

    @extend_schema(responses={200: s.AwardCycleSerializer})
    def post(self, request, pk):
        cycle = award_service.publish_award_results(
            award_cycle_id=pk,
            actor=_actor(request),
        )
        return Response(s.AwardCycleSerializer(cycle).data)


# --- Audit & Notifications Endpoints ---

class AuditLogListView(generics.ListAPIView):
    """Authorized viewer reviews SPACS audit trail (UC-SPACS-021, CFR-SPACS-016)."""
    permission_classes = [MODULE, HasPermission("spacs.audit.view")]
    serializer_class = s.SpacsAuditLogSerializer

    def get_queryset(self):
        return audit_selectors.visible_audit_logs(_actor(self.request))


class NotificationListView(generics.ListAPIView):
    """User views notifications (BR-SPACS-008)."""
    permission_classes = [MODULE]
    serializer_class = s.SpacsNotificationSerializer

    def get_queryset(self):
        return audit_selectors.visible_notifications(_actor(self.request))
