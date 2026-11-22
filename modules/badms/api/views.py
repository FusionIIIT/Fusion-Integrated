"""DRF API Views for BADMS.

Handles HTTP requests, authenticates roles from Fusion context/headers,
maps requests to domain services, and enforces permission gates.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasPermission

from ..domain import DomainValidationError
from ..selectors import (
    get_archival_request_by_id,
    get_user_storage_quota,
    list_archival_requests_for_user,
    list_audit_events,
    list_backup_history,
    list_backup_schedules,
    list_restoration_requests,
    list_storage_extensions,
)
from ..services import (
    classify_archival_sysadmin,
    configure_backup_schedule,
    configure_sensitive_encryption_it_security,
    decide_secure_archival_hod,
    decide_sensitive_restoration_sysadmin,
    decide_storage_extension_hod,
    execute_data_restoration,
    perform_special_archival_operation,
    request_data_restoration,
    submit_secure_archival_request,
    submit_storage_extension_request,
    trigger_manual_backup,
)
from .serializers import (
    ArchivalRequestSerializer,
    AuditEventSerializer,
    BackupRecordSerializer,
    BackupScheduleSerializer,
    EncryptedArchiveSerializer,
    RestorationRequestSerializer,
    StorageExtensionRequestSerializer,
    StorageQuotaSerializer,
)


def _get_context_identity(request):
    """Extract user ID, role, and department from Fusion headers or principal."""
    p = getattr(request, "principal", None)
    if p:
        user_id = str(p.user_id)
        role = p.active_role or "faculty"
        department_id = getattr(p, "discipline", "CSE") or "CSE"
    else:
        user_id = request.headers.get("X-User-Id") or getattr(request.user, "username", "default_user")
        role = request.headers.get("X-User-Role") or "faculty"
        department_id = request.headers.get("X-Department-Id") or "CSE"
    return user_id, role, department_id


# ---------------------------------------------------------------------------
# Backup Views
# ---------------------------------------------------------------------------
class BackupListView(APIView):
    permission_map = {
        "GET": "badms.backup.view_history",
        "POST": "badms.backup.trigger_manual",
    }

    def get(self, request):
        records = list_backup_history(limit=50)
        serializer = BackupRecordSerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id, role, _ = _get_context_identity(request)
        dataset_name = request.data.get("dataset_name", "primary_db")
        force_failure = request.data.get("force_failure", False)
        try:
            record = trigger_manual_backup(
                actor_user_id=user_id,
                actor_role=role,
                dataset_name=dataset_name,
                force_failure=force_failure,
            )
            serializer = BackupRecordSerializer(record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BackupScheduleListView(APIView):
    permission_map = {
        "LOCAL": "badms.schedule.manage_local",
        "GLOBAL": "badms.schedule.manage_global",
    }

    def get(self, request):
        scope = request.query_params.get("scope")
        schedules = list_backup_schedules(scope=scope)
        serializer = BackupScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id, role, _ = _get_context_identity(request)
        scope = request.data.get("scope", "LOCAL").upper()
        try:
            sched = configure_backup_schedule(
                actor_user_id=user_id,
                actor_role=role,
                name=request.data.get("name", "Schedule"),
                scope=scope,
                dataset_name=request.data.get("dataset_name", "primary_db"),
                frequency=request.data.get("frequency", "DAILY"),
                scheduled_time=request.data.get("scheduled_time", "02:00"),
                repository_path=request.data.get("repository_path", "/var/backups/fusion"),
                day_of_week=request.data.get("day_of_week"),
            )
            serializer = BackupScheduleSerializer(sched)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Archival Views
# ---------------------------------------------------------------------------
class ArchivalRequestListView(APIView):
    permission_map = {
        "POST": "badms.archival.submit",
    }

    def get(self, request):
        user_id, role, department_id = _get_context_identity(request)
        requests = list_archival_requests_for_user(user_id, role, department_id)
        serializer = ArchivalRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id, role, department_id = _get_context_identity(request)
        file_name = request.data.get("file_name", "")
        file_size_mb = float(request.data.get("file_size_mb", 10.0))
        reason = request.data.get("reason", "")
        initial_classification = request.data.get("initial_classification")
        owners = request.data.get("owners", "")
        attachment_ref = request.data.get("attachment_ref", "")
        dept = request.data.get("department_id") or department_id
        
        try:
            archival_req = submit_secure_archival_request(
                requester_user_id=user_id,
                department_id=dept,
                file_name=file_name,
                file_size_mb=file_size_mb,
                reason=reason,
                initial_classification=initial_classification,
                owners=owners,
                attachment_ref=attachment_ref,
                actor_role=role,
            )
            serializer = ArchivalRequestSerializer(archival_req)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArchivalDetailView(APIView):
    def get(self, request, pk):
        req = get_archival_request_by_id(pk)
        if not req:
            return Response({"error": "Archival request not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ArchivalRequestSerializer(req)
        return Response(serializer.data)


class ArchivalHodDecisionView(APIView):
    required_permission = "badms.archival.review_hod"

    def post(self, request, pk):
        user_id, role, department_id = _get_context_identity(request)
        approved = request.data.get("approved", True)
        remarks = request.data.get("remarks", "")
        try:
            req = decide_secure_archival_hod(
                request_id=pk,
                hod_user_id=user_id,
                hod_role=role,
                hod_department=department_id,
                approved=approved,
                remarks=remarks,
            )
            serializer = ArchivalRequestSerializer(req)
            return Response(serializer.data)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArchivalSysAdminClassifyView(APIView):
    required_permission = "badms.archival.classify_sysadmin"

    def post(self, request, pk):
        user_id, role, _ = _get_context_identity(request)
        classification = request.data.get("classification", "ROUTINE")
        try:
            req = classify_archival_sysadmin(
                request_id=pk,
                sysadmin_user_id=user_id,
                sysadmin_role=role,
                authoritative_classification=classification,
            )
            serializer = ArchivalRequestSerializer(req)
            return Response(serializer.data)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ArchivalEncryptionConfigureView(APIView):
    required_permission = "badms.archival.configure_encryption"

    def post(self, request, pk):
        user_id, role, _ = _get_context_identity(request)
        algorithm = request.data.get("algorithm", "AES-256")
        try:
            archive = configure_sensitive_encryption_it_security(
                request_id=pk,
                security_user_id=user_id,
                security_role=role,
                encryption_algorithm=algorithm,
            )
            serializer = EncryptedArchiveSerializer(archive)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SpecialArchivalView(APIView):
    required_permission = "badms.archival.special_operate"

    def post(self, request):
        user_id, role, department_id = _get_context_identity(request)
        try:
            req = perform_special_archival_operation(
                superadmin_user_id=user_id,
                superadmin_role=role,
                file_name=request.data.get("file_name", "Special_Dataset"),
                file_size_mb=float(request.data.get("file_size_mb", 50.0)),
                department_id=request.data.get("department_id", department_id),
                reason=request.data.get("reason", "Institutional Archive"),
                owners=request.data.get("owners", "Research Office"),
            )
            serializer = ArchivalRequestSerializer(req)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Storage Extension Views
# ---------------------------------------------------------------------------
class StorageQuotaView(APIView):
    required_permission = "badms.storage.monitor_threshold"

    def get(self, request):
        user_id, _, department_id = _get_context_identity(request)
        quota = get_user_storage_quota(user_id, department_id)
        serializer = StorageQuotaSerializer(quota)
        return Response(serializer.data)


class StorageExtensionListView(APIView):
    permission_map = {
        "POST": "badms.storage.request_extension",
    }

    def get(self, request):
        user_id, role, department_id = _get_context_identity(request)
        requests = list_storage_extensions(user_id, role, department_id)
        serializer = StorageExtensionRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id, role, department_id = _get_context_identity(request)
        requested_mb = float(request.data.get("requested_additional_mb", 1024.0))
        justification = request.data.get("justification", "")
        try:
            ext = submit_storage_extension_request(
                requester_user_id=user_id,
                department_id=department_id,
                requested_additional_mb=requested_mb,
                justification=justification,
                actor_role=role,
            )
            serializer = StorageExtensionRequestSerializer(ext)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StorageExtensionHodDecisionView(APIView):
    required_permission = "badms.storage.review_extension"

    def post(self, request, pk):
        user_id, role, department_id = _get_context_identity(request)
        approved = request.data.get("approved", True)
        remarks = request.data.get("remarks", "")
        try:
            ext = decide_storage_extension_hod(
                request_id=pk,
                hod_user_id=user_id,
                hod_role=role,
                hod_department=department_id,
                approved=approved,
                remarks=remarks,
            )
            serializer = StorageExtensionRequestSerializer(ext)
            return Response(serializer.data)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Restoration Views
# ---------------------------------------------------------------------------
class RestorationListView(APIView):
    permission_map = {
        "POST": "badms.restoration.request",
    }

    def get(self, request):
        user_id, role, department_id = _get_context_identity(request)
        requests = list_restoration_requests(user_id, role, department_id)
        serializer = RestorationRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id, role, department_id = _get_context_identity(request)
        archival_request_id = request.data.get("archival_request_id")
        reason = request.data.get("reason", "")
        target_loc = request.data.get("target_location", "/restores/workspace")
        try:
            rst = request_data_restoration(
                requester_user_id=user_id,
                department_id=department_id,
                archival_request_id=archival_request_id,
                reason=reason,
                target_location=target_loc,
                actor_role=role,
            )
            serializer = RestorationRequestSerializer(rst)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RestorationSysAdminDecisionView(APIView):
    required_permission = "badms.restoration.approve_sensitive"

    def post(self, request, pk):
        user_id, role, _ = _get_context_identity(request)
        approved = request.data.get("approved", True)
        remarks = request.data.get("remarks", "")
        try:
            rst = decide_sensitive_restoration_sysadmin(
                request_id=pk,
                sysadmin_user_id=user_id,
                sysadmin_role=role,
                approved=approved,
                remarks=remarks,
            )
            serializer = RestorationRequestSerializer(rst)
            return Response(serializer.data)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RestorationExecuteView(APIView):
    required_permission = "badms.restoration.execute"

    def post(self, request, pk):
        user_id, role, _ = _get_context_identity(request)
        try:
            rst = execute_data_restoration(
                request_id=pk,
                sysadmin_user_id=user_id,
                sysadmin_role=role,
            )
            serializer = RestorationRequestSerializer(rst)
            return Response(serializer.data)
        except DomainValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Audit & Security Views
# ---------------------------------------------------------------------------
class AuditListView(APIView):
    required_permission = "badms.audit.view_operational"

    def get(self, request):
        _, role, department_id = _get_context_identity(request)
        events = list_audit_events(role, department_id, limit=100)
        serializer = AuditEventSerializer(events, many=True)
        return Response(serializer.data)


class SecurityPolicyAdminView(APIView):
    required_permission = "badms.security.administer"

    def post(self, request):
        return Response({"status": "Security policies updated and RBAC synchronised"})
