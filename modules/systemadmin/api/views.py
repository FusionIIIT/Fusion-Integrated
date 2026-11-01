"""HTTP API Views for System Admin Module."""
from typing import Tuple
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.models.role_mgmt import RoleDefinition, RoleAssignment
from modules.systemadmin.models.archival import ArchivedUser, ArchivedHistoricalData, PermanentPurgeRequest
from modules.systemadmin.models.config import SystemAdminConfig

from modules.systemadmin.selectors import (
    get_user_by_id,
    list_users,
    get_user_status_history,
    list_roles,
    get_role_detail,
    list_role_assignments,
    get_assignment_history,
    list_archived_users,
    list_archived_historical_data,
    list_purge_requests,
    list_audit_logs,
    list_session_logs,
    list_security_alerts,
    list_notifications,
    get_audit_metrics_summary,
    get_dashboard_metrics,
)
from modules.systemadmin.services.user_service import UserService, UserManagementError
from modules.systemadmin.services.role_service import RoleService, RoleManagementError
from modules.systemadmin.services.archival_service import ArchivalService, ArchivalError
from modules.systemadmin.services.config_service import ConfigService, ConfigurationError
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.api import serializers as s

MODULE = HasModuleGrant("systemadmin")


def _get_actor(request) -> Tuple[str, str]:
    """Helper to extract username and role from request principal or authenticated user."""
    principal = getattr(request, "principal", None)
    if principal:
        username = getattr(principal, "username", None) or str(getattr(principal, "user_id", "admin"))
        role = "IT Head" if principal.has_permission("systemadmin.purge.authorize") else "Super Admin"
        return username, role

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user.username, "Super Admin"

    return "system_admin", "Super Admin"


def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


# =========================================================================
# Dashboard
# =========================================================================

class DashboardOverviewView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.dashboard.view")]

    def get(self, request):
        data = get_dashboard_metrics()
        return Response(data)


# =========================================================================
# User Management Views
# =========================================================================

class UserListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.user.view")]

    def get(self, request):
        user_type = request.query_params.get("user_type")
        status_param = request.query_params.get("status")
        department = request.query_params.get("department")
        programme = request.query_params.get("programme")
        batch_year = request.query_params.get("batch_year")
        search = request.query_params.get("search")

        qs = list_users(
            search=search,
            user_type=user_type,
            status=status_param,
            department=department,
            programme=programme,
            batch_year=int(batch_year) if batch_year else None,
        )
        serializer = s.BasicUserProfileSerializer(qs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class UserCreateView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.user.create")]

    def post(self, request):
        serializer = s.UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            profile = UserService.create_basic_user(
                institute_id=data["institute_id"],
                user_type=data["user_type"],
                full_name=data["full_name"],
                institute_email=data["institute_email"],
                date_of_joining=data["date_of_joining"],
                contact_number=data.get("contact_number", ""),
                department=data.get("department", ""),
                programme=data.get("programme", ""),
                discipline=data.get("discipline", ""),
                batch_year=data.get("batch_year"),
                employee_id=data.get("employee_id", ""),
                expected_completion_date=data.get("expected_completion_date"),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.BasicUserProfileSerializer(profile).data, status=status.HTTP_201_CREATED)
        except UserManagementError as exc:
            raise BadRequestError(str(exc))


class UserDetailView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.user.view")]

    def get(self, request, user_id):
        profile = get_user_by_id(user_id)
        if not profile:
            raise NotFoundError("User not found.")
        serializer = s.BasicUserProfileDetailSerializer(profile)
        return Response(serializer.data)

    def patch(self, request, user_id):
        principal = getattr(request, "principal", None)
        if principal and not principal.has_permission("systemadmin.user.edit"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        serializer = s.UserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            updated = UserService.update_user_profile(
                user_id=user_id,
                updates=serializer.validated_data,
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.BasicUserProfileSerializer(updated).data)
        except UserManagementError as exc:
            raise BadRequestError(str(exc))


class UserStatusView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.user.status")]

    def post(self, request, user_id):
        serializer = s.UserStatusChangeSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        action = serializer.validated_data["action"]
        reason = serializer.validated_data["reason"]
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            if action == "deactivate":
                profile = UserService.deactivate_user(
                    user_id=user_id,
                    reason=reason,
                    actor_username=actor,
                    ip_address=ip,
                )
            else:
                profile = UserService.reactivate_user(
                    user_id=user_id,
                    reason=reason,
                    actor_username=actor,
                    ip_address=ip,
                )
            return Response(s.BasicUserProfileSerializer(profile).data)
        except UserManagementError as exc:
            raise BadRequestError(str(exc))


class UserBulkCreateView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.user.bulk")]

    def post(self, request):
        serializer = s.BulkUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        records = serializer.validated_data["users"]
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            summary = UserService.bulk_create_users(
                user_records=records,
                actor_username=actor,
                ip_address=ip,
            )
            return Response(summary, status=status.HTTP_201_CREATED)
        except UserManagementError as exc:
            raise BadRequestError(str(exc))


class UserBulkStatusView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.user.bulk")]

    def post(self, request):
        serializer = s.BulkUserStatusSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            summary = UserService.bulk_status_update(
                user_ids=data["user_ids"],
                action=data["action"],
                reason=data["reason"],
                actor_username=actor,
                ip_address=ip,
            )
            return Response(summary)
        except UserManagementError as exc:
            raise BadRequestError(str(exc))


# =========================================================================
# Role Management Views
# =========================================================================

class RoleListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.view")]

    def get(self, request):
        roles_data = list_roles()
        return Response({"results": roles_data, "count": len(roles_data)})


class RoleDetailView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.view")]

    def get(self, request, role_id):
        role_data = get_role_detail(role_id)
        if not role_data:
            raise NotFoundError("Role definition not found.")
        return Response(role_data)


class RoleAssignmentListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.view")]

    def get(self, request):
        role_id = request.query_params.get("role_id")
        user_id = request.query_params.get("user_id")
        status_param = request.query_params.get("status")

        qs = list_role_assignments(
            role_id=int(role_id) if role_id else None,
            user_id=int(user_id) if user_id else None,
            status=status_param,
        )
        serializer = s.RoleAssignmentSerializer(qs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class RoleAssignView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.assign")]

    def post(self, request):
        serializer = s.RoleAssignmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            assignment = RoleService.assign_role(
                role_code=data["role_code"],
                user_id=data["user_id"],
                start_date=data["start_date"],
                end_date=data.get("end_date"),
                scope=data.get("scope", ""),
                reason=data.get("reason", ""),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.RoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)
        except RoleManagementError as exc:
            raise ConflictError(str(exc))


class RoleReassignView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.reassign")]

    def post(self, request, assignment_id):
        serializer = s.RoleReassignSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            new_assignment = RoleService.reassign_role(
                current_assignment_id=assignment_id,
                new_user_id=data["new_user_id"],
                effective_date=data["effective_date"],
                reason=data["reason"],
                pending_task_disposition=data.get("pending_task_disposition", "transfer"),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.RoleAssignmentSerializer(new_assignment).data)
        except RoleManagementError as exc:
            raise ConflictError(str(exc))


class RoleRevokeView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.revoke")]

    def post(self, request, assignment_id):
        serializer = s.RoleRevokeSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            assignment = RoleService.revoke_role(
                assignment_id=assignment_id,
                reason=data["reason"],
                is_emergency=data.get("is_emergency", False),
                effective_date=data.get("effective_date"),
                pending_task_disposition=data.get("pending_task_disposition", "close"),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.RoleAssignmentSerializer(assignment).data)
        except RoleManagementError as exc:
            raise BadRequestError(str(exc))


class RoleExtendView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.role.extend")]

    def post(self, request, assignment_id):
        serializer = s.RoleExtendSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            assignment = RoleService.extend_role_validity(
                assignment_id=assignment_id,
                new_end_date=data["new_end_date"],
                extension_approval_ref=data["extension_approval_ref"],
                reason=data["reason"],
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.RoleAssignmentSerializer(assignment).data)
        except RoleManagementError as exc:
            raise BadRequestError(str(exc))


# =========================================================================
# Archival & Purge Views
# =========================================================================

class ArchivedUserListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.view")]

    def get(self, request):
        status_param = request.query_params.get("status")
        search = request.query_params.get("search")
        qs = list_archived_users(status=status_param, search=search)
        serializer = s.ArchivedUserSerializer(qs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class ArchiveUserView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.execute")]

    def post(self, request):
        serializer = s.ArchiveUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            archived = ArchivalService.archive_user(
                user_id=data["user_id"],
                reason=data["reason"],
                retention_option=data.get("retention_option", "standard_institutional"),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.ArchivedUserSerializer(archived).data, status=status.HTTP_201_CREATED)
        except ArchivalError as exc:
            raise BadRequestError(str(exc))


class RestoreArchivedUserView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.restore")]

    def post(self, request, user_id):
        serializer = s.RestoreUserSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        ref = serializer.validated_data["restoration_authorization_ref"]
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            user = ArchivalService.restore_archived_user(
                user_id=user_id,
                restoration_authorization_ref=ref,
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.BasicUserProfileSerializer(user).data)
        except ArchivalError as exc:
            raise BadRequestError(str(exc))


class ArchivedHistoricalDataListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.view")]

    def get(self, request):
        category = request.query_params.get("category")
        status_param = request.query_params.get("status")
        qs = list_archived_historical_data(category=category, status=status_param)
        serializer = s.ArchivedHistoricalDataSerializer(qs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class ArchiveHistoricalDataView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.execute")]

    def post(self, request):
        serializer = s.ArchiveHistoricalDataCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            record = ArchivalService.archive_historical_data(
                category=data["category"],
                date_range_start=data["date_range_start"],
                date_range_end=data["date_range_end"],
                record_count=data["record_count"],
                storage_size_kb=data["storage_size_kb"],
                backup_reference=data["backup_reference"],
                retention_years=data.get("retention_years", 7),
                summary_metadata=data.get("summary_metadata", {}),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.ArchivedHistoricalDataSerializer(record).data, status=status.HTTP_201_CREATED)
        except ArchivalError as exc:
            raise BadRequestError(str(exc))


class RestoreHistoricalDataView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.restore")]

    def post(self, request, data_id):
        serializer = s.RestoreHistoricalDataSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        ref = serializer.validated_data["approval_ref"]
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            record = ArchivalService.restore_historical_data(
                data_id=data_id,
                approval_ref=ref,
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.ArchivedHistoricalDataSerializer(record).data)
        except ArchivalError as exc:
            raise BadRequestError(str(exc))


class PurgeRequestListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.archive.view")]

    def get(self, request):
        status_param = request.query_params.get("status")
        target_type = request.query_params.get("target_type")
        qs = list_purge_requests(status=status_param, target_type=target_type)
        serializer = s.PermanentPurgeRequestSerializer(qs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class PurgeRequestCreateView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.purge.request")]

    def post(self, request):
        serializer = s.PurgeRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            purge_req = ArchivalService.request_permanent_purge(
                target_type=data["target_type"],
                target_id=data["target_id"],
                reason=data["reason"],
                regulatory_authorization_ref=data["regulatory_authorization_ref"],
                requester_username=actor,
                ip_address=ip,
            )
            return Response(s.PermanentPurgeRequestSerializer(purge_req).data, status=status.HTTP_201_CREATED)
        except ArchivalError as exc:
            raise BadRequestError(str(exc))


class PurgeAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.purge.authorize")]

    def post(self, request, request_id):
        serializer = s.PurgeAuthorizeSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            result = ArchivalService.authorize_permanent_purge(
                purge_request_id=request_id,
                it_head_username=actor,
                decision=data["decision"],
                comments=data["comments"],
                ip_address=ip,
            )
            return Response(s.PermanentPurgeRequestSerializer(result).data)
        except ArchivalError as exc:
            raise BadRequestError(str(exc))


# =========================================================================
# Audit Logs, Reports & Security
# =========================================================================

class AuditLogListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.audit.view")]

    def get(self, request):
        actor_username = request.query_params.get("actor_username")
        action = request.query_params.get("action")
        result_param = request.query_params.get("result")
        target_user = request.query_params.get("target_user")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        search = request.query_params.get("search")

        qs = list_audit_logs(
            actor_username=actor_username,
            action=action,
            result=result_param,
            target_user=target_user,
            start_date=start_date,
            end_date=end_date,
            search=search,
        )
        serializer = s.SystemAdminAuditLogSerializer(qs[:200], many=True)
        return Response({"results": serializer.data, "count": qs.count()})


class AuditReportView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.audit.report")]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        summary = get_audit_metrics_summary(start_date=start_date, end_date=end_date)
        return Response(summary)


class SessionListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.audit.view")]

    def get(self, request):
        username = request.query_params.get("username")
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1")
        qs = list_session_logs(username=username, is_active=is_active)
        serializer = s.SessionLogSerializer(qs[:100], many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class SecurityAlertListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.audit.view")]

    def get(self, request):
        severity = request.query_params.get("severity")
        is_resolved_param = request.query_params.get("is_resolved")
        is_resolved = None
        if is_resolved_param is not None:
            is_resolved = is_resolved_param.lower() in ("true", "1")
        qs = list_security_alerts(severity=severity, is_resolved=is_resolved)
        serializer = s.SecurityAlertSerializer(qs, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


class NotificationListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.dashboard.view")]

    def get(self, request):
        actor, _ = _get_actor(request)
        is_read_param = request.query_params.get("is_read")
        is_read = None
        if is_read_param is not None:
            is_read = is_read_param.lower() in ("true", "1")
        category = request.query_params.get("category")
        qs = list_notifications(recipient_username=actor, is_read=is_read, category=category)
        serializer = s.AdminNotificationSerializer(qs[:50], many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})


# =========================================================================
# Configuration Views
# =========================================================================

class ConfigListView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.config.manage")]

    def get(self, request):
        configs = ConfigService.get_all_configurations()
        return Response({"results": configs, "count": len(configs)})


class ConfigUpdateView(APIView):
    permission_classes = [MODULE, HasPermission("systemadmin.config.manage")]

    def patch(self, request, key):
        serializer = s.ConfigUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError("Validation failed.", details=serializer.errors)

        data = serializer.validated_data
        actor, _ = _get_actor(request)
        ip = _get_client_ip(request)

        try:
            cfg = ConfigService.update_configuration(
                key=key,
                value=data["value"],
                confirmation_token=data.get("confirmation_token", ""),
                actor_username=actor,
                ip_address=ip,
            )
            return Response(s.SystemAdminConfigSerializer(cfg).data)
        except ConfigurationError as exc:
            raise BadRequestError(str(exc))
