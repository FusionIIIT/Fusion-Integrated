"""HTTP views for SPACS module."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.api import serializers as s
from modules.spacs.api.permissions import RequirePermission
from modules.spacs.domain.errors import (
    CompletenessError,
    DocumentReuseError,
    DuplicateApplicationError,
    EligibilityError,
    InvalidTransitionError,
    RenewalEligibilityError,
    SpacsDomainError,
    UnauthorizedActionError,
)
from modules.spacs.models import (
    SpacsApplication,
    SpacsAwardCandidate,
    SpacsAwardCycle,
    SpacsCatalogueEntry,
    SpacsTask,
)
from modules.spacs.selectors import (
    get_audit_trail_for_auditor,
    get_verification_queue,
    visible_applications_for_student,
    visible_catalogue,
)
from modules.spacs.services import applications as app_svc
from modules.spacs.services import awards as award_svc
from modules.spacs.services import catalogue as cat_svc
from modules.spacs.services import decisions as dec_svc
from modules.spacs.services import renewals as ren_svc
from modules.spacs.services import verification as ver_svc


def _map_domain_error(e: Exception):
    """Map domain exceptions to corresponding DRF HTTP errors."""
    if isinstance(e, InvalidTransitionError):
        raise ConflictError(str(e)) from e
    if isinstance(
        e,
        (
            EligibilityError,
            DuplicateApplicationError,
            DocumentReuseError,
            CompletenessError,
            UnauthorizedActionError,
            RenewalEligibilityError,
            SpacsDomainError,
        ),
    ):
        raise BadRequestError(str(e)) from e
    raise BadRequestError(str(e)) from e


class SchemeListView(APIView):
    """List or create schemes."""

    permission_classes = [RequirePermission("spacs.scheme.view", "spacs.scheme.create")]

    @extend_schema(responses={200: s.SchemeSerializer(many=True)})
    def get(self, request):
        schemes = visible_catalogue()
        return Response(s.SchemeSerializer(schemes, many=True).data)

    @extend_schema(request=s.SchemeCreateSerializer, responses={201: s.SchemeSerializer})
    def post(self, request):
        if not getattr(request.principal, "has_permission", lambda p: False)("spacs.scheme.create"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.SchemeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            scheme = cat_svc.create_catalogue_entry(
                created_by_user_id=request.principal.user_id,
                **ser.validated_data,
            )
            return Response(s.SchemeSerializer(scheme).data, status=status.HTTP_201_CREATED)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class SchemeDetailView(APIView):
    """Retrieve or update scheme details."""

    permission_classes = [RequirePermission("spacs.scheme.view", "spacs.scheme.update")]

    @extend_schema(responses={200: s.SchemeSerializer})
    def get(self, request, pk: int):
        try:
            scheme = SpacsCatalogueEntry.objects.get(pk=pk)
            return Response(s.SchemeSerializer(scheme).data)
        except SpacsCatalogueEntry.DoesNotExist as e:
            raise NotFoundError("Scheme not found.") from e

    @extend_schema(request=s.SchemeSerializer, responses={200: s.SchemeSerializer})
    def patch(self, request, pk: int):
        try:
            scheme = SpacsCatalogueEntry.objects.get(pk=pk)
        except SpacsCatalogueEntry.DoesNotExist as e:
            raise NotFoundError("Scheme not found.") from e
        ser = s.SchemeSerializer(scheme, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class CycleListView(APIView):
    """List or announce award cycles."""

    permission_classes = [RequirePermission("spacs.cycle.view", "spacs.cycle.create")]

    @extend_schema(responses={200: s.CycleSerializer(many=True)})
    def get(self, request):
        cycles = SpacsAwardCycle.objects.all().order_by("-id")
        return Response(s.CycleSerializer(cycles, many=True).data)

    @extend_schema(request=s.CycleCreateSerializer, responses={201: s.CycleSerializer})
    def post(self, request):
        if not getattr(request.principal, "has_permission", lambda p: False)("spacs.cycle.create"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.CycleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            cycle = award_svc.open_award_cycle(
                convener_user_id=request.principal.user_id,
                **ser.validated_data,
            )
            return Response(s.CycleSerializer(cycle).data, status=status.HTTP_201_CREATED)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class ApplicationListView(APIView):
    """List applications or submit a new application."""

    permission_classes = [RequirePermission("spacs.application.view", "spacs.application.create")]

    @extend_schema(responses={200: s.ApplicationSerializer(many=True)})
    def get(self, request):
        user_id = request.principal.user_id
        is_student = (
            getattr(request.principal, "kind", "") == "student"
            or getattr(request.principal, "active_role", "") == "student"
        )
        if is_student:
            apps = visible_applications_for_student(user_id)
        else:
            apps = SpacsApplication.objects.all().order_by("-id")
        return Response(s.ApplicationSerializer(apps, many=True).data)

    @extend_schema(request=s.ApplicationCreateSerializer, responses={201: s.ApplicationSerializer})
    def post(self, request):
        if not getattr(request.principal, "has_permission", lambda p: False)(
            "spacs.application.create"
        ):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.ApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            draft = app_svc.create_draft_application(
                scheme_code=ser.validated_data["scheme_code"],
                applicant_user_id=request.principal.user_id,
                academic_cycle=ser.validated_data["academic_cycle"],
            )
            income = ser.validated_data.get("family_income")
            app = app_svc.submit_application(
                application_id=draft.application_id,
                acting_user_id=request.principal.user_id,
                student_cpi=float(ser.validated_data["cpi"]),
                student_family_income=float(income) if income is not None else None,
            )
            return Response(s.ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class ApplicationDetailView(APIView):
    """View application details with scoping."""

    permission_classes = [RequirePermission("spacs.application.view")]

    @extend_schema(request=None, responses={200: s.ApplicationSerializer})
    def get(self, request, pk: int):
        try:
            app = SpacsApplication.objects.get(pk=pk)
        except SpacsApplication.DoesNotExist as e:
            raise NotFoundError("Application not found.") from e
        is_student = (
            getattr(request.principal, "kind", "") == "student"
            or getattr(request.principal, "active_role", "") == "student"
        )
        if is_student and app.applicant_user_id != request.principal.user_id:
            raise NotFoundError("Application not found.")
        return Response(s.ApplicationSerializer(app).data)

    @extend_schema(request=s.ApplicationAmendSerializer, responses={200: s.ApplicationSerializer})
    def patch(self, request, pk: int):
        try:
            app = SpacsApplication.objects.get(pk=pk)
        except SpacsApplication.DoesNotExist as e:
            raise NotFoundError("Application not found.") from e
        if app.applicant_user_id != request.principal.user_id:
            raise NotFoundError("Application not found.")
        ser = s.ApplicationAmendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            updated = app_svc.amend_application(
                application_id=app.application_id,
                student_user_id=request.principal.user_id,
                **ser.validated_data,
            )
            return Response(s.ApplicationSerializer(updated).data)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class ApplicationWithdrawView(APIView):
    """Withdraw a pending application."""

    permission_classes = [RequirePermission("spacs.application.update")]

    @extend_schema(request=None, responses={200: s.ApplicationSerializer})
    def post(self, request, pk: int):
        try:
            app = SpacsApplication.objects.get(pk=pk)
        except SpacsApplication.DoesNotExist as e:
            raise NotFoundError("Application not found.") from e
        if app.applicant_user_id != request.principal.user_id:
            raise NotFoundError("Application not found.")
        try:
            withdrawn = app_svc.withdraw_application(
                application_id=app.application_id,
                acting_user_id=request.principal.user_id,
            )
            return Response(s.ApplicationSerializer(withdrawn).data)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class VerificationQueueView(APIView):
    """List pending verification items for staff."""

    permission_classes = [RequirePermission("spacs.application.review")]

    @extend_schema(responses={200: s.ApplicationSerializer(many=True)})
    def get(self, request):
        records = get_verification_queue()
        return Response(s.ApplicationSerializer(records, many=True).data)


class VerificationActionView(APIView):
    """Perform verification check: verify or mark defect."""

    permission_classes = [RequirePermission("spacs.application.review")]

    @extend_schema(request=s.VerificationActionSerializer, responses={200: s.ApplicationSerializer})
    def post(self, request, pk: int):
        try:
            app = SpacsApplication.objects.get(pk=pk)
        except SpacsApplication.DoesNotExist as e:
            raise NotFoundError("Application not found.") from e
        ser = s.VerificationActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]
        roles = list(getattr(request.principal, "roles", []))
        try:
            if app.state in ["submitted", "resubmitted", "renewal_submitted"]:
                ver_svc.open_verification_task(
                    application_id=app.application_id,
                    assistant_user_id=request.principal.user_id,
                    user_roles=roles,
                )
            if action == "verify":
                updated = ver_svc.mark_verified(
                    application_id=app.application_id,
                    assistant_user_id=request.principal.user_id,
                    user_roles=roles,
                )
            else:
                updated = ver_svc.request_correction(
                    application_id=app.application_id,
                    assistant_user_id=request.principal.user_id,
                    user_roles=roles,
                    reason=ser.validated_data.get("notes", "Defective submission"),
                )
            return Response(s.ApplicationSerializer(updated).data)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class DecisionActionView(APIView):
    """Convener approval or rejection decision."""

    permission_classes = [RequirePermission("spacs.application.approve")]

    @extend_schema(request=s.DecisionActionSerializer, responses={200: s.ApplicationSerializer})
    def post(self, request):
        ser = s.DecisionActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        outcome = ser.validated_data["outcome"]
        app_id = ser.validated_data["application_id"]
        roles = list(getattr(request.principal, "roles", []))
        try:
            app = SpacsApplication.objects.get(application_id=app_id)
            if app.state in ["verified", "renewal_verified", "verification_concern"]:
                dec_svc.open_convener_decision(
                    application_id=app_id,
                    convener_user_id=request.principal.user_id,
                    user_roles=roles,
                )
            if outcome == "approved":
                dec = dec_svc.approve_application(
                    application_id=app_id,
                    convener_user_id=request.principal.user_id,
                    user_roles=roles,
                    reason=ser.validated_data.get("reason", "Approved by Convener"),
                )
            else:
                dec = dec_svc.reject_application(
                    application_id=app_id,
                    convener_user_id=request.principal.user_id,
                    user_roles=roles,
                    reason=ser.validated_data.get("reason", "Rejected by Convener"),
                )
            return Response(s.ApplicationSerializer(dec).data)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class RenewalListView(APIView):
    """List or submit renewal applications."""

    permission_classes = [RequirePermission("spacs.application.create", "spacs.application.view")]

    @extend_schema(responses={200: s.ApplicationSerializer(many=True)})
    def get(self, request):
        if getattr(request.principal, "role", "") == "student":
            renewals = SpacsApplication.objects.filter(
                applicant_user_id=request.principal.user_id, is_renewal=True
            )
        else:
            renewals = SpacsApplication.objects.filter(is_renewal=True).order_by("-id")
        return Response(s.ApplicationSerializer(renewals, many=True).data)

    @extend_schema(request=s.RenewalCreateSerializer, responses={201: s.ApplicationSerializer})
    def post(self, request):
        if not getattr(request.principal, "has_permission", lambda p: False)(
            "spacs.application.create"
        ):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = s.RenewalCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ren = ren_svc.submit_renewal_application(
                student_user_id=request.principal.user_id,
                **ser.validated_data,
            )
            return Response(s.ApplicationSerializer(ren).data, status=status.HTTP_201_CREATED)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class AwardCyclePublishView(APIView):
    """Publish award cycle outcomes."""

    permission_classes = [RequirePermission("spacs.cycle.publish")]

    @extend_schema(request=None, responses={200: s.CycleSerializer})
    def post(self, request, pk: int):
        try:
            cycle = award_svc.publish_award_results(
                award_cycle_id=pk,
                convener_user_id=request.principal.user_id,
            )
            return Response(s.CycleSerializer(cycle).data)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class AwardListView(APIView):
    """List awards and create award candidates."""

    permission_classes = [RequirePermission("spacs.award.view", "spacs.award.create")]

    @extend_schema(responses={200: s.AwardCandidateSerializer(many=True)})
    def get(self, request):
        if getattr(request.principal, "role", "") == "student":
            awards = SpacsAwardCandidate.objects.filter(student_user_id=request.principal.user_id)
        else:
            awards = SpacsAwardCandidate.objects.all().order_by("-id")
        return Response(s.AwardCandidateSerializer(awards, many=True).data)

    @extend_schema(request=s.AwardCandidateSerializer, responses={201: s.AwardCandidateSerializer})
    def post(self, request):
        ser = s.AwardCandidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cand = ser.save()
        return Response(s.AwardCandidateSerializer(cand).data, status=status.HTTP_201_CREATED)


class AwardPublishView(APIView):
    """Publish convocation award lists."""

    permission_classes = [RequirePermission("spacs.award.publish")]

    @extend_schema(request=None, responses={200: s.AwardCandidateSerializer(many=True)})
    def post(self, request):
        cycle_id = request.data.get("cycle_id", 1)
        try:
            cycle = award_svc.publish_award_results(
                award_cycle_id=cycle_id,
                convener_user_id=request.principal.user_id,
            )
            winners = cycle.candidates.filter(shortlisted=True)
            return Response(s.AwardCandidateSerializer(winners, many=True).data)
        except (SpacsDomainError, ValueError) as e:
            _map_domain_error(e)


class AwardExportView(APIView):
    """Export awards and financial disbursement data."""

    permission_classes = [RequirePermission("spacs.award.export")]

    @extend_schema(responses={200: s.AwardCandidateSerializer(many=True)})
    def get(self, request):
        awards = SpacsAwardCandidate.objects.all().order_by("-id")
        return Response(s.AwardCandidateSerializer(awards, many=True).data)


class TaskListView(APIView):
    """List pending tasks for assistants."""

    permission_classes = [RequirePermission("spacs.application.review")]

    @extend_schema(responses={200: s.TaskSerializer(many=True)})
    def get(self, request):
        tasks = SpacsTask.objects.filter(status="pending").order_by("created_at")
        return Response(s.TaskSerializer(tasks, many=True).data)


class AuditListView(APIView):
    """List audit logs for authorized auditor."""

    permission_classes = [RequirePermission("spacs.audit.view")]

    @extend_schema(responses={200: s.AuditLogSerializer(many=True)})
    def get(self, request):
        roles = list(getattr(request.principal, "roles", []))
        try:
            logs = get_audit_trail_for_auditor(roles)
            return Response(s.AuditLogSerializer(logs, many=True).data)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
