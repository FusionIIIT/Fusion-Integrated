"""API views for Super Admin."""
from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.superadmin.api.serializers import (
    AuditEntrySerializer,
    RoleAssignmentSerializer,
    UserAccountSerializer,
)
from modules.superadmin.domain import policy
from modules.superadmin.domain.policy import DomainValidationError
from modules.superadmin.models import AuditEntry, RoleAssignment, UserAccount


def _log_audit(action: str, actor: str, target: str, reason: str = "") -> None:
    AuditEntry.objects.create(
        actor_username=actor or "superadmin",
        action=action,
        target_id=target,
        reason=reason,
    )


class UserAccountListCreateAPIView(APIView):
    permission_classes = [HasPermission("superadmin.user.manage")]

    def get(self, request: Request) -> Response:
        users = UserAccount.objects.all()
        return Response(UserAccountSerializer(users, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = UserAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            policy.validate_institute_email(email)
            user = serializer.save(status="ACTIVE")
            actor = getattr(request.user, "username", "superadmin")
            _log_audit("CREATE_USER", actor, user.institute_id)
            return Response(UserAccountSerializer(user).data, status=status.HTTP_201_CREATED)
        except DomainValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class UserDeactivateAPIView(APIView):
    permission_classes = [HasPermission("superadmin.user.manage")]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        user = get_object_or_404(UserAccount.objects.select_for_update(), user_id=user_id)
        user.status = "DEACTIVATED"
        user.deactivated_at = timezone.now()
        user.save(update_fields=["status", "deactivated_at"])
        RoleAssignment.objects.filter(user_id=user_id, status="ACTIVE").update(status="REVOKED")
        actor = getattr(request.user, "username", "superadmin")
        _log_audit("DEACTIVATE_USER", actor, user.institute_id)
        return Response(UserAccountSerializer(user).data)


class UserArchiveAPIView(APIView):
    permission_classes = [HasPermission("superadmin.user.manage")]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        user = get_object_or_404(UserAccount.objects.select_for_update(), user_id=user_id)
        now = timezone.now()
        reason = request.data.get("reason", "")
        try:
            policy.validate_archival_eligibility(user.status, user.deactivated_at, now)
            user.status = "ARCHIVED_REVERSIBLE"
            user.archived_at = now
            user.reversible_until = policy.calculate_reversible_window(now)
            user.save(update_fields=["status", "archived_at", "reversible_until"])
            actor = getattr(request.user, "username", "superadmin")
            _log_audit("ARCHIVE_USER", actor, user.institute_id, reason)
            return Response(UserAccountSerializer(user).data)
        except DomainValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class UserRestoreAPIView(APIView):
    permission_classes = [HasPermission("superadmin.user.manage")]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        user = get_object_or_404(UserAccount.objects.select_for_update(), user_id=user_id)
        try:
            policy.validate_archived_user_restoration(
                user.status, user.reversible_until, timezone.now()
            )
            user.status = "ACTIVE"
            user.archived_at = None
            user.reversible_until = None
            user.save(update_fields=["status", "archived_at", "reversible_until"])
            actor = getattr(request.user, "username", "superadmin")
            _log_audit("RESTORE_USER", actor, user.institute_id)
            return Response(UserAccountSerializer(user).data)
        except DomainValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RoleAssignmentListCreateAPIView(APIView):
    permission_classes = [HasPermission("superadmin.role.manage")]

    def get(self, request: Request) -> Response:
        roles = RoleAssignment.objects.all()
        return Response(RoleAssignmentSerializer(roles, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            policy.validate_role_dating(data["start_date"], data.get("end_date"))
            active_scopes = RoleAssignment.objects.filter(
                role_code=data["role_code"], status="ACTIVE"
            ).values_list("scope", flat=True)
            scope = data.get("scope", "INSTITUTE")
            policy.validate_singular_role_occupancy(data["role_code"], scope, list(active_scopes))

            role = serializer.save(status="ACTIVE")
            actor = getattr(request.user, "username", "superadmin")
            _log_audit("ASSIGN_ROLE", actor, f"{role.role_code}:{role.user_id}")
            return Response(RoleAssignmentSerializer(role).data, status=status.HTTP_201_CREATED)
        except DomainValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RoleRevokeAPIView(APIView):
    permission_classes = [HasPermission("superadmin.role.manage")]

    def post(self, request: Request, pk: int) -> Response:
        role = get_object_or_404(RoleAssignment, pk=pk)
        reason = request.data.get("reason", "")
        try:
            policy.validate_role_revocation(reason)
            role.status = "REVOKED"
            role.revocation_reason = reason
            role.save(update_fields=["status", "revocation_reason"])
            actor = getattr(request.user, "username", "superadmin")
            _log_audit("REVOKE_ROLE", actor, str(pk), reason)
            return Response(RoleAssignmentSerializer(role).data)
        except DomainValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class AuditEntryListAPIView(APIView):
    permission_classes = [HasPermission("superadmin.audit.view")]

    def get(self, request: Request) -> Response:
        audits = AuditEntry.objects.all()[:100]
        return Response(AuditEntrySerializer(audits, many=True).data)
