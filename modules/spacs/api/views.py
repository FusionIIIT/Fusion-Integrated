"""API views for SPACS.

Enforces:
- HasModuleGrant("spacs")
- Fine-grained permission checks matching registry.py
- Scoped querysets (unowned records return 404 Not Found)
"""
from __future__ import annotations

from datetime import date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.api.permissions import require_spacs_permission, MODULE_GRANT
from modules.spacs.api import serializers as s
from modules.spacs.selectors import (
    scoping,
    catalogue as catalogue_selectors,
    applications as app_selectors,
    awards as award_selectors,
    audit as audit_selectors,
)
from modules.spacs.services import (
    catalogue as catalogue_services,
    applications as app_services,
    verification as verif_services,
    decisions as decision_services,
    renewals as renewal_services,
    awards as award_services,
)


def _principal(request):
    return getattr(request, "principal", None)


# --- Catalogue Endpoints ---
class CatalogueListView(APIView):
    """GET: Browse active catalogue.
       POST: Create draft catalogue entry.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            classes = require_spacs_permission("spacs.catalogue.view")
        elif self.request.method == "POST":
            classes = require_spacs_permission("spacs.catalogue.manage")
        else:
            classes = []

        return [permission() for permission in classes]

    def get(self, request):
        p = _principal(request)

        if scoping.is_convener(p):
            entries = catalogue_selectors.get_all_catalogue_entries()
        else:
            entries = catalogue_selectors.get_published_catalogue()

        return Response(
            s.CatalogueEntrySerializer(entries, many=True).data
        )

    def post(self, request):
        p = _principal(request)

        code = request.data.get("code")
        title = request.data.get("title")
        kind = request.data.get("kind")
        desc = request.data.get("description", "")

        if not code or not title or not kind:
            raise BadRequestError("code, title, and kind are required.")

        entry = catalogue_services.create_catalogue_entry(
            code=code,
            title=title,
            kind=kind,
            description=desc,
            actor_user_id=p.user_id,
        )

        return Response(
            s.CatalogueEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )


class CatalogueDetailView(APIView):
    """GET: Detail of a catalogue entry."""

    permission_classes = require_spacs_permission(
        "spacs.catalogue.view"
    )

    def get(self, request, pk):
        entry = catalogue_selectors.get_catalogue_entry_by_pk(pk)

        if not entry:
            raise NotFoundError("Catalogue entry not found.")

        return Response(
            s.CatalogueEntrySerializer(entry).data
        )


class CatalogueVersionCreateView(APIView):
    """POST /api/v1/spacs/catalogue/<int:pk>/versions/ - Create draft version (UC-SPACS-011)"""
    permission_classes = require_spacs_permission("spacs.catalogue.manage")

    def post(self, request, pk):
        p = _principal(request)
        entry = catalogue_selectors.get_catalogue_entry_by_pk(pk)
        if not entry:
            raise NotFoundError("Catalogue entry not found.")

        data = request.data
        version = catalogue_services.create_policy_version(
            catalogue_entry=entry,
            version_label=data.get("version_label", "v1.0"),
            effective_from=data.get("effective_from", date.today()),
            effective_to=data.get("effective_to"),
            eligibility_schema=data.get("eligibility_schema", {}),
            required_evidence_schema=data.get("required_evidence_schema", []),
            sla_config=data.get("sla_config", {}),
            is_renewable=data.get("is_renewable", False),
            renewal_window_start=data.get("renewal_window_start"),
            renewal_window_end=data.get("renewal_window_end"),
            max_renewal_cycles=data.get("max_renewal_cycles", 0),
            candidate_source_method=data.get("candidate_source_method", "application"),
            eval_committee_role=data.get("eval_committee_role", ""),
            approving_authority_title=data.get("approving_authority_title", ""),
            actor_user_id=p.user_id,
        )
        return Response(s.CataloguePolicyVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class CataloguePublishView(APIView):
    """POST /api/v1/spacs/catalogue/versions/<int:version_id>/publish/ - Publish version (UC-SPACS-023)"""
    permission_classes = require_spacs_permission("spacs.catalogue.manage")

    def post(self, request, version_id):
        p = _principal(request)
        version = catalogue_selectors.get_policy_version_by_pk(version_id)
        if not version:
            raise NotFoundError("Policy version not found.")

        ref = request.data.get("policy_approval_ref")
        approval_date = request.data.get("policy_approval_date")
        if not ref or not approval_date:
            raise BadRequestError("policy_approval_ref and policy_approval_date are required to publish.")

        pub_version = catalogue_services.publish_policy_version(
            version=version,
            policy_approval_ref=ref,
            policy_approval_date=approval_date,
            actor_user_id=p.user_id,
        )
        return Response(s.CataloguePolicyVersionSerializer(pub_version).data)


class CatalogueRetireView(APIView):
    """POST /api/v1/spacs/catalogue/<int:pk>/retire/ - Retire entry prospectively (UC-SPACS-012)"""
    permission_classes = require_spacs_permission("spacs.catalogue.manage")

    def post(self, request, pk):
        p = _principal(request)
        entry = catalogue_selectors.get_catalogue_entry_by_pk(pk)
        if not entry:
            raise NotFoundError("Catalogue entry not found.")

        entry = catalogue_services.retire_catalogue_entry(entry, actor_user_id=p.user_id)
        return Response(s.CatalogueEntrySerializer(entry).data)


# --- Scholarship Applications Endpoints ---

class MyApplicationsView(APIView):
    """GET /api/v1/spacs/applications/mine/ - List student's own applications (UC-SPACS-008)"""
    permission_classes = require_spacs_permission("spacs.application.view_self")

    def get(self, request):
        p = _principal(request)
        apps = app_selectors.get_student_applications(p.user_id)
        return Response(s.ScholarshipApplicationListSerializer(apps, many=True).data)


class ApplicationDraftSaveView(APIView):
    """POST /api/v1/spacs/applications/ - Create/update server-side draft (BR-SPACS-007)"""
    permission_classes = require_spacs_permission("spacs.application.create")

    def post(self, request):
        p = _principal(request)
        ser = s.DraftSaveInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        policy = catalogue_selectors.get_policy_version_by_pk(data["policy_version_id"])
        if not policy:
            raise NotFoundError("Policy version not found.")

        app = app_services.save_draft(
            user_id=p.user_id,
            policy_version=policy,
            academic_cycle=data["academic_cycle"],
            submission_data=data["submission_data"],
            documents=data.get("documents", []),
            application_id=request.data.get("application_id"),
            applicant_snapshot=data.get("applicant_snapshot"),
        )
        return Response(s.ScholarshipApplicationDetailSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    """GET: View application details.
       PUT: Modify an editable or returned application.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            classes = require_spacs_permission(
                "spacs.application.view_self",
                "spacs.application.view_all",
                "spacs.application.verify",
            )
        elif self.request.method == "PUT":
            classes = require_spacs_permission(
                "spacs.application.modify_self"
            )
        else:
            classes = []

        return [permission() for permission in classes]

    def get(self, request, pk):
        p = _principal(request)

        app = scoping.applications_for(p).filter(pk=pk).first()

        if not app:
            raise NotFoundError("Application not found.")

        return Response(
            s.ScholarshipApplicationDetailSerializer(app).data
        )

    def put(self, request, pk):
        p = _principal(request)

        app = scoping.applications_for(p).filter(
            pk=pk,
            user_id=p.user_id,
        ).first()

        if not app:
            raise NotFoundError("Application not found.")

        submission_data = request.data.get(
            "submission_data",
            app.submission_data,
        )
        documents = request.data.get("documents")

        if app.status == "draft":
            updated = app_services.save_draft(
                user_id=p.user_id,
                policy_version=app.policy_version,
                academic_cycle=app.academic_cycle,
                submission_data=submission_data,
                documents=documents,
                application_id=app.id,
            )

        elif app.status == "correction_required":
            updated = verif_services.resubmit_corrected_application(
                application_id=app.id,
                user_id=p.user_id,
                updated_submission_data=submission_data,
            )

        else:
            raise ConflictError(
                f"Cannot edit application in status '{app.status}'."
            )

        return Response(
            s.ScholarshipApplicationDetailSerializer(updated).data
        )


class ApplicationSubmitView(APIView):
    """POST /api/v1/spacs/applications/<int:pk>/submit/ - Submit application (UC-SPACS-001)"""
    permission_classes = require_spacs_permission("spacs.application.create")

    def post(self, request, pk):
        p = _principal(request)
        app = scoping.applications_for(p).filter(pk=pk, user_id=p.user_id).first()
        if not app:
            raise NotFoundError("Application not found.")

        snapshot = request.data.get("student_snapshot", {})
        submitted = app_services.submit_application(
            application_id=app.id,
            user_id=p.user_id,
            student_snapshot=snapshot,
        )
        return Response(s.ScholarshipApplicationDetailSerializer(submitted).data)


class ApplicationWithdrawView(APIView):
    """POST /api/v1/spacs/applications/<int:pk>/withdraw/ - Withdraw application (UC-SPACS-004)"""
    permission_classes = require_spacs_permission("spacs.application.withdraw_self")

    def post(self, request, pk):
        p = _principal(request)
        app = scoping.applications_for(p).filter(pk=pk, user_id=p.user_id).first()
        if not app:
            raise NotFoundError("Application not found.")

        reason = request.data.get("reason", "")
        withdrawn = app_services.withdraw_application(
            application_id=app.id,
            user_id=p.user_id,
            reason=reason,
        )
        return Response(s.ScholarshipApplicationDetailSerializer(withdrawn).data)



class ApplicationTimelineView(APIView):
    """GET: Application status history with appropriate redaction."""

    permission_classes = require_spacs_permission(
        "spacs.application.view_self",
        "spacs.application.view_all",
        "spacs.application.verify",
    )

    def get(self, request, pk):
        p = _principal(request)

        app = scoping.applications_for(p).filter(pk=pk).first()

        if not app:
            raise NotFoundError("Application not found.")

        is_staff = (
            scoping.is_assistant(p)
            or scoping.is_convener(p)
            or scoping.is_auditor(p)
        )

        timeline = audit_selectors.get_application_timeline(
            app,
            is_staff=is_staff,
        )

        return Response({
            "application_id": app.pk,
            "timeline": timeline,
        })

class ApplicationExportView(APIView):
    """GET /api/v1/spacs/applications/<int:pk>/export/ - Export application summary (UC-SPACS-007)"""
    permission_classes = require_spacs_permission("spacs.application.export")

    def get(self, request, pk):
        p = _principal(request)
        app = scoping.applications_for(p).filter(pk=pk).first()
        if not app:
            raise NotFoundError("Application not found.")

        rows = [
            ["Application Number", app.application_number],
            ["Scheme", app.policy_version.catalogue_entry.title],
            ["Academic Cycle", app.academic_cycle],
            ["Status", app.status],
            ["Submitted At", str(app.submitted_at or "N/A")],
            ["Applicant User ID", str(app.user_id)],
        ]
        return safe_csv.stream(
            filename=f"spacs-app-{app.application_number}.csv",
            header=["Field", "Value"],
            rows=rows,
        )


# --- Scholarship Renewal Endpoints ---

class RenewalInitiateView(APIView):
    """POST /api/v1/spacs/applications/<int:pk>/renew/ - Initiate renewal draft (UC-SPACS-015)"""
    permission_classes = require_spacs_permission("spacs.application.create")

    def post(self, request, pk):
        p = _principal(request)
        # pk from URL path is the prior application being renewed.
        prior_app_id = pk
        cycle = request.data.get("academic_cycle")
        policy_id = request.data.get("policy_version_id")

        if not cycle or not policy_id:
            raise BadRequestError("academic_cycle and policy_version_id are required.")

        policy = catalogue_selectors.get_policy_version_by_pk(policy_id)
        if not policy:
            raise NotFoundError("Policy version not found.")

        renewal_draft = renewal_services.initiate_renewal(
            prior_application_id=prior_app_id,
            user_id=p.user_id,
            new_academic_cycle=cycle,
            active_policy_version=policy,
        )
        return Response(s.ScholarshipApplicationDetailSerializer(renewal_draft).data, status=status.HTTP_201_CREATED)


# --- Assistant Verification Endpoints ---

class VerificationQueueView(APIView):
    """GET /api/v1/spacs/verification/queue/ - Assistant verification queue (UC-SPACS-002)"""
    permission_classes = require_spacs_permission("spacs.application.verify")

    def get(self, request):
        queue = app_selectors.get_assistant_verification_queue()
        return Response(s.ScholarshipApplicationListSerializer(queue, many=True).data)


class VerificationActionView(APIView):
    """POST /api/v1/spacs/verification/<int:pk>/action/ - Verify, Request Correction, or Flag Concern"""
    permission_classes = require_spacs_permission("spacs.application.verify")

    def post(self, request, pk):
        p = _principal(request)
        ser = s.VerificationActionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        action = data["action"]
        comment = data.get("comment", "")
        findings = data.get("findings", {})

        if action == "verify":
            app = verif_services.mark_verified_and_route(
                application_id=pk,
                assistant_user_id=p.user_id,
                findings=findings,
            )
        elif action == "flag_concern":
            app = verif_services.flag_verification_concern(
                application_id=pk,
                assistant_user_id=p.user_id,
                concern_note=comment,
            )
        elif action == "request_correction":
            app = verif_services.request_correction(
                application_id=pk,
                reviewer_user_id=p.user_id,
                actor_role="spacs_assistant",
                correction_reason=comment,
            )
        else:
            raise BadRequestError(f"Unknown verification action '{action}'.")

        return Response(s.ScholarshipApplicationDetailSerializer(app).data)


class DocumentVerifyView(APIView):
    """POST /api/v1/spacs/verification/documents/<int:pk>/ - Record finding on evidence (BR-SPACS-016)"""
    permission_classes = require_spacs_permission("spacs.application.verify")

    def post(self, request, pk):
        p = _principal(request)
        status_val = request.data.get("status")
        comment = request.data.get("comment", "")
        if not status_val:
            raise BadRequestError("Verification status is required.")

        doc = verif_services.record_document_verification_finding(
            document_id=pk,
            assistant_user_id=p.user_id,
            verification_status=status_val,
            comment=comment,
        )
        return Response(s.ApplicationDocumentSerializer(doc).data)


# --- Convener Decisions Endpoints ---

class DecisionQueueView(APIView):
    """GET /api/v1/spacs/decisions/queue/ - Convener decision queue (UC-SPACS-006)"""
    permission_classes = require_spacs_permission("spacs.application.decide")

    def get(self, request):
        queue = app_selectors.get_convener_decision_queue()
        return Response(s.ScholarshipApplicationListSerializer(queue, many=True).data)


class DecisionActionView(APIView):
    """POST /api/v1/spacs/decisions/<int:pk>/action/ - Convener Approve, Reject, Return (UC-SPACS-006)"""
    permission_classes = require_spacs_permission("spacs.application.decide")

    def post(self, request, pk):
        p = _principal(request)
        ser = s.DecisionActionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        app = decision_services.record_scholarship_decision(
            application_id=pk,
            convener_user_id=p.user_id,
            outcome=data["outcome"],
            reason=data.get("reason", ""),
            policy_reference=data.get("policy_reference", ""),
        )
        return Response(s.ScholarshipApplicationDetailSerializer(app).data)


# --- Convocation Awards Endpoints ---

class AwardCycleListView(APIView):
    """GET: List award cycles.
       POST: Create a new award cycle.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            classes = require_spacs_permission(
                "spacs.award.view"
            )
        elif self.request.method == "POST":
            classes = require_spacs_permission(
                "spacs.award.manage"
            )
        else:
            classes = []

        return [permission() for permission in classes]

    def get(self, request):
        p = _principal(request)

        cycles = scoping.award_cycles_for(p)

        return Response(
            s.AwardCycleSerializer(cycles, many=True).data
        )

    def post(self, request):
        p = _principal(request)

        policy_id = request.data.get("policy_version_id")
        year = request.data.get("convocation_year")

        if not policy_id or not year:
            raise BadRequestError(
                "policy_version_id and convocation_year are required."
            )

        policy = catalogue_selectors.get_policy_version_by_pk(policy_id)

        if not policy:
            raise NotFoundError("Policy version not found.")

        cycle = award_services.open_award_cycle(
            policy_version=policy,
            convocation_year=int(year),
            actor_user_id=p.user_id,
        )

        return Response(
            s.AwardCycleSerializer(cycle).data,
            status=status.HTTP_201_CREATED,
        )


class AwardCyclePoolView(APIView):
    """POST /api/v1/spacs/awards/cycles/<int:pk>/pool/ - Finalize candidate pool (UC-SPACS-017)"""
    permission_classes = require_spacs_permission("spacs.award.manage")

    def post(self, request, pk):
        p = _principal(request)
        candidate_ids = request.data.get("candidate_user_ids", [])
        snapshots = request.data.get("snapshots", {})

        cycle = award_services.prepare_candidate_pool(
            cycle_id=pk,
            convener_user_id=p.user_id,
            candidate_user_ids=candidate_ids,
            snapshots_by_user={int(k): v for k, v in snapshots.items()},
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class AwardEvaluationView(APIView):
    """GET /api/v1/spacs/awards/cycles/<int:pk>/evaluation/ - Candidates sheet
       POST /api/v1/spacs/awards/cycles/<int:pk>/evaluation/ - Record committee evaluation (UC-SPACS-018)
    """
    permission_classes = require_spacs_permission("spacs.award.evaluate")

    def get(self, request, pk):
        candidates = award_selectors.get_candidate_evaluation_sheet(pk)
        return Response(s.AwardCandidateSerializer(candidates, many=True).data)

    def post(self, request, pk):
        p = _principal(request)
        evaluations = request.data.get("evaluations", [])
        actor_role = getattr(p, "active_role", None) or "award_eval_committee"

        cycle = award_services.record_committee_evaluations(
            cycle_id=pk,
            evaluator_user_id=p.user_id,
            actor_role=actor_role,
            evaluations=evaluations,
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class AwardApprovalView(APIView):
    """POST /api/v1/spacs/awards/cycles/<int:pk>/approval/ - Record institutional approval (UC-SPACS-019)"""
    permission_classes = require_spacs_permission("spacs.award.manage")

    def post(self, request, pk):
        p = _principal(request)
        authority = request.data.get("approval_authority", "")
        reference = request.data.get("approval_reference", "")
        winners = request.data.get("winning_candidate_ids", [])

        cycle = award_services.record_institutional_approval(
            cycle_id=pk,
            convener_user_id=p.user_id,
            approval_authority=authority,
            approval_reference=reference,
            winning_candidate_ids=winners,
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class AwardPublishView(APIView):
    """POST /api/v1/spacs/awards/cycles/<int:pk>/publish/ - Publish award results (UC-SPACS-020)"""
    permission_classes = require_spacs_permission("spacs.award.publish")

    def post(self, request, pk):
        p = _principal(request)
        cycle = award_services.publish_award_results(
            cycle_id=pk,
            convener_user_id=p.user_id,
        )
        return Response(s.AwardCycleSerializer(cycle).data)


class PublishedAwardsPublicView(APIView):
    """GET /api/v1/spacs/awards/published/ - Public published awardees"""
    permission_classes = [MODULE_GRANT]

    def get(self, request):
        year = request.query_params.get("year")
        conv_year = int(year) if year and year.isdigit() else None
        winners = award_selectors.get_published_award_winners(convocation_year=conv_year)
        return Response(s.AwardCandidateSerializer(winners, many=True).data)


# --- Audit Trail Endpoint ---

class AuditTrailView(APIView):
    """GET /api/v1/spacs/audit/ - Read-only audit log inspection (UC-SPACS-021, BR-SPACS-021)"""
    permission_classes = require_spacs_permission("spacs.audit.view")

    def get(self, request):
        params = request.query_params
        logs = audit_selectors.get_audit_trail(
            entity_type=params.get("entity_type"),
            entity_id=params.get("entity_id"),
            actor_user_id=int(params["actor_user_id"]) if params.get("actor_user_id") else None,
            action=params.get("action"),
            limit=int(params.get("limit", 100)),
        )
        return Response(s.AuditLogSerializer(logs, many=True).data)
