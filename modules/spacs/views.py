"""SPACS scholarship application and supporting-document API endpoints."""
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from modules.spacs.models import ScholarshipApplication, SupportingDocument
from modules.spacs.permissions import (
    ASSISTANT_ROLE,
    CONVENER_ROLE,
    STUDENT_ROLE,
    IsSpacsAssistant,
    IsSpacsConvener,
    IsStudentApplicant,
    IsStudentSupportingDocument,
)
from modules.spacs.serializers import (
    ScholarshipApplicationSerializer,
    SupportingDocumentSerializer,
)


class ScholarshipApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ScholarshipApplicationSerializer
    lookup_field = "application_id"

    def get_permissions(self):
        action_permissions = {
            "submit": IsStudentApplicant,
            "verify": IsSpacsAssistant,
            "approve": IsSpacsConvener,
            "reject": IsSpacsConvener,
            "return_for_correction": IsSpacsConvener,
        }
        permission_class = action_permissions.get(self.action)
        if permission_class is None:
            principal = getattr(self.request, "principal", None)
            role_permissions = {
                STUDENT_ROLE: IsStudentApplicant,
                ASSISTANT_ROLE: IsSpacsAssistant,
                CONVENER_ROLE: IsSpacsConvener,
            }
            permission_class = role_permissions.get(
                getattr(principal, "active_role", None),
                IsStudentApplicant,
            )
        return [permission_class()]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        queryset = ScholarshipApplication.objects.all()
        if principal is None:
            return queryset.none()

        role = getattr(principal, "active_role", None)
        if role == STUDENT_ROLE:
            return queryset.filter(student_id=principal.user_id)
        if role == ASSISTANT_ROLE:
            return queryset.filter(assigned_assistant_user_id=principal.user_id)
        if role == CONVENER_ROLE:
            return queryset
        return queryset.none()

    def get_serializer(self, *args, **kwargs):
        # The authenticated principal, not the request body, is the source of ownership.
        data = kwargs.get("data")
        principal = getattr(self.request, "principal", None)
        if (
            self.action == "create"
            and data is not None
            and "student_id" not in data
            and principal is not None
        ):
            kwargs["data"] = {**data, "student_id": principal.user_id}
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(student_id=self.request.principal.user_id)

    def _locked_application(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        application = (
            self.filter_queryset(self.get_queryset())
            .select_for_update()
            .filter(**lookup)
            .first()
        )
        if application is None:
            raise NotFound("Scholarship application not found.")
        self.check_object_permissions(self.request, application)
        return application

    @action(detail=True, methods=["post"])
    def submit(self, request, application_id=None):
        with transaction.atomic():
            application = self._locked_application()
            if application.status != ScholarshipApplication.STATUS_DRAFT:
                raise ValidationError(
                    {"status": "Only draft applications can be submitted."}
                )
            application.status = ScholarshipApplication.STATUS_SUBMITTED
            application.submission_date = timezone.now()
            application.save(update_fields=["status", "submission_date", "updated_at"])
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    def verify(self, request, application_id=None):
        allowed_fields = {"verification_status", "verification_findings"}
        if set(request.data) - allowed_fields:
            raise ValidationError(
                {"detail": "Only verification status and findings may be recorded."}
            )
        if "verification_findings" not in request.data:
            raise ValidationError(
                {"verification_findings": "This field is required."}
            )
        findings = request.data["verification_findings"]
        if not isinstance(findings, dict):
            raise ValidationError(
                {"verification_findings": "Expected an object of verification findings."}
            )
        verification_status = request.data.get(
            "verification_status",
            ScholarshipApplication.VERIFICATION_VERIFIED,
        )
        allowed_statuses = {
            ScholarshipApplication.VERIFICATION_VERIFIED,
            ScholarshipApplication.VERIFICATION_ISSUES_FOUND,
        }
        if verification_status not in allowed_statuses:
            raise ValidationError(
                {"verification_status": "Choose a final verification outcome."}
            )

        with transaction.atomic():
            application = self._locked_application()
            if application.status not in {
                ScholarshipApplication.STATUS_SUBMITTED,
                ScholarshipApplication.STATUS_UNDER_VERIFICATION,
            }:
                raise ValidationError(
                    {"status": "Only submitted applications can be verified."}
                )
            application.status = ScholarshipApplication.STATUS_UNDER_VERIFICATION
            application.verification_status = verification_status
            application.verification_findings = findings
            application.verified_by_user_id = request.principal.user_id
            application.verified_at = timezone.now()
            application.save(update_fields=[
                "status",
                "verification_status",
                "verification_findings",
                "verified_by_user_id",
                "verified_at",
                "updated_at",
            ])
        return Response(self.get_serializer(application).data)

    def _decide(self, request, *, target_status):
        extra_fields = set(request.data) - {"decision_note"}
        if extra_fields:
            raise ValidationError(
                {"detail": "Only a decision note may accompany the decision."}
            )
        decision_note = request.data.get("decision_note", "")
        if not isinstance(decision_note, str):
            raise ValidationError({"decision_note": "Expected a string."})

        with transaction.atomic():
            application = self._locked_application()
            if application.status not in {
                ScholarshipApplication.STATUS_SUBMITTED,
                ScholarshipApplication.STATUS_UNDER_VERIFICATION,
            }:
                raise ValidationError(
                    {"status": "Only submitted or verified applications can be decided."}
                )
            application.status = target_status
            application.decision_note = decision_note
            application.decided_by_user_id = request.principal.user_id
            application.decided_at = timezone.now()
            application.save(update_fields=[
                "status",
                "decision_note",
                "decided_by_user_id",
                "decided_at",
                "updated_at",
            ])
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, application_id=None):
        return self._decide(
            request, target_status=ScholarshipApplication.STATUS_APPROVED,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, application_id=None):
        return self._decide(
            request, target_status=ScholarshipApplication.STATUS_REJECTED,
        )

    @action(detail=True, methods=["post"])
    def return_for_correction(self, request, application_id=None):
        return self._decide(
            request, target_status=ScholarshipApplication.STATUS_CORRECTION_REQUIRED,
        )


class SupportingDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = SupportingDocumentSerializer
    permission_classes = [IsStudentSupportingDocument]
    lookup_field = "document_id"

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if principal is None:
            return SupportingDocument.objects.none()
        return SupportingDocument.objects.filter(owner_user_id=principal.user_id)

    def perform_create(self, serializer):
        serializer.save(owner_user_id=self.request.principal.user_id)
