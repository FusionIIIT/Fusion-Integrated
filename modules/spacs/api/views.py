from uuid import UUID

from django.db import models
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from fusion_auth.principal import Principal
from modules.spacs.api import serializers as s
from modules.spacs.models import Application, WorkflowTask
from modules.spacs.services import (
    applications,
    awards,
    catalogue,
    evidence,
    notifications,
    workflow,
)
from modules.spacs.services.errors import IntegrationUnavailableError

MODULE = HasModuleGrant("spacs")


def _notification_roles(principal: Principal) -> tuple[str, ...]:
    role_permissions = (
        (workflow.ASSISTANT, "spacs.application.verify"),
        (workflow.CONVENER, "spacs.application.decide"),
        (workflow.CONVENER, "spacs.award.manage"),
        ("Award Evaluation Committee", "spacs.award.evaluate"),
        (workflow.CONVENER, "spacs.award.publish"),
        (workflow.CONVENER, "spacs.catalogue.manage"),
        (workflow.CONVENER, "spacs.catalogue.publish"),
    )
    return tuple(
        dict.fromkeys(
            role for role, permission in role_permissions if principal.has_permission(permission)
        )
    )


class CatalogueView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.catalogue.view")]

    def get(self, request):
        versions = catalogue.published_catalogue()
        return Response(s.CatalogueVersionSerializer(versions, many=True).data)


class ApplicationListCreateView(APIView):
    def get_permissions(self):
        permission = (
            HasPermission("spacs.application.view_self")
            if self.request.method == "GET"
            else HasPermission("spacs.application.create")
        )
        return [MODULE(), permission()]

    def get(self, request):
        rows = Application.objects.filter(
            user_id=request.principal.user_id,
        ).order_by("-created_at")
        return Response(s.ApplicationSerializer(rows, many=True).data)

    def post(self, request):
        payload = s.ApplicationStartSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = applications.start_application(
            user_id=request.principal.user_id,
            **payload.validated_data,
        )
        return Response(
            s.ApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicationDetailView(APIView):
    def get_permissions(self):
        permission = (
            HasPermission("spacs.application.view_self")
            if self.request.method == "GET"
            else HasPermission("spacs.application.create")
        )
        return [MODULE(), permission()]

    def get(self, request, public_id: UUID):
        application = Application.objects.filter(
            public_id=public_id,
            user_id=request.principal.user_id,
        ).first()
        if application is None:
            raise NotFoundError("No such application.")
        return Response(s.ApplicationSerializer(application).data)

    def patch(self, request, public_id: UUID):
        payload = s.ApplicationDraftSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = applications.save_draft(
            application_id=public_id,
            user_id=request.principal.user_id,
            **payload.validated_data,
        )
        return Response(s.ApplicationSerializer(application).data)


class ApplicationSubmitView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.create")]

    def post(self, request, public_id: UUID):
        application = applications.submit_application(
            application_id=public_id,
            user_id=request.principal.user_id,
        )
        return Response(s.ApplicationSerializer(application).data)


class ApplicationResubmitView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.create")]

    def post(self, request, public_id: UUID):
        application = applications.resubmit_application(
            application_id=public_id,
            user_id=request.principal.user_id,
        )
        return Response(s.ApplicationSerializer(application).data)


class ApplicationEvidenceUploadView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.create")]

    def post(self, request, public_id: UUID):
        payload = s.EvidenceUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        uploaded_file = payload.validated_data["file"]
        row = evidence.upload(
            public_id=public_id,
            user_id=request.principal.user_id,
            requirement_id=payload.validated_data["requirement_id"],
            filename=uploaded_file.name,
            content_type=uploaded_file.content_type or "",
            content=uploaded_file,
        )
        return Response(
            s.EvidenceSerializer(row).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicationEvidenceReusableView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.create")]

    def get(self, request, public_id: UUID):
        requirement_id = request.query_params.get("requirement_id", "")
        rows = evidence.reusable(
            public_id=public_id,
            user_id=request.principal.user_id,
            requirement_id=requirement_id,
        )
        return Response(s.EvidenceSerializer(rows, many=True).data)


class ApplicationEvidenceReuseView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.create")]

    def post(self, request, public_id: UUID):
        payload = s.EvidenceReuseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = evidence.reuse(
            public_id=public_id,
            user_id=request.principal.user_id,
            **payload.validated_data,
        )
        return Response(s.EvidenceSerializer(row).data, status=status.HTTP_201_CREATED)


class ApplicationEvidenceOwnerDownloadView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.view_self")]

    def get(self, request, public_id: UUID, evidence_id: int):
        return _evidence_response(
            public_id=public_id,
            evidence_id=evidence_id,
            user_id=request.principal.user_id,
        )


class ApplicationEvidenceStaffDownloadView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.view")]

    def get(self, request, public_id: UUID, evidence_id: int):
        return _evidence_response(
            public_id=public_id,
            evidence_id=evidence_id,
            user_id=request.principal.user_id,
        )


def _evidence_response(*, public_id: UUID, evidence_id: int, user_id: int):
    row, content = evidence.open_for_review(
        public_id=public_id,
        evidence_id=evidence_id,
        user_id=user_id,
    )
    metadata = row.metadata
    filename = metadata.get("filename") if isinstance(metadata, dict) else None
    content_type = metadata.get("content_type") if isinstance(metadata, dict) else None
    if not isinstance(filename, str) or not isinstance(content_type, str):
        raise IntegrationUnavailableError("Evidence filename or content type is unavailable.")
    return FileResponse(
        content,
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )


class ApplicationOwnerExportView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.view_self")]

    def get(self, request, public_id: UUID):
        payload = applications.export_application(
            application_id=public_id,
            actor_user_id=request.principal.user_id,
            owner_user_id=request.principal.user_id,
        )
        response = Response(payload)
        response["Content-Disposition"] = (
            f'attachment; filename="spacs-application-{public_id}.json"'
        )
        return response


class ApplicationStaffExportView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.export")]

    def get(self, request, public_id: UUID):
        payload = applications.export_application(
            application_id=public_id,
            actor_user_id=request.principal.user_id,
        )
        response = Response(payload)
        response["Content-Disposition"] = (
            f'attachment; filename="spacs-application-{public_id}.json"'
        )
        return response


class VerificationQueueView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.verify")]

    def get(self, request):
        tasks = (
            WorkflowTask.objects.filter(
                application__isnull=False,
                role_name=workflow.ASSISTANT,
                completed_at__isnull=True,
            )
            .filter(
                models.Q(assigned_user_id__isnull=True)
                | models.Q(assigned_user_id=request.principal.user_id)
            )
            .select_related("application", "application__catalogue_version")
            .prefetch_related("application__reviews")
            .order_by("created_at")
        )
        return Response(s.WorkflowTaskSerializer(tasks, many=True).data)


class DecisionQueueView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.decide")]

    def get(self, request):
        tasks = (
            WorkflowTask.objects.filter(
                application__isnull=False,
                role_name=workflow.CONVENER,
                completed_at__isnull=True,
            )
            .filter(
                models.Q(assigned_user_id__isnull=True)
                | models.Q(assigned_user_id=request.principal.user_id)
            )
            .select_related("application", "application__catalogue_version")
            .prefetch_related("application__reviews")
            .order_by("created_at")
        )
        return Response(s.WorkflowTaskSerializer(tasks, many=True).data)


class ApplicationReviewFindingsView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.verify")]

    def post(self, request, public_id: UUID):
        payload = s.ApplicationReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        review = workflow.record_findings(
            public_id=public_id,
            reviewer_user_id=request.principal.user_id,
            findings=payload.validated_data["findings"],
        )
        return Response(
            {"id": review.pk, "application_id": str(public_id), "at": review.at},
            status=status.HTTP_201_CREATED,
        )


class ApplicationVerificationActionView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.verify")]

    def post(self, request, public_id: UUID, action: str):
        user_id = request.principal.user_id
        if action == "open":
            application = workflow.begin_verification(
                public_id=public_id,
                user_id=user_id,
            )
        elif action == "correction":
            payload = s.WorkflowReasonSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            application = workflow.request_correction(
                public_id=public_id,
                user_id=user_id,
                reason=payload.validated_data["reason"],
            )
        elif action == "route":
            payload = s.VerificationRouteSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            application = workflow.route_verification(
                public_id=public_id,
                user_id=user_id,
                concern=payload.validated_data["concern"],
            )
        else:
            raise NotFoundError("No such verification action.")
        return Response(s.ApplicationSerializer(application).data)


class ApplicationDecisionActionView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.decide")]

    def post(self, request, public_id: UUID, action: str):
        user_id = request.principal.user_id
        if action == "open":
            application = workflow.begin_convener_review(
                public_id=public_id,
                user_id=user_id,
            )
        elif action in {"approve", "reject"}:
            payload = s.WorkflowDecisionSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            application = workflow.decide(
                public_id=public_id,
                user_id=user_id,
                outcome="Approved" if action == "approve" else "Rejected",
                reason=payload.validated_data["reason"],
            )
        elif action == "correction":
            payload = s.WorkflowReasonSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            application = workflow.request_correction(
                public_id=public_id,
                user_id=user_id,
                actor=workflow.CONVENER,
                reason=payload.validated_data["reason"],
            )
        else:
            raise NotFoundError("No such decision action.")
        return Response(s.ApplicationSerializer(application).data)


class AwardCycleCreateView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.award.manage")]

    def post(self, request):
        payload = s.AwardCycleStartSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cycle = awards.create_cycle(
            actor_user_id=request.principal.user_id,
            **payload.validated_data,
        )
        return Response(
            s.AwardCycleSerializer(cycle).data,
            status=status.HTTP_201_CREATED,
        )


class AwardCandidateBatchView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.award.manage")]

    def post(self, request, cycle_id: int):
        payload = s.AwardCandidateBatchSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        candidates = awards.add_candidates(
            cycle_id=cycle_id,
            actor_user_id=request.principal.user_id,
            **payload.validated_data,
        )
        return Response(
            s.AwardCandidateSerializer(candidates, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class NotificationInboxView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.view_self")]

    def get(self, request):
        rows = notifications.inbox_for_user(
            user_id=request.principal.user_id,
            recipient_roles=_notification_roles(request.principal),
        )
        return Response(
            [
                {
                    "id": row.pk,
                    "topic": row.topic,
                    "payload": row.payload,
                    "created_at": row.created_at,
                    "read_at": row.read_at,
                }
                for row in rows
            ]
        )


class NotificationReadView(APIView):
    permission_classes = [MODULE, HasPermission("spacs.application.view_self")]

    def post(self, request, notification_id: int):
        row = notifications.mark_inbox_read(
            notification_id=notification_id,
            user_id=request.principal.user_id,
            recipient_roles=_notification_roles(request.principal),
        )
        return Response({"id": row.pk, "read_at": row.read_at})
