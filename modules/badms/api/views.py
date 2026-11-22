"""BADMS REST API views.

Strictly adheres to platform structure:
- Views never query models directly; all reads call `selectors`, all writes call `services`.
- Authorization enforced by HasPermission and Principal context.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError
from fusion_auth.permissions import HasPermission, IsAuthenticatedPrincipal
from modules.badms.api.serializers import (
    ArchivalRequestSerializer,
    AuditLogSerializer,
    BackupRecordSerializer,
    BackupScheduleSerializer,
    ClassifyArchivalSerializer,
    ConfigureEncryptionSerializer,
    CreateBackupScheduleSerializer,
    CreateSpecialArchivalSerializer,
    HoDDecisionSerializer,
    RestorationRequestSerializer,
    SecurityPolicySerializer,
    SpecialArchivalRecordSerializer,
    StorageExtensionRequestSerializer,
    SubmitArchivalRequestSerializer,
    SubmitRestorationSerializer,
    SubmitStorageExtensionSerializer,
    SysAdminRestorationDecisionSerializer,
    TriggerManualBackupSerializer,
    UpdateSecurityPolicySerializer,
    UserStorageQuotaSerializer,
)
from modules.badms.domain.errors import (
    BadmsDomainError,
    DepartmentScopeViolation,
    InvalidTransition,
    QuotaExceededError,
    RepositoryUnreachableError,
    RuleViolation,
    StorageNotFullError,
)
from modules.badms.selectors import (
    get_archival_request_by_id,
    get_backup_by_id,
    get_backup_compliance_report,
    get_departmental_report,
    get_security_audit_report,
    get_user_storage_quota,
    list_archival_requests,
    list_audit_logs,
    list_backups,
    list_hod_archival_queue,
    list_hod_storage_extension_queue,
    list_it_security_encryption_queue,
    list_restorations,
    list_schedules,
    list_security_policies,
    list_storage_extensions,
    list_sysadmin_classification_queue,
    list_sysadmin_restoration_queue,
)
from modules.badms.services import (
    classify_archival_request_sysadmin,
    configure_security_policy,
    configure_sensitive_encryption,
    create_schedule,
    decide_archival_request_hod,
    decide_sensitive_restoration_sysadmin,
    decide_storage_extension_hod,
    execute_special_archival,
    execute_technical_restoration,
    submit_archival_request,
    submit_restoration_request,
    submit_storage_extension,
    trigger_manual_backup,
)


def _handle_domain_error(exc: Exception):
    if isinstance(exc, InvalidTransition):
        raise ConflictError(str(exc))
    if isinstance(
        exc,
        (
            BadmsDomainError,
            RuleViolation,
            DepartmentScopeViolation,
            QuotaExceededError,
            StorageNotFullError,
            RepositoryUnreachableError,
        ),
    ):
        raise ValidationError(str(exc))
    raise exc


# -- Backups --
class BackupListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.backup.view")]

    def get(self, request):
        status_param = request.query_params.get("status")
        type_param = request.query_params.get("backup_type")
        backups = list_backups(status=status_param, backup_type=type_param)
        serializer = BackupRecordSerializer(backups[:50], many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})


class ManualBackupTriggerView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.backup.trigger")]

    def post(self, request):
        serializer = TriggerManualBackupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        role = p.active_role or (p.roles[0] if p.roles else "user")

        try:
            record = trigger_manual_backup(
                actor_id=p.user_id,
                actor_username=p.username,
                actor_role=role,
                dataset=serializer.validated_data.get("dataset", "all"),
                repository_path=serializer.validated_data.get(
                    "repository_path", "/var/backups/fusion"
                ),
            )
            return Response(BackupRecordSerializer(record).data, status=status.HTTP_201_CREATED)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class BackupDetailView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.backup.view")]

    def get(self, request, pk: int):
        backup = get_backup_by_id(pk)
        if not backup:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BackupRecordSerializer(backup).data)


# -- Schedules --
class BackupScheduleListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.schedule.view")]

    def get(self, request):
        scope = request.query_params.get("scope")
        schedules = list_schedules(scope=scope)
        serializer = BackupScheduleSerializer(schedules, many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})

    def post(self, request):
        HasPermission("badms.schedule.manage")().has_permission(request, self)
        serializer = CreateBackupScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        role = p.active_role or (p.roles[0] if p.roles else "sysadmin")

        try:
            sched = create_schedule(
                actor_id=p.user_id,
                actor_username=p.username,
                actor_role=role,
                **serializer.validated_data,
            )
            return Response(BackupScheduleSerializer(sched).data, status=status.HTTP_201_CREATED)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


# -- Archival Requests --
class ArchivalRequestListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.archival.view")]

    def get(self, request):
        p = request.principal
        role = p.active_role or (p.roles[0] if p.roles else "user")
        queue = request.query_params.get("queue")

        if queue == "hod" and "badms.archival.hod_decide" in p.permissions:
            dept_id = int(request.query_params.get("department_id", 1))
            requests = list_hod_archival_queue(dept_id)
        elif queue == "classify" and "badms.archival.classify" in p.permissions:
            requests = list_sysadmin_classification_queue()
        elif queue == "encrypt" and "badms.archival.encrypt" in p.permissions:
            requests = list_it_security_encryption_queue()
        elif role in ("sysadmin", "super_admin", "it_security_lead", "Super Admin", "Director"):
            requests = list_archival_requests()
        else:
            requests = list_archival_requests(user_id=p.user_id)

        serializer = ArchivalRequestSerializer(requests[:50], many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})

    def post(self, request):
        HasPermission("badms.archival.submit")().has_permission(request, self)
        serializer = SubmitArchivalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        dept_id = int(request.data.get("department_id", 1))

        try:
            archival = submit_archival_request(
                user_id=p.user_id,
                username=p.username,
                department_id=dept_id,
                **serializer.validated_data,
            )
            return Response(
                ArchivalRequestSerializer(archival).data, status=status.HTTP_201_CREATED
            )
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class ArchivalRequestDetailView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.archival.view")]

    def get(self, request, pk: int):
        archival = get_archival_request_by_id(pk)
        if not archival:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ArchivalRequestSerializer(archival).data)


class HoDArchivalDecisionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.archival.hod_decide")]

    def post(self, request, pk: int):
        serializer = HoDDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        dept_id = int(request.data.get("department_id", 1))

        try:
            archival = decide_archival_request_hod(
                request_id=pk,
                hod_id=p.user_id,
                hod_username=p.username,
                hod_department_id=dept_id,
                approve=serializer.validated_data["approve"],
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            )
            return Response(ArchivalRequestSerializer(archival).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class SysAdminClassifyView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.archival.classify")]

    def post(self, request, pk: int):
        serializer = ClassifyArchivalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal

        try:
            archival = classify_archival_request_sysadmin(
                request_id=pk,
                sysadmin_id=p.user_id,
                sysadmin_username=p.username,
                authoritative_classification=serializer.validated_data[
                    "authoritative_classification"
                ],
            )
            return Response(ArchivalRequestSerializer(archival).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class ITSecurityEncryptionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.archival.encrypt")]

    def post(self, request, pk: int):
        serializer = ConfigureEncryptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal

        try:
            archival = configure_sensitive_encryption(
                request_id=pk,
                security_officer_id=p.user_id,
                security_officer_username=p.username,
                encryption_algorithm=serializer.validated_data.get(
                    "encryption_algorithm", "AES-256"
                ),
            )
            return Response(ArchivalRequestSerializer(archival).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class SpecialArchivalView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.special_archival.execute")]

    def post(self, request):
        serializer = CreateSpecialArchivalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal

        try:
            record = execute_special_archival(
                super_admin_id=p.user_id,
                super_admin_username=p.username,
                **serializer.validated_data,
            )
            return Response(
                SpecialArchivalRecordSerializer(record).data, status=status.HTTP_201_CREATED
            )
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


# -- Storage & Extensions --
class UserStorageQuotaView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.storage.view_self")]

    def get(self, request):
        p = request.principal
        quota = get_user_storage_quota(p.user_id)
        if not quota:
            return Response(
                {
                    "user_id": p.user_id,
                    "department_id": 1,
                    "used_bytes": 0,
                    "quota_bytes": 10737418240,
                    "is_full": False,
                    "available_infra_bytes": 1099511627776,
                }
            )
        return Response(UserStorageQuotaSerializer(quota).data)


class StorageExtensionListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.storage.view")]

    def get(self, request):
        p = request.principal
        queue = request.query_params.get("queue")

        if queue == "hod" and "badms.storage.hod_decide" in p.permissions:
            dept_id = int(request.query_params.get("department_id", 1))
            extensions = list_hod_storage_extension_queue(dept_id)
        else:
            extensions = list_storage_extensions(user_id=p.user_id)

        serializer = StorageExtensionRequestSerializer(extensions, many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})

    def post(self, request):
        HasPermission("badms.storage.request_extension")().has_permission(request, self)
        serializer = SubmitStorageExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        dept_id = int(request.data.get("department_id", 1))

        try:
            req = submit_storage_extension(
                user_id=p.user_id,
                username=p.username,
                department_id=dept_id,
                **serializer.validated_data,
            )
            return Response(
                StorageExtensionRequestSerializer(req).data, status=status.HTTP_201_CREATED
            )
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class StorageExtensionDecisionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.storage.hod_decide")]

    def post(self, request, pk: int):
        serializer = HoDDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        dept_id = int(request.data.get("department_id", 1))

        try:
            req = decide_storage_extension_hod(
                request_id=pk,
                hod_id=p.user_id,
                hod_username=p.username,
                hod_department_id=dept_id,
                approve=serializer.validated_data["approve"],
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            )
            return Response(StorageExtensionRequestSerializer(req).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


# -- Restoration --
class RestorationListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.restoration.view")]

    def get(self, request):
        p = request.principal
        queue = request.query_params.get("queue")

        if queue == "admin" and "badms.restoration.approve" in p.permissions:
            restorations = list_sysadmin_restoration_queue()
        else:
            restorations = list_restorations(user_id=p.user_id)

        serializer = RestorationRequestSerializer(restorations, many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})

    def post(self, request):
        HasPermission("badms.restoration.request")().has_permission(request, self)
        serializer = SubmitRestorationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal

        try:
            restoration = submit_restoration_request(
                user_id=p.user_id,
                username=p.username,
                **serializer.validated_data,
            )
            return Response(
                RestorationRequestSerializer(restoration).data, status=status.HTTP_201_CREATED
            )
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class SysAdminRestorationDecisionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.restoration.approve")]

    def post(self, request, pk: int):
        serializer = SysAdminRestorationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal

        try:
            restoration = decide_sensitive_restoration_sysadmin(
                restoration_id=pk,
                sysadmin_id=p.user_id,
                sysadmin_username=p.username,
                approve=serializer.validated_data["approve"],
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            )
            return Response(RestorationRequestSerializer(restoration).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


class RestorationExecuteView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.restoration.execute")]

    def post(self, request, pk: int):
        p = request.principal

        try:
            restoration = execute_technical_restoration(
                restoration_id=pk,
                sysadmin_id=p.user_id,
                sysadmin_username=p.username,
            )
            return Response(RestorationRequestSerializer(restoration).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)


# -- Audit, Reports & Security --
class AuditLogListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.audit.view")]

    def get(self, request):
        logs = list_audit_logs()
        serializer = AuditLogSerializer(logs[:100], many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})


class DepartmentalReportView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.report.departmental")]

    def get(self, request):
        dept_id = int(request.query_params.get("department_id", 1))
        report = get_departmental_report(dept_id)
        return Response(report)


class ComplianceReportView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.report.compliance")]

    def get(self, request):
        report = get_backup_compliance_report()
        return Response(report)


class SecurityAuditReportView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.report.security")]

    def get(self, request):
        report = get_security_audit_report()
        return Response(report)


class SecurityPolicyListView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasPermission("badms.security.manage")]

    def get(self, request):
        policies = list_security_policies()
        serializer = SecurityPolicySerializer(policies, many=True)
        return Response({"results": serializer.data, "next": None, "previous": None})

    def patch(self, request):
        key = request.data.get("key")
        if not key:
            raise ValidationError("Policy key is required.")
        serializer = UpdateSecurityPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = request.principal
        role = p.active_role or (p.roles[0] if p.roles else "it_security_lead")

        try:
            policy = configure_security_policy(
                actor_id=p.user_id,
                actor_username=p.username,
                actor_role=role,
                key=key,
                **serializer.validated_data,
            )
            return Response(SecurityPolicySerializer(policy).data)
        except (BadmsDomainError, ValueError) as exc:
            _handle_domain_error(exc)
