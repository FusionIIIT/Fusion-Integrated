from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.api import serializers as s
from modules.badms.selectors import (
    get_department_report,
    scope_archival_requests,
    scope_audit_events,
    scope_backup_records,
    scope_backup_schedules,
    scope_restoration_requests,
    scope_security_policies,
    scope_storage_extensions,
)
from modules.badms.services import (
    approve_sensitive_restoration,
    classify_archival_request,
    configure_sensitive_encryption,
    create_backup_schedule,
    decide_archival_request,
    decide_storage_extension,
    execute_data_restoration,
    perform_special_archival,
    request_data_restoration,
    save_security_policy,
    submit_archival_request,
    submit_storage_extension,
    trigger_manual_backup,
    update_backup_schedule,
)

MODULE = HasModuleGrant("badms")


def _actor(request):
    return getattr(request, "principal", None)


# -- Backups -------------------------------------------------------------------
class ManualBackupView(APIView):
    permission_classes = [MODULE, HasPermission("badms.backup.manage")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.TriggerManualBackupSerializer, responses={201: s.BackupRecordSerializer}
    )
    def post(self, request):
        ser = s.TriggerManualBackupSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        record = trigger_manual_backup(_actor(request), ser.validated_data["dataset_name"])
        return Response(s.BackupRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class BackupRecordListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("badms.backup.view")]
    serializer_class = s.BackupRecordSerializer

    def get_queryset(self):
        return scope_backup_records(_actor(self.request))


class BackupRecordDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission("badms.backup.view")]
    serializer_class = s.BackupRecordSerializer

    def get_queryset(self):
        return scope_backup_records(_actor(self.request))


# -- Schedules -----------------------------------------------------------------
class BackupScheduleListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("badms.backup.view")]
    serializer_class = s.BackupScheduleSerializer

    def get_queryset(self):
        return scope_backup_schedules(_actor(self.request))


class CreateLocalScheduleView(APIView):
    permission_classes = [MODULE, HasPermission("badms.backup.manage")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.CreateBackupScheduleSerializer, responses={201: s.BackupScheduleSerializer}
    )
    def post(self, request):
        ser = s.CreateBackupScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sched = create_backup_schedule(_actor(request), scope_type="local", **ser.validated_data)
        return Response(s.BackupScheduleSerializer(sched).data, status=status.HTTP_201_CREATED)


class UpdateLocalScheduleView(APIView):
    permission_classes = [MODULE, HasPermission("badms.backup.manage")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.UpdateBackupScheduleSerializer, responses={200: s.BackupScheduleSerializer}
    )
    def put(self, request, pk: int):
        ser = s.UpdateBackupScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sched = update_backup_schedule(_actor(request), schedule_id=pk, **ser.validated_data)
        return Response(s.BackupScheduleSerializer(sched).data, status=status.HTTP_200_OK)

    patch = put


class CreateGlobalScheduleView(APIView):
    permission_classes = [MODULE, HasPermission("badms.backup_policy.manage")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.CreateBackupScheduleSerializer, responses={201: s.BackupScheduleSerializer}
    )
    def post(self, request):
        ser = s.CreateBackupScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sched = create_backup_schedule(_actor(request), scope_type="global", **ser.validated_data)
        return Response(s.BackupScheduleSerializer(sched).data, status=status.HTTP_201_CREATED)


# -- Archival Requests ---------------------------------------------------------
class ArchivalRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = s.ArchivalRequestSerializer
    throttle_scope = "badms_write"

    def get_permissions(self):
        perm = "badms.archival.create" if self.request.method == "POST" else "badms.archival.view"
        return [MODULE(), HasPermission(perm)()]

    def get_queryset(self):
        return scope_archival_requests(_actor(self.request))

    @extend_schema(
        request=s.SubmitArchivalRequestSerializer, responses={201: s.ArchivalRequestSerializer}
    )
    def post(self, request, *args, **kwargs):
        ser = s.SubmitArchivalRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = submit_archival_request(_actor(request), **ser.validated_data)
        return Response(s.ArchivalRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class ArchivalRequestDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission("badms.archival.view")]
    serializer_class = s.ArchivalRequestSerializer

    def get_queryset(self):
        return scope_archival_requests(_actor(self.request))


class DecideArchivalRequestView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archival.approve")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.DecideArchivalRequestSerializer, responses={200: s.ArchivalRequestSerializer}
    )
    def post(self, request, pk: int):
        ser = s.DecideArchivalRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = decide_archival_request(_actor(request), request_id=pk, **ser.validated_data)
        return Response(s.ArchivalRequestSerializer(req).data, status=status.HTTP_200_OK)


class ClassifyArchivalRequestView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archival.review")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.ClassifyArchivalRequestSerializer, responses={200: s.ArchivalRequestSerializer}
    )
    def post(self, request, pk: int):
        ser = s.ClassifyArchivalRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = classify_archival_request(_actor(request), request_id=pk, **ser.validated_data)
        return Response(s.ArchivalRequestSerializer(req).data, status=status.HTTP_200_OK)


class ConfigureEncryptionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.security.manage")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.ConfigureEncryptionSerializer, responses={200: s.ArchivalRequestSerializer}
    )
    def post(self, request, pk: int):
        ser = s.ConfigureEncryptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = configure_sensitive_encryption(_actor(request), request_id=pk, **ser.validated_data)
        return Response(s.ArchivalRequestSerializer(req).data, status=status.HTTP_200_OK)


class SpecialArchivalView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archival.manage")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.SpecialArchivalSerializer, responses={201: s.ArchivalRequestSerializer}
    )
    def post(self, request):
        ser = s.SpecialArchivalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = perform_special_archival(_actor(request), **ser.validated_data)
        return Response(s.ArchivalRequestSerializer(req).data, status=status.HTTP_201_CREATED)


# -- Storage Extensions --------------------------------------------------------
class StorageExtensionListCreateView(generics.ListCreateAPIView):
    serializer_class = s.StorageExtensionRequestSerializer
    throttle_scope = "badms_write"

    def get_permissions(self):
        perm = "badms.storage.create" if self.request.method == "POST" else "badms.storage.view"
        return [MODULE(), HasPermission(perm)()]

    def get_queryset(self):
        return scope_storage_extensions(_actor(self.request))

    @extend_schema(
        request=s.SubmitStorageExtensionSerializer,
        responses={201: s.StorageExtensionRequestSerializer},
    )
    def post(self, request, *args, **kwargs):
        ser = s.SubmitStorageExtensionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = submit_storage_extension(_actor(request), **ser.validated_data)
        return Response(
            s.StorageExtensionRequestSerializer(req).data, status=status.HTTP_201_CREATED
        )


class DecideStorageExtensionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.storage.approve")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.DecideStorageExtensionSerializer,
        responses={200: s.StorageExtensionRequestSerializer},
    )
    def post(self, request, pk: int):
        ser = s.DecideStorageExtensionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = decide_storage_extension(_actor(request), request_id=pk, **ser.validated_data)
        return Response(s.StorageExtensionRequestSerializer(req).data, status=status.HTTP_200_OK)


# -- Restoration ---------------------------------------------------------------
class RestorationListCreateView(generics.ListCreateAPIView):
    serializer_class = s.RestorationRequestSerializer
    throttle_scope = "badms_write"

    def get_permissions(self):
        perm = (
            "badms.restoration.create"
            if self.request.method == "POST"
            else "badms.restoration.view"
        )
        return [MODULE(), HasPermission(perm)()]

    def get_queryset(self):
        return scope_restoration_requests(_actor(self.request))

    @extend_schema(
        request=s.RequestRestorationSerializer, responses={201: s.RestorationRequestSerializer}
    )
    def post(self, request, *args, **kwargs):
        ser = s.RequestRestorationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = request_data_restoration(_actor(request), **ser.validated_data)
        return Response(s.RestorationRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class ApproveSensitiveRestorationView(APIView):
    permission_classes = [MODULE, HasPermission("badms.restoration.approve")]
    throttle_scope = "badms_write"

    @extend_schema(
        request=s.ApproveSensitiveRestorationSerializer,
        responses={200: s.RestorationRequestSerializer},
    )
    def post(self, request, pk: int):
        ser = s.ApproveSensitiveRestorationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = approve_sensitive_restoration(
            _actor(request), restoration_id=pk, **ser.validated_data
        )
        return Response(s.RestorationRequestSerializer(req).data, status=status.HTTP_200_OK)


class ExecuteRestorationView(APIView):
    permission_classes = [MODULE, HasPermission("badms.restoration.restore")]
    throttle_scope = "badms_write"
    serializer_class = s.RestorationRequestSerializer

    @extend_schema(request=None, responses={200: s.RestorationRequestSerializer})
    def post(self, request, pk: int):
        req = execute_data_restoration(_actor(request), restoration_id=pk)
        return Response(s.RestorationRequestSerializer(req).data, status=status.HTTP_200_OK)


# -- Audits & Reports ----------------------------------------------------------
class AuditEventListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("badms.audit.view")]
    serializer_class = s.AuditEventSerializer

    def get_queryset(self):
        return scope_audit_events(_actor(self.request))


class SecurityAuditEventListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("badms.audit.view")]
    serializer_class = s.AuditEventSerializer

    def get_queryset(self):
        return scope_audit_events(_actor(self.request)).filter(
            event_type__in=[
                "archival_encryption_configured",
                "security_policy_saved",
                "backup_failure_escalated",
            ]
        )


class DepartmentReportView(APIView):
    permission_classes = [MODULE, HasPermission("badms.report.view")]

    @extend_schema(responses={200: s.DepartmentReportSerializer})
    def get(self, request):
        dept = (
            request.query_params.get("department")
            or getattr(_actor(request), "department", "")
            or ""
        )
        if not dept:
            raise BadRequestError("Department parameter is required.")
        actor = _actor(request)
        if getattr(actor, "active_role", "") == "HOD" and getattr(actor, "department", "") != dept:
            raise NotFoundError("Department not found in your authorized scope.")
        report = get_department_report(actor, dept)
        return Response(s.DepartmentReportSerializer(report).data, status=status.HTTP_200_OK)


# -- Security Policies ---------------------------------------------------------
class SecurityPolicyListCreateView(generics.ListCreateAPIView):
    serializer_class = s.SecurityPolicySerializer
    permission_classes = [MODULE, HasPermission("badms.security.manage")]
    throttle_scope = "badms_write"

    def get_queryset(self):
        return scope_security_policies(_actor(self.request))

    @extend_schema(
        request=s.SaveSecurityPolicySerializer, responses={201: s.SecurityPolicySerializer}
    )
    def post(self, request, *args, **kwargs):
        ser = s.SaveSecurityPolicySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        policy = save_security_policy(_actor(request), **ser.validated_data)
        return Response(s.SecurityPolicySerializer(policy).data, status=status.HTTP_201_CREATED)
