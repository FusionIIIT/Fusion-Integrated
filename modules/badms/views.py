"""Views for BADMS module."""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.domain import permissions as p
from modules.badms.models import (
    ArchivalRequest,
    BadmsAuditLog,
    BadmsNotification,
    BackupExecution,
    BackupSchedule,
    RestorationRequest,
    SpecialArchivalRecord,
    StorageExtensionRequest,
)
from modules.badms.serializers import (
    ArchivalClassifySerializer,
    ArchivalRequestSerializer,
    ArchivalRequestSubmitSerializer,
    BadmsAuditLogSerializer,
    BadmsNotificationSerializer,
    BackupExecutionSerializer,
    BackupScheduleSerializer,
    ConfigureEncryptionSerializer,
    HodReviewSerializer,
    RestorationDecisionSerializer,
    RestorationRequestSerializer,
    SpecialArchivalRecordSerializer,
    StorageExtensionDecisionSerializer,
    StorageExtensionRequestSerializer,
    SubmitRestorationSerializer,
    SubmitSpecialArchivalSerializer,
    SubmitStorageExtensionSerializer,
    TriggerBackupSerializer,
    UserStorageQuotaSerializer,
)
from modules.badms.services.archival import (
    ArchivalValidationError,
    classify_archival_request,
    hod_review_request,
    submit_archival_request,
)
from modules.badms.services.backup import (
    BackupServiceError,
    execute_backup,
    verify_backup_integrity,
)
from modules.badms.services.encryption import configure_archive_encryption
from modules.badms.services.restoration import (
    RestorationServiceError,
    create_restoration_request,
    process_restoration_decision,
)
from modules.badms.services.schedules import (
    ScheduleValidationError,
    create_schedule,
    execute_scheduled_backup,
    get_effective_schedule,
)
from modules.badms.services.department import (
    can_review_department_request,
    get_user_department,
)
from modules.badms.services.reports import get_retention_compliance_summary
from modules.badms.services.special_archival import (
    SpecialArchivalError,
    record_special_archival,
)
from modules.badms.services.storage import (
    QuotaExceededError,
    StorageExtensionError,
    get_or_create_user_quota,
    process_storage_extension_decision,
    submit_storage_extension,
)

MODULE = HasModuleGrant("badms")


class BadmsStatusView(APIView):
    """Health and status check for BADMS module."""
    permission_classes = [MODULE, HasPermission(p.ARCHIVE_VIEW_SELF)]

    def get(self, request):
        return Response({
            "status": "active",
            "module": "badms",
            "user_id": request.principal.user_id,
        })


class UserQuotaView(APIView):
    """Retrieve the authenticated user's storage quota and consumption."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        quota = get_or_create_user_quota(principal.user_id)
        serializer = UserStorageQuotaSerializer(quota)
        return Response(serializer.data)


class ArchivalRequestListCreateView(APIView):
    """List archival requests visible to the caller, or submit a new archival request."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal

        if principal.has_permission(p.ARCHIVE_VIEW):
            # Global view (SysAdmin, Super Admin, Security)
            qs = ArchivalRequest.objects.all()
            dept = request.query_params.get("department")
            if dept:
                qs = qs.filter(department__iexact=dept)
            status_param = request.query_params.get("status")
            if status_param:
                qs = qs.filter(status=status_param)
        elif principal.has_permission(p.ARCHIVE_REVIEW):
            # HoD view: scoped strictly to HoD's department
            hod_dept = get_user_department(principal.user_id)
            if not hod_dept:
                qs = ArchivalRequest.objects.none()
            else:
                qs = ArchivalRequest.objects.filter(department__iexact=hod_dept)
                status_param = request.query_params.get("status")
                if status_param:
                    qs = qs.filter(status=status_param)
        elif principal.has_permission(p.ARCHIVE_VIEW_SELF):
            # Self view: caller's own submissions
            qs = ArchivalRequest.objects.filter(user_id=principal.user_id)
        else:
            raise PermissionDenied("You do not have permission to view archival requests.")

        serializer = ArchivalRequestSerializer(qs.order_by("-created_at"), many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        principal = request.principal
        if not principal.has_permission(p.ARCHIVE_CREATE):
            raise PermissionDenied("You do not have permission to submit archival requests.")

        serializer = ArchivalRequestSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            archive_request = submit_archival_request(
                user_id=principal.user_id,
                user_role=principal.active_role or "",
                payload=serializer.validated_data,
            )
        except QuotaExceededError as err:
            return Response(
                {"detail": str(err), "code": "quota_exceeded"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ArchivalValidationError as err:
            return Response(
                {"detail": str(err), "code": "validation_error"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output = ArchivalRequestSerializer(archive_request)
        return Response(output.data, status=status.HTTP_201_CREATED)


class ArchivalRequestDetailView(APIView):
    """Retrieve details of a single archival request with department/ownership scoping."""
    permission_classes = [MODULE]

    def get_object(self, pk: int, principal):
        try:
            obj = ArchivalRequest.objects.get(pk=pk)
        except ArchivalRequest.DoesNotExist:
            raise NotFound(f"Archival request #{pk} not found.")

        # Check authorization
        if principal.has_permission(p.ARCHIVE_VIEW):
            return obj
        if principal.has_permission(p.ARCHIVE_REVIEW) and can_review_department_request(
            principal, obj.department
        ):
            return obj
        if obj.user_id == principal.user_id and principal.has_permission(p.ARCHIVE_VIEW_SELF):
            return obj

        raise NotFound(f"Archival request #{pk} not found.")

    def get(self, request, pk: int):
        obj = self.get_object(pk, request.principal)
        serializer = ArchivalRequestSerializer(obj)
        return Response(serializer.data)


class UserNotificationsView(APIView):
    """List notifications for the authenticated user."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        qs = BadmsNotification.objects.filter(
            user_id=principal.user_id
        ).order_by("-created_at")[:50]
        serializer = BadmsNotificationSerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})


class ArchivalHodDecisionView(APIView):
    """Process HoD approval or rejection of an archival request with department scoping."""
    permission_classes = [MODULE, HasPermission(p.ARCHIVE_REVIEW)]

    def post(self, request, pk: int):
        principal = request.principal
        try:
            archive = ArchivalRequest.objects.get(pk=pk)
        except ArchivalRequest.DoesNotExist:
            raise NotFound(f"Archival request #{pk} not found.")

        if not can_review_department_request(principal, archive.department):
            raise PermissionDenied(
                f"You are only authorized to review requests within your department ({archive.department})."
            )

        serializer = HodReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = hod_review_request(
                archive_id=pk,
                reviewer_id=principal.user_id,
                reviewer_role=principal.active_role or "HOD",
                decision=serializer.validated_data["decision"],
                comments=serializer.validated_data["comments"],
            )
        except ArchivalValidationError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ArchivalRequestSerializer(updated).data, status=status.HTTP_200_OK)


class ArchivalClassifyView(APIView):
    """SysAdmin assigns authoritative classification to a HoD-approved archive request."""
    permission_classes = [MODULE, HasPermission(p.ARCHIVE_CLASSIFY)]

    def post(self, request, pk: int):
        principal = request.principal
        try:
            archive = ArchivalRequest.objects.get(pk=pk)
        except ArchivalRequest.DoesNotExist:
            raise NotFound(f"Archival request #{pk} not found.")

        serializer = ArchivalClassifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = classify_archival_request(
                archive_id=pk,
                sysadmin_id=principal.user_id,
                sysadmin_role=principal.active_role or "sysadmin",
                classification=serializer.validated_data["classification"],
                comments=serializer.validated_data["comments"],
            )
        except ArchivalValidationError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ArchivalRequestSerializer(updated).data, status=status.HTTP_200_OK)


class ArchivalConfigureEncryptionView(APIView):
    """IT Security configures encryption (AES-256) for sensitive archival requests."""
    permission_classes = [MODULE, HasPermission(p.ARCHIVE_ENCRYPT)]

    def post(self, request, pk: int):
        principal = request.principal
        try:
            archive = ArchivalRequest.objects.get(pk=pk)
        except ArchivalRequest.DoesNotExist:
            raise NotFound(f"Archival request #{pk} not found.")

        serializer = ConfigureEncryptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = configure_archive_encryption(
                archive_id=pk,
                security_user_id=principal.user_id,
                security_role=principal.active_role or "it_security",
                algorithm=serializer.validated_data["algorithm"],
                key_id=serializer.validated_data["key_id"],
            )
        except ArchivalValidationError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ArchivalRequestSerializer(updated).data, status=status.HTTP_200_OK)


class BackupExecutionListCreateView(APIView):
    """List backup history or trigger a manual backup execution."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        if not (
            principal.has_permission(p.BACKUP_VIEW)
            or principal.has_permission(p.BACKUP_MANAGE)
        ):
            raise PermissionDenied("You do not have permission to view backup history.")

        qs = BackupExecution.objects.all()

        # Regular backup.view callers can only see local backups; backup.manage sees all
        if not principal.has_permission(p.BACKUP_MANAGE):
            qs = qs.filter(scope="local")

        scope_param = request.query_params.get("scope")
        if scope_param:
            qs = qs.filter(scope=scope_param)

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        serializer = BackupExecutionSerializer(qs.order_by("-started_at")[:100], many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        principal = request.principal
        if not (
            principal.has_permission(p.BACKUP_CREATE)
            or principal.has_permission(p.BACKUP_MANAGE)
        ):
            raise PermissionDenied("You do not have permission to trigger backups.")

        serializer = TriggerBackupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        requested_scope = data.get("scope", "local")

        # Global backups require policy.manage or Super Admin privileges
        if requested_scope == "global" and not (
            principal.has_permission(p.POLICY_MANAGE)
            or (principal.active_role or "").lower() in ("super admin", "admin")
        ):
            raise PermissionDenied(
                "Managing global backups requires Super Admin privileges (badms.policy.manage)."
            )

        backup = execute_backup(
            initiated_by_user_id=principal.user_id,
            initiated_by_role=principal.active_role or "sysadmin",
            backup_type=data.get("backup_type", "full"),
            scope=requested_scope,
            target_dataset=data.get("target_dataset", "all"),
            simulate_unreachable=data.get("simulate_unreachable", False),
            simulate_failure=data.get("simulate_failure", False),
        )

        status_code = (
            status.HTTP_201_CREATED if backup.status == "completed" else status.HTTP_200_OK
        )
        return Response(BackupExecutionSerializer(backup).data, status=status_code)


class BackupExecutionDetailView(APIView):
    """Retrieve details of a specific backup execution."""
    permission_classes = [MODULE]

    def get(self, request, pk: int):
        principal = request.principal
        if not (
            principal.has_permission(p.BACKUP_VIEW)
            or principal.has_permission(p.BACKUP_MANAGE)
        ):
            raise PermissionDenied("You do not have permission to view backup details.")

        try:
            backup = BackupExecution.objects.get(pk=pk)
        except BackupExecution.DoesNotExist:
            raise NotFound(f"Backup #{pk} not found.")

        if not principal.has_permission(p.BACKUP_MANAGE) and backup.scope != "local":
            raise NotFound(f"Backup #{pk} not found.")

        return Response(BackupExecutionSerializer(backup).data)


class BackupIntegrityVerifyView(APIView):
    """Verify integrity of a completed backup."""
    permission_classes = [MODULE, HasPermission(p.BACKUP_MANAGE)]

    def post(self, request, pk: int):
        try:
            is_valid = verify_backup_integrity(
                backup_id=pk,
                user_id=request.principal.user_id,
                role=request.principal.active_role or "sysadmin",
            )
        except BackupServiceError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        backup = BackupExecution.objects.get(pk=pk)
        return Response({
            "integrity_verified": is_valid,
            "backup": BackupExecutionSerializer(backup).data,
        })


class BackupScheduleListCreateView(APIView):
    """List configured backup schedules or create a new schedule with scope authorization."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        if not (
            principal.has_permission(p.BACKUP_VIEW)
            or principal.has_permission(p.BACKUP_MANAGE)
            or principal.has_permission(p.POLICY_MANAGE)
        ):
            raise PermissionDenied("You do not have permission to view backup schedules.")

        qs = BackupSchedule.objects.all()
        schedule_type = request.query_params.get("schedule_type")
        if schedule_type:
            qs = qs.filter(schedule_type=schedule_type)
        dataset = request.query_params.get("target_dataset")
        if dataset:
            qs = qs.filter(target_dataset=dataset)

        serializer = BackupScheduleSerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        principal = request.principal
        data = request.data
        req_type = (data.get("schedule_type") or "local").lower()

        # Authorization: Global schedules require Super Admin / POLICY_MANAGE
        if req_type == "global":
            if not (
                principal.has_permission(p.POLICY_MANAGE)
                or (principal.active_role or "").lower() in ("super admin", "admin")
            ):
                raise PermissionDenied(
                    "Only Super Admin can manage global schedules and default policies (badms.policy.manage)."
                )
        else:
            if not (
                principal.has_permission(p.BACKUP_MANAGE)
                or principal.has_permission(p.POLICY_MANAGE)
                or (principal.active_role or "").lower() in ("sysadmin", "super admin")
            ):
                raise PermissionDenied("You do not have permission to configure backup schedules.")

        try:
            schedule = create_schedule(
                user_id=principal.user_id,
                user_role=principal.active_role or "sysadmin",
                payload=data,
            )
        except ScheduleValidationError as err:
            return Response(
                {"detail": str(err), "code": "invalid_configuration"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(BackupScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED)


class BackupScheduleDetailView(APIView):
    """Retrieve, update, or delete a specific backup schedule."""
    permission_classes = [MODULE]

    def get_object(self, pk: int):
        try:
            return BackupSchedule.objects.get(pk=pk)
        except BackupSchedule.DoesNotExist:
            raise NotFound(f"Schedule #{pk} not found.")

    def get(self, request, pk: int):
        schedule = self.get_object(pk)
        return Response(BackupScheduleSerializer(schedule).data)

    def patch(self, request, pk: int):
        schedule = self.get_object(pk)
        principal = request.principal

        if schedule.schedule_type == "global" and not (
            principal.has_permission(p.POLICY_MANAGE)
            or (principal.active_role or "").lower() in ("super admin", "admin")
        ):
            raise PermissionDenied("Only Super Admin can mutate global schedules.")

        for key, val in request.data.items():
            if hasattr(schedule, key) and key not in ("id", "created_by_user_id", "created_at"):
                setattr(schedule, key, val)
        schedule.save()
        return Response(BackupScheduleSerializer(schedule).data)

    def delete(self, request, pk: int):
        schedule = self.get_object(pk)
        principal = request.principal

        if schedule.schedule_type == "global" and not (
            principal.has_permission(p.POLICY_MANAGE)
            or (principal.active_role or "").lower() in ("super admin", "admin")
        ):
            raise PermissionDenied("Only Super Admin can delete global schedules.")

        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EffectiveScheduleView(APIView):
    """Resolve and return the current effective backup schedule applying precedence rules."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        if not (
            principal.has_permission(p.BACKUP_VIEW)
            or principal.has_permission(p.BACKUP_MANAGE)
            or principal.has_permission(p.POLICY_MANAGE)
        ):
            raise PermissionDenied("You do not have permission to view effective schedules.")

        dataset = request.query_params.get("dataset", "all")
        effective = get_effective_schedule(dataset)

        return Response({
            "target_dataset": dataset,
            "has_effective_schedule": effective is not None,
            "effective_schedule": BackupScheduleSerializer(effective).data if effective else None,
            "precedence_rule": (
                "local_override"
                if (effective and effective.schedule_type == "local")
                else "global_default"
                if effective
                else "none"
            ),
        })


class RunScheduledBackupView(APIView):
    """Trigger immediate execution of a configured schedule."""
    permission_classes = [MODULE]

    def post(self, request, pk: int):
        principal = request.principal
        if not (
            principal.has_permission(p.BACKUP_MANAGE)
            or principal.has_permission(p.POLICY_MANAGE)
        ):
            raise PermissionDenied("You do not have permission to execute scheduled backups.")

        simulate_unreachable = request.data.get("simulate_unreachable", False)
        try:
            execution = execute_scheduled_backup(
                pk,
                user_id=principal.user_id,
                simulate_unreachable=simulate_unreachable,
            )
        except ScheduleValidationError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BackupExecutionSerializer(execution).data, status=status.HTTP_200_OK)


class RestorationRequestListCreateView(APIView):
    """List restoration requests or submit a new restoration request."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        if not (
            principal.has_permission(p.RESTORATION_VIEW_SELF)
            or principal.has_permission(p.RESTORATION_VIEW)
        ):
            raise PermissionDenied("You do not have permission to view restoration requests.")

        if principal.has_permission(p.RESTORATION_VIEW):
            qs = RestorationRequest.objects.all()
        else:
            qs = RestorationRequest.objects.filter(requester_user_id=principal.user_id)

        serializer = RestorationRequestSerializer(qs.order_by("-created_at")[:100], many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        principal = request.principal
        if not principal.has_permission(p.RESTORATION_CREATE):
            raise PermissionDenied("You do not have permission to submit restoration requests.")

        serializer = SubmitRestorationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            restoration = create_restoration_request(
                user_id=principal.user_id,
                user_role=principal.active_role or "student",
                payload=serializer.validated_data,
            )
        except RestorationServiceError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            RestorationRequestSerializer(restoration).data,
            status=status.HTTP_201_CREATED,
        )


class RestorationRequestDetailView(APIView):
    """Retrieve details of a restoration request."""
    permission_classes = [MODULE]

    def get(self, request, pk: int):
        principal = request.principal
        try:
            obj = RestorationRequest.objects.get(pk=pk)
        except RestorationRequest.DoesNotExist:
            raise NotFound(f"Restoration request #{pk} not found.")

        if not principal.has_permission(p.RESTORATION_VIEW) and obj.requester_user_id != principal.user_id:
            raise NotFound(f"Restoration request #{pk} not found.")

        return Response(RestorationRequestSerializer(obj).data)


class RestorationApprovalView(APIView):
    """SysAdmin decision (approve or reject) for a sensitive restoration request."""
    permission_classes = [MODULE, HasPermission(p.RESTORATION_APPROVE)]

    def post(self, request, pk: int):
        principal = request.principal
        serializer = RestorationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = process_restoration_decision(
                restoration_id=pk,
                sysadmin_user_id=principal.user_id,
                sysadmin_role=principal.active_role or "sysadmin",
                decision=serializer.validated_data["decision"],
                comments=serializer.validated_data["comments"],
            )
        except RestorationServiceError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RestorationRequestSerializer(updated).data, status=status.HTTP_200_OK)


class StorageExtensionListCreateView(APIView):
    """List storage extension requests or submit a new storage extension request."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal

        if principal.has_permission(p.STORAGE_VIEW):
            qs = StorageExtensionRequest.objects.all()
            dept = request.query_params.get("department")
            if dept:
                qs = qs.filter(department__iexact=dept)
            status_param = request.query_params.get("status")
            if status_param:
                qs = qs.filter(status=status_param)
        elif principal.has_permission(p.STORAGE_REVIEW):
            # HoD view: scoped strictly to HoD's department
            hod_dept = get_user_department(principal.user_id)
            if not hod_dept:
                qs = StorageExtensionRequest.objects.none()
            else:
                qs = StorageExtensionRequest.objects.filter(department__iexact=hod_dept)
                status_param = request.query_params.get("status")
                if status_param:
                    qs = qs.filter(status=status_param)
        elif principal.has_permission(p.STORAGE_VIEW_SELF):
            qs = StorageExtensionRequest.objects.filter(user_id=principal.user_id)
        else:
            raise PermissionDenied("You do not have permission to view storage extension requests.")

        serializer = StorageExtensionRequestSerializer(qs.order_by("-created_at"), many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    def post(self, request):
        principal = request.principal
        if not principal.has_permission(p.STORAGE_CREATE):
            raise PermissionDenied("You do not have permission to request storage extensions.")

        serializer = SubmitStorageExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            ext = submit_storage_extension(
                user_id=principal.user_id,
                user_role=principal.active_role or "",
                requested_bytes=serializer.validated_data["requested_bytes"],
                reason=serializer.validated_data["reason"],
            )
        except StorageExtensionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StorageExtensionRequestSerializer(ext).data, status=status.HTTP_201_CREATED)


class StorageExtensionDetailView(APIView):
    """Retrieve details of a single storage extension request."""
    permission_classes = [MODULE]

    def get(self, request, pk: int):
        principal = request.principal
        try:
            obj = StorageExtensionRequest.objects.get(pk=pk)
        except StorageExtensionRequest.DoesNotExist:
            raise NotFound(f"Storage extension request #{pk} not found.")

        # Check authorization
        if principal.has_permission(p.STORAGE_VIEW):
            return Response(StorageExtensionRequestSerializer(obj).data)
        if principal.has_permission(p.STORAGE_REVIEW) and can_review_department_request(
            principal, obj.department
        ):
            return Response(StorageExtensionRequestSerializer(obj).data)
        if obj.user_id == principal.user_id and principal.has_permission(p.STORAGE_VIEW_SELF):
            return Response(StorageExtensionRequestSerializer(obj).data)

        raise NotFound(f"Storage extension request #{pk} not found.")


class StorageExtensionDecisionView(APIView):
    """HoD decision (approve or reject) for a storage extension request."""
    permission_classes = [MODULE, HasPermission(p.STORAGE_REVIEW)]

    def post(self, request, pk: int):
        principal = request.principal
        try:
            ext = StorageExtensionRequest.objects.get(pk=pk)
        except StorageExtensionRequest.DoesNotExist:
            raise NotFound(f"Storage extension request #{pk} not found.")

        if not can_review_department_request(principal, ext.department):
            raise PermissionDenied(
                f"You are only authorized to review storage extension requests within your department ({ext.department})."
            )

        serializer = StorageExtensionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = process_storage_extension_decision(
                request_id=pk,
                reviewer_id=principal.user_id,
                reviewer_role=principal.active_role or "HOD",
                decision=serializer.validated_data["decision"],
                comments=serializer.validated_data["comments"],
            )
        except StorageExtensionError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(StorageExtensionRequestSerializer(updated).data, status=status.HTTP_200_OK)


class SpecialArchivalListCreateView(APIView):
    """List special offline archival records or execute special offline archival."""
    permission_classes = [MODULE]

    def get(self, request):
        principal = request.principal
        if not (principal.has_permission(p.ARCHIVE_SPECIAL) or principal.has_permission(p.AUDIT_VIEW)):
            raise PermissionDenied("You do not have permission to view special archival records.")

        records = SpecialArchivalRecord.objects.all().order_by("-completed_at")
        serializer = SpecialArchivalRecordSerializer(records, many=True)
        return Response({"count": records.count(), "results": serializer.data})

    def post(self, request):
        principal = request.principal
        if not principal.has_permission(p.ARCHIVE_SPECIAL):
            raise PermissionDenied("Only Super Admin can perform special archival in the system.")

        serializer = SubmitSpecialArchivalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            record = record_special_archival(
                performer_id=principal.user_id,
                performer_role=principal.active_role or "Super Admin",
                payload=serializer.validated_data,
            )
        except SpecialArchivalError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SpecialArchivalRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class BadmsAuditLogListView(APIView):
    """List immutable audit events."""
    permission_classes = [MODULE, HasPermission(p.AUDIT_VIEW)]

    def get(self, request):
        qs = BadmsAuditLog.objects.all().order_by("-created_at")

        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action__icontains=action)

        target_type = request.query_params.get("target_type")
        if target_type:
            qs = qs.filter(target_type=target_type)

        outcome = request.query_params.get("outcome")
        if outcome:
            qs = qs.filter(outcome=outcome)

        actor_user_id = request.query_params.get("actor_user_id")
        if actor_user_id:
            qs = qs.filter(actor_user_id=actor_user_id)

        limit = min(int(request.query_params.get("limit", 50)), 200)
        serializer = BadmsAuditLogSerializer(qs[:limit], many=True)
        return Response({"count": qs.count(), "results": serializer.data})


class RetentionComplianceReportView(APIView):
    """Operational metrics and retention compliance summary."""
    permission_classes = [MODULE, HasPermission(p.REPORT_VIEW)]

    def get(self, request):
        summary = get_retention_compliance_summary()
        return Response(summary, status=status.HTTP_200_OK)
