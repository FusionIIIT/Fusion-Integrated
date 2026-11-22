from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.api import serializers as s
from modules.badms.models import (
    BackupRun,
    BackupSchedule,
    SecurityPolicyVersion,
)
from modules.badms.selectors import scoping
from modules.badms.services import audit, workflows
from modules.badms.services.authz import require

MODULE = HasModuleGrant("badms")


class BadmsAPIView(APIView):
    def authorize(self, request, permission):
        self.permission_classes = [MODULE, HasPermission(permission)]
        self.check_permissions(request)


class BackupListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.backup.view")
        require(request.principal, "badms.backup.view")
        rows = scoping.backups_for(request.principal).order_by("-created_at")[:100]
        return Response(s.BackupRunSerializer(rows, many=True).data)

    def post(self, request):
        self.authorize(request, "badms.backup.create")
        dataset = request.data.get("dataset_key", "fusion_integrated")
        if (not isinstance(dataset, str)
                or dataset not in settings.BADMS_DATASETS):
            raise ValidationError({
                "dataset_key": "Choose a configured backup dataset.",
            })
        row = BackupRun.objects.create(
            dataset_key=dataset.strip(),
            trigger=BackupRun.Trigger.MANUAL,
            started_by_user_id=request.principal.user_id,
        )
        audit.record(actor_user_id=request.principal.user_id, action="queue",
                     resource="backup", resource_id=str(row.pk))
        from modules.badms.tasks import run_backup

        run_backup.delay(row.pk)
        return Response(s.BackupRunSerializer(row).data,
                        status=status.HTTP_202_ACCEPTED)


class BackupDetailView(BadmsAPIView):
    permission_classes = [MODULE, HasPermission("badms.backup.view")]

    def get(self, request, pk):
        self.check_permissions(request)
        row = scoping.backups_for(request.principal).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("Backup run not found.")
        return Response(s.BackupRunSerializer(row).data)


class ScheduleListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.schedule.view")
        rows = BackupSchedule.objects.order_by("scope", "dataset_key")
        return Response(s.BackupScheduleSerializer(rows, many=True).data)

    def post(self, request):
        self.authorize(request, "badms.schedule.create")
        payload = s.BackupScheduleSerializer(data=request.data,
                                             context={"request": request})
        payload.is_valid(raise_exception=True)
        row = payload.save()
        audit.record(actor_user_id=request.principal.user_id, action="create",
                     resource="schedule", resource_id=str(row.pk))
        return Response(s.BackupScheduleSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ScheduleDetailView(BadmsAPIView):
    def patch(self, request, pk):
        self.authorize(request, "badms.schedule.update")
        row = BackupSchedule.objects.filter(pk=pk).first()
        if row is None:
            raise NotFoundError("Backup schedule not found.")
        payload = s.BackupScheduleSerializer(
            row, data=request.data, partial=True, context={"request": request},
        )
        payload.is_valid(raise_exception=True)
        row = payload.save()
        audit.record(actor_user_id=request.principal.user_id, action="update",
                     resource="schedule", resource_id=str(row.pk))
        return Response(s.BackupScheduleSerializer(row).data)


class ArchivalListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.archive.view")
        rows = scoping.archival_requests_for(request.principal).order_by("-created_at")
        return Response(s.ArchivalRequestSerializer(rows[:100], many=True).data)

    def post(self, request):
        self.authorize(request, "badms.archive.create")
        payload = s.ArchivalRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = workflows.submit_archival_request(
            actor=request.principal, data=payload.validated_data,
        )
        return Response(s.ArchivalRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ArchivalDetailView(BadmsAPIView):
    permission_classes = [MODULE, HasPermission("badms.archive.view")]

    def get(self, request, pk):
        self.check_permissions(request)
        row = scoping.archival_requests_for(request.principal).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("Archival request not found.")
        return Response(s.ArchivalRequestSerializer(row).data)


class ArchivalDecisionView(BadmsAPIView):
    def post(self, request, pk):
        self.authorize(request, "badms.archive.approve")
        payload = s.ArchivalDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = workflows.decide_archival_request(
            actor=request.principal, request_id=pk,
            approved=payload.validated_data["approved"],
            reason=payload.validated_data.get("reason", ""),
        )
        return Response(s.ArchivalRequestSerializer(row).data)


class ArchivalClassificationView(BadmsAPIView):
    def post(self, request, pk):
        self.authorize(request, "badms.archive.assign")
        payload = s.ClassificationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = workflows.classify_archival_request(
            actor=request.principal, request_id=pk,
            classification=payload.validated_data["classification"],
        )
        return Response(s.ArchivalRequestSerializer(row).data)


class EncryptionConfiguredView(BadmsAPIView):
    def post(self, request, pk):
        self.authorize(request, "badms.encryption.manage")
        row = workflows.mark_encryption_configured(
            actor=request.principal, request_id=pk,
        )
        return Response(s.ArchivalRequestSerializer(row).data)


class SpecialArchivalView(BadmsAPIView):
    def post(self, request):
        self.authorize(request, "badms.archive.create")
        payload = s.ArchivalRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = workflows.submit_special_archival(
            actor=request.principal, data=payload.validated_data,
        )
        return Response(s.ArchivalRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class RestoreListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.restore.view")
        rows = scoping.restoration_requests_for(request.principal).order_by(
            "-created_at",
        )
        return Response(s.RestoreRequestSerializer(rows[:100], many=True).data)

    def post(self, request):
        self.authorize(request, "badms.restore.create")
        archive_id = request.data.get("archive")
        reason = request.data.get("reason", "")
        if not isinstance(archive_id, int) or not isinstance(reason, str) or not reason:
            raise ValidationError({"detail": "archive and reason are required."})
        row = workflows.submit_restore_request(
            actor=request.principal, archive_id=archive_id, reason=reason,
        )
        return Response(s.RestoreRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class RestoreDecisionView(BadmsAPIView):
    def post(self, request, pk):
        self.authorize(request, "badms.restore.approve")
        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            raise ValidationError({"approved": "A boolean decision is required."})
        row = workflows.decide_restore_request(
            actor=request.principal, request_id=pk, approved=approved,
        )
        return Response(s.RestoreRequestSerializer(row).data)


class RestoreExecuteView(BadmsAPIView):
    def post(self, request, pk):
        self.authorize(request, "badms.restore.restore")
        row, path = workflows.execute_restore_request(
            actor=request.principal, request_id=pk,
        )
        try:
            response = FileResponse(
                Path(path).open("rb"),  # noqa: SIM115 -- FileResponse owns this stream.
                as_attachment=True,
                filename=row.archive.file_name,
                content_type="application/octet-stream",
            )
        except OSError:
            Path(path).unlink(missing_ok=True)
            raise
        response._resource_closers.append(
            lambda: Path(path).unlink(missing_ok=True),
        )
        return response


class StorageExtensionListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.storage_extension.view")
        rows = scoping.storage_extensions_for(request.principal).order_by(
            "-created_at",
        )
        return Response(s.StorageExtensionSerializer(rows[:100], many=True).data)

    def post(self, request):
        self.authorize(request, "badms.storage_extension.create")
        payload = s.StorageExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = workflows.submit_storage_extension(
            actor=request.principal,
            requested_bytes=payload.validated_data["requested_bytes"],
            justification=payload.validated_data["justification"],
        )
        return Response(s.StorageExtensionSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class StorageExtensionDecisionView(BadmsAPIView):
    def post(self, request, pk):
        self.authorize(request, "badms.storage_extension.approve")
        payload = s.ArchivalDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = workflows.decide_storage_extension(
            actor=request.principal, request_id=pk,
            approved=payload.validated_data["approved"],
            reason=payload.validated_data.get("reason", ""),
        )
        return Response(s.StorageExtensionSerializer(row).data)


class AuditListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.audit_event.view")
        rows = scoping.audit_events_for(request.principal).order_by(
            "-occurred_at",
        )[:200]
        return Response([{
            "id": row.pk, "actor_user_id": row.actor_user_id,
            "action": row.action, "resource": row.resource,
            "resource_id": row.resource_id, "outcome": row.outcome,
            "details": row.details, "occurred_at": row.occurred_at,
        } for row in rows])


class ReportsView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.report.view")
        archives = scoping.archival_requests_for(request.principal)
        backups = scoping.backups_for(request.principal)
        extensions = scoping.storage_extensions_for(request.principal)
        return Response({
            "archives_by_status": dict(
                archives.values_list("status").annotate(n=Count("id"))
                .values_list("status", "n")),
            "backups_by_status": dict(
                backups.values_list("status").annotate(n=Count("id"))
                .values_list("status", "n")),
            "storage_extensions_by_status": dict(
                extensions.values_list("status").annotate(n=Count("id"))
                .values_list("status", "n")),
            "generated_at": timezone.now(),
        })


class SecurityPolicyListView(BadmsAPIView):
    def get(self, request):
        self.authorize(request, "badms.security_policy.manage")
        rows = SecurityPolicyVersion.objects.order_by(
            "classification", "-effective_from",
        )
        return Response(s.SecurityPolicySerializer(rows, many=True).data)

    def post(self, request):
        self.authorize(request, "badms.security_policy.manage")
        payload = s.SecurityPolicySerializer(
            data=request.data, context={"request": request},
        )
        payload.is_valid(raise_exception=True)
        row = payload.save()
        audit.record(actor_user_id=request.principal.user_id, action="create",
                     resource="security_policy", resource_id=str(row.pk))
        return Response(s.SecurityPolicySerializer(row).data,
                        status=status.HTTP_201_CREATED)
