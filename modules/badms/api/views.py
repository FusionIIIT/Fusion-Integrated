"""DRF views for BADMS endpoints."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.models import (
    BackupOperation,
    BackupSchedule,
    BadmsAuditLog,
    StorageQuota,
)
from modules.badms.selectors import scoping
from modules.badms.services import operations
from modules.badms.api.serializers import (
    BackupOperationSerializer,
    BackupScheduleSerializer,
    SecureArchivalRequestSerializer,
    DataRestorationRequestSerializer,
    StorageQuotaSerializer,
    StorageExtensionRequestSerializer,
    BadmsAuditLogSerializer,
)

MODULE_GUARD = HasModuleGrant("badms")


class BackupOperationListView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.backup.view")]

    def get(self, request):
        ops = BackupOperation.objects.all()[:100]
        return Response(BackupOperationSerializer(ops, many=True).data)

    def post(self, request):
        dataset_code = request.data.get("dataset_code", "all")
        op = operations.trigger_manual_backup(actor=request.user, dataset_code=dataset_code)
        return Response(BackupOperationSerializer(op).data, status=status.HTTP_201_CREATED)


class BackupScheduleListView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.schedule.view")]

    def get(self, request):
        schedules = BackupSchedule.objects.filter(is_active=True)
        return Response(BackupScheduleSerializer(schedules, many=True).data)

    def post(self, request):
        scope = request.data.get("scope", "local")
        dataset_code = request.data.get("dataset_code", "")
        cron = request.data.get("cron_expression", "0 2 * * *")
        retention = int(request.data.get("retention_days", 30))
        sch = operations.configure_schedule(
            actor=request.user,
            scope=scope,
            dataset_code=dataset_code,
            cron_expression=cron,
            retention_days=retention,
        )
        return Response(BackupScheduleSerializer(sch).data, status=status.HTTP_201_CREATED)


class SecureArchivalListView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.archival.request")]

    def get(self, request):
        reqs = scoping.visible_archival_requests(request.user)
        return Response(SecureArchivalRequestSerializer(reqs, many=True).data)

    def post(self, request):
        req = operations.submit_archival_request(
            actor=request.user,
            department=request.data.get("department", "CSE"),
            file_name=request.data.get("file_name", "archive.tar.gz"),
            file_type=request.data.get("file_type", "application/gzip"),
            file_size_bytes=int(request.data.get("file_size_bytes", 0)),
            reason=request.data.get("reason", "Semester archive"),
            initial_classification=request.data.get("initial_classification", "routine"),
        )
        return Response(SecureArchivalRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class ArchivalHodReviewView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.department.review")]

    def post(self, request, pk: int):
        action = request.data.get("action", "approve")
        remarks = request.data.get("remarks", "")
        req = operations.hod_review_archival(actor=request.user, request_id=pk, action=action, remarks=remarks)
        return Response(SecureArchivalRequestSerializer(req).data)


class ArchivalClassifyView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.archival.classify_authoritative")]

    def post(self, request, pk: int):
        tier = request.data.get("authoritative_classification", "routine")
        req = operations.sysadmin_classify_archival(actor=request.user, request_id=pk, authoritative_classification=tier)
        return Response(SecureArchivalRequestSerializer(req).data)


class ArchivalEncryptionView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.security.manage")]

    def post(self, request, pk: int):
        algo = request.data.get("algorithm", "AES-256")
        req = operations.it_security_configure_encryption(actor=request.user, request_id=pk, algorithm=algo)
        return Response(SecureArchivalRequestSerializer(req).data)


class StorageQuotaView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.storage.request")]

    def get(self, request):
        quota, _ = StorageQuota.objects.get_or_create(user_id=request.user.user_id)
        return Response(StorageQuotaSerializer(quota).data)


class StorageExtensionListView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.storage.request")]

    def get(self, request):
        reqs = scoping.visible_storage_extensions(request.user)
        return Response(StorageExtensionRequestSerializer(reqs, many=True).data)

    def post(self, request):
        req = operations.submit_storage_extension(
            actor=request.user,
            department=request.data.get("department", "CSE"),
            requested_additional_mb=int(request.data.get("requested_additional_mb", 1024)),
            reason=request.data.get("reason", "Project data"),
        )
        return Response(StorageExtensionRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class StorageExtensionHodReviewView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.department.review")]

    def post(self, request, pk: int):
        action = request.data.get("action", "approve")
        remarks = request.data.get("remarks", "")
        req = operations.hod_review_storage_extension(actor=request.user, request_id=pk, action=action, remarks=remarks)
        return Response(StorageExtensionRequestSerializer(req).data)


class RestorationListView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.restoration.request")]

    def get(self, request):
        reqs = scoping.visible_restorations(request.user)
        return Response(DataRestorationRequestSerializer(reqs, many=True).data)

    def post(self, request):
        req = operations.submit_restoration_request(
            actor=request.user,
            archival_request_id=int(request.data.get("archival_request_id")),
            reason=request.data.get("reason", "Need access to previous project"),
        )
        return Response(DataRestorationRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class RestorationSysAdminReviewView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.restoration.approve_sensitive")]

    def post(self, request, pk: int):
        action = request.data.get("action", "approve")
        remarks = request.data.get("remarks", "")
        req = operations.sysadmin_review_restoration(actor=request.user, restoration_id=pk, action=action, remarks=remarks)
        return Response(DataRestorationRequestSerializer(req).data)


class AuditLogListView(APIView):
    permission_classes = [MODULE_GUARD, HasPermission("badms.audit.view")]

    def get(self, request):
        logs = BadmsAuditLog.objects.all()[:100]
        return Response(BadmsAuditLogSerializer(logs, many=True).data)
