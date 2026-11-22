from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from core.api.pagination import CursorPagination
from core.files.validators import sanitise_filename
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.api.serializers import (
    ArchiveCreateSerializer,
    ArchiveDecisionSerializer,
    ArchivePageSerializer,
    ArchiveReadSerializer,
    AuditEventSerializer,
    AuditPageSerializer,
    BackupRunPageSerializer,
    BackupRunSerializer,
    BackupScheduleListSerializer,
    BackupScheduleSerializer,
    ClassificationSerializer,
    MyStorageThresholdSerializer,
    RestoreCreateSerializer,
    RestorePageSerializer,
    RestoreReadSerializer,
    SecurityPolicySerializer,
    SpecialArchiveReadSerializer,
    SpecialArchiveSerializer,
    StorageExtensionCreateSerializer,
    StorageExtensionDecisionSerializer,
    StorageExtensionPageSerializer,
    StorageExtensionReadSerializer,
    StorageThresholdSerializer,
)
from modules.badms.models import (
    ArchiveRequest,
    AuditEvent,
    BackupRun,
    BackupSchedule,
    SecurityPolicy,
    StorageExtensionRequest,
    StorageThreshold,
)
from modules.badms.services import (
    archives,
    backups,
    notifications,
    restorations,
    special_archives,
    storage_extensions,
)
from modules.badms.services.storage import badms_storage, require_secure_storage
from modules.directory import contracts as directory

MODULE = HasModuleGrant("badms")


class ArchiveCollectionView(APIView):
    permission_classes = [MODULE]
    paginator = CursorPagination()

    @extend_schema(responses=ArchivePageSerializer, operation_id="badms_archive_list")
    def get(self, request):
        actor = request.principal
        rows = ArchiveRequest.objects.all()
        if actor.has_permission("badms.archive.review_department"):
            users = directory.get_users([actor.user_id])
            department = users.get(actor.user_id).department if actor.user_id in users else ""
            if not department:
                return Response({"results": []})
            rows = rows.filter(department=department).exclude(
                user_id=actor.user_id, status="Submitted")
        elif not (actor.has_permission("badms.archive.classify") or
                  actor.has_permission("badms.archive.encrypt")):
            rows = rows.filter(user_id=actor.user_id)
        page = self.paginator.paginate_queryset(rows.order_by("-id"), request, view=self)
        return self.paginator.get_paginated_response(ArchiveReadSerializer(page, many=True).data)

    @extend_schema(request=ArchiveCreateSerializer, responses={201: ArchiveReadSerializer},
                   operation_id="badms_archive_create")
    def post(self, request):
        if not request.principal.has_permission("badms.archive.create"):
            raise PermissionDeniedError()
        if not request.is_secure() and not settings.DEBUG:
            from core.api.exceptions import ConflictError
            raise ConflictError("Secure transport is required for archive uploads.",
                                code="tls_required")
        if not settings.DEBUG:
            require_secure_storage()
        payload = ArchiveCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        principal = request.principal
        ref = directory.get_users([principal.user_id]).get(principal.user_id)
        if ref is None or not ref.department:
            raise BadRequestError("A department is required to submit an archival request.",
                                  code="department_required")
        upload = payload.validated_data.pop("attachment")
        safe_name = sanitise_filename(upload.name, fallback="archive")
        key = badms_storage().save(f"badms/incoming/{principal.user_id}/{safe_name}", upload)
        checksum = ""
        try:
            import hashlib
            with badms_storage().open(key, "rb") as stream:
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                checksum = digest.hexdigest()
            with transaction.atomic():
                row = ArchiveRequest.objects.create(
                    user_id=principal.user_id, department=ref.department,
                    requester_email=ref.email,
                    file_name=payload.validated_data["file_name"],
                    file_date=payload.validated_data["file_date"],
                    owners=payload.validated_data["owners"],
                    file_type=payload.validated_data["file_type"],
                    reason=payload.validated_data["reason"], attachment_key=key,
                    attachment_size_bytes=upload.size,
                    initial_classification=payload.validated_data["initial_classification"],
                    checksum_sha256=checksum)
                AuditEvent.objects.create(
                    actor_user_id=principal.user_id, department=ref.department,
                    action="archive.submit", object_type="archive_request",
                    object_id=str(row.pk), outcome="Submitted",
                    details={"checksum_sha256": checksum})
                hod_emails = settings.BADMS_HOD_EMAILS.get(ref.department, [])
                if isinstance(hod_emails, str):
                    hod_emails = [hod_emails]
                notifications.enqueue([ref.email, *hod_emails],
                                      subject="Archival request submitted",
                                      body=f"Archival request {row.pk} was submitted.")
        except Exception:
            badms_storage().delete(key)
            raise
        return Response(ArchiveReadSerializer(row).data, status=status.HTTP_201_CREATED)


class ArchiveDetailView(APIView):
    permission_classes = [MODULE, HasPermission(
        "badms.archive.view_self", "badms.archive.review_department",
        "badms.archive.classify", "badms.archive.encrypt")]

    @extend_schema(responses=ArchiveReadSerializer, operation_id="badms_archive_detail")
    def get(self, request, pk):
        actor = request.principal
        row = ArchiveRequest.objects.filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No such archival request.")
        if row.user_id != actor.user_id:
            if actor.has_permission("badms.archive.review_department"):
                users = directory.get_users([actor.user_id])
                department = users.get(actor.user_id).department if actor.user_id in users else ""
                if not department or row.department != department:
                    raise NotFoundError("No such archival request.")
            elif not (actor.has_permission("badms.archive.classify") or
                      actor.has_permission("badms.archive.encrypt")):
                raise NotFoundError("No such archival request.")
        return Response(ArchiveReadSerializer(row).data)


class ArchiveDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archive.review_department")]

    @extend_schema(request=ArchiveDecisionSerializer, responses=ArchiveReadSerializer)
    def post(self, request, pk):
        payload = ArchiveDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        users = directory.get_users([request.principal.user_id])
        ref = users.get(request.principal.user_id)
        department = ref.department if ref else ""
        if not department:
            raise BadRequestError("Department scope is unavailable.", code="department_required")
        row = archives.decide(request_id=pk, actor=request.principal, department=department,
                              approve=payload.validated_data["decision"] == "approve",
                              note=payload.validated_data["note"])
        return Response(ArchiveReadSerializer(row).data)


class ArchiveClassificationView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archive.classify")]

    @extend_schema(request=ClassificationSerializer, responses=ArchiveReadSerializer)
    def post(self, request, pk):
        payload = ClassificationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = archives.classify(request_id=pk, actor=request.principal,
                                classification=payload.validated_data["classification"])
        return Response(ArchiveReadSerializer(row).data)


class ArchiveEncryptionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archive.encrypt")]

    @extend_schema(request=None, responses=ArchiveReadSerializer)
    def post(self, request, pk):
        row = archives.create_sensitive_archive(request_id=pk, actor=request.principal)
        return Response(ArchiveReadSerializer(row).data)


class RestorationCollectionView(APIView):
    permission_classes = [MODULE]
    paginator = CursorPagination()

    @extend_schema(responses=RestorePageSerializer)
    def get(self, request):
        actor = request.principal
        rows = restorations.RestorationRequest.objects.filter(user_id=actor.user_id)
        if actor.has_permission("badms.restore.execute"):
            rows = restorations.RestorationRequest.objects.exclude(
                user_id=actor.user_id,
                status="Sensitive Restoration Pending Approval")
        page = self.paginator.paginate_queryset(rows.order_by("-id"), request, view=self)
        return self.paginator.get_paginated_response(RestoreReadSerializer(page, many=True).data)

    @extend_schema(request=RestoreCreateSerializer, responses={201: RestoreReadSerializer})
    def post(self, request):
        if not request.principal.has_permission("badms.restore.create"):
            raise PermissionDeniedError()
        payload = RestoreCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = restorations.request_restore(
            actor=request.principal,
            archive_id=payload.validated_data["archive_request_id"])
        return Response(RestoreReadSerializer(row).data, status=status.HTTP_201_CREATED)


class RestorationDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.restore.approve")]

    @extend_schema(request=ArchiveDecisionSerializer, responses=RestoreReadSerializer)
    def post(self, request, pk):
        decision = request.data.get("decision")
        if decision not in ("approve", "reject"):
            raise BadRequestError("decision must be approve or reject.",
                                  code="invalid_decision")
        row = restorations.decide_sensitive(request_id=pk, actor=request.principal,
                                             approve=decision == "approve")
        return Response(RestoreReadSerializer(row).data)


class RestorationExecutionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.restore.execute")]

    @extend_schema(request=None, responses=RestoreReadSerializer)
    def post(self, request, pk):
        row = restorations.execute_restore(request_id=pk, actor=request.principal)
        return Response(RestoreReadSerializer(row).data)


class RestorationDownloadView(APIView):
    permission_classes = [MODULE, HasPermission("badms.restore.view_self",
                                                "badms.restore.execute")]

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    def get(self, request, pk):
        row = restorations.RestorationRequest.objects.filter(pk=pk, status="Restored").first()
        if row is None:
            raise NotFoundError("No restored archive was found.")
        if (row.user_id != request.principal.user_id and
                not request.principal.has_permission("badms.restore.execute")):
            raise NotFoundError("No restored archive was found.")
        try:
            stream = badms_storage().open(row.restored_key, "rb")
        except OSError as exc:
            raise NotFoundError("The restored archive is unavailable.") from exc
        filename = sanitise_filename(row.archive_request.file_name, fallback="restored-archive")
        return FileResponse(stream, as_attachment=True, filename=filename,
                            content_type="application/octet-stream")


class StorageExtensionCollectionView(APIView):
    permission_classes = [MODULE]
    paginator = CursorPagination()

    @extend_schema(responses=StorageExtensionPageSerializer)
    def get(self, request):
        actor = request.principal
        rows = storage_extensions.StorageExtensionRequest.objects.filter(user_id=actor.user_id)
        if actor.has_permission("badms.storage_extension.review_department"):
            users = directory.get_users([actor.user_id])
            department = users.get(actor.user_id).department if actor.user_id in users else ""
            rows = (rows.filter(department=department).exclude(
                user_id=actor.user_id, status="Submitted") if department else rows.none())
        page = self.paginator.paginate_queryset(rows.order_by("-id"), request, view=self)
        return self.paginator.get_paginated_response(
            StorageExtensionReadSerializer(page, many=True).data)

    @extend_schema(request=StorageExtensionCreateSerializer,
                   responses={201: StorageExtensionReadSerializer})
    def post(self, request):
        if not request.principal.has_permission("badms.storage_extension.create"):
            raise PermissionDeniedError()
        payload = StorageExtensionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = request.principal
        ref = directory.get_users([actor.user_id]).get(actor.user_id)
        if ref is None or not ref.department:
            raise BadRequestError("A department is required to submit this request.",
                                  code="department_required")
        attachment_key = ""
        upload = payload.validated_data.get("attachment")
        if upload is not None:
            if not settings.DEBUG:
                require_secure_storage()
            from core.files.validators import sanitise_filename
            name = sanitise_filename(upload.name, fallback="storage-support")
            attachment_key = badms_storage().save(
                f"badms/storage-extension/{actor.user_id}/{name}", upload)
        try:
            row = storage_extensions.submit(
                actor=actor, department=ref.department,
                requested_bytes=payload.validated_data["requested_bytes"],
                justification=payload.validated_data["justification"],
                requester_email=ref.email,
                attachment_key=attachment_key)
        except Exception:
            if attachment_key:
                badms_storage().delete(attachment_key)
            raise
        return Response(StorageExtensionReadSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class StorageExtensionDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("badms.storage_extension.review_department")]

    @extend_schema(request=StorageExtensionDecisionSerializer,
                   responses=StorageExtensionReadSerializer)
    def post(self, request, pk):
        payload = StorageExtensionDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        users = directory.get_users([request.principal.user_id])
        ref = users.get(request.principal.user_id)
        department = ref.department if ref else ""
        if not department:
            raise BadRequestError("Department scope is unavailable.", code="department_required")
        row = storage_extensions.decide(
            request_id=pk, actor=request.principal, department=department,
            approve=payload.validated_data["decision"] == "approve",
            note=payload.validated_data["note"])
        return Response(StorageExtensionReadSerializer(row).data)


class BackupRunCollectionView(APIView):
    permission_classes = [MODULE]
    paginator = CursorPagination()

    @extend_schema(responses=BackupRunPageSerializer)
    def get(self, request):
        if not request.principal.has_permission("badms.backup.view"):
            raise PermissionDeniedError("You do not have permission to view backups.")
        rows = BackupRun.objects.order_by("-id")
        page = self.paginator.paginate_queryset(rows, request, view=self)
        return self.paginator.get_paginated_response(BackupRunSerializer(page, many=True).data)

    @extend_schema(request=None, responses={202: BackupRunSerializer})
    def post(self, request):
        if not request.principal.has_permission("badms.backup.run_manual"):
            raise PermissionDeniedError("You do not have permission to trigger backups.")
        row = backups.queue_manual(actor=request.principal)
        return Response(BackupRunSerializer(row).data, status=status.HTTP_202_ACCEPTED)


class SpecialArchiveView(APIView):
    permission_classes = [MODULE, HasPermission("badms.archive.special")]

    @extend_schema(request=SpecialArchiveSerializer,
                   responses={201: SpecialArchiveReadSerializer})
    def post(self, request):
        if not request.is_secure() and not settings.DEBUG:
            from core.api.exceptions import ConflictError
            raise ConflictError("Secure transport is required for archive uploads.",
                                code="tls_required")
        payload = SpecialArchiveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        row = special_archives.perform(
            actor=request.principal,
            offline_request_reference=values["offline_request_reference"],
            research_description=values["research_description"],
            upload=values["attachment"])
        return Response(SpecialArchiveReadSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class BackupScheduleCollectionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses=BackupScheduleListSerializer)
    def get(self, request):
        actor = request.principal
        rows = BackupSchedule.objects.all()
        if not actor.has_permission("badms.schedule.global.manage"):
            if actor.has_permission("badms.schedule.local.manage"):
                rows = rows.filter(scope="local")
            else:
                raise PermissionDeniedError("You do not have permission to view schedules.")
        return Response({"results": BackupScheduleSerializer(
            rows.order_by("dataset"), many=True).data})

    @extend_schema(request=BackupScheduleSerializer,
                   responses={201: BackupScheduleSerializer})
    def post(self, request):
        actor = request.principal
        payload = BackupScheduleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        scope = payload.validated_data["scope"]
        needed = ("badms.schedule_global.manage" if scope == "global"
                  else "badms.schedule_local.manage")
        if not actor.has_permission(needed):
            raise PermissionDeniedError("You do not have permission to manage this schedule.")
        if payload.validated_data["frequency"] not in ("daily", "weekly"):
            raise BadRequestError("frequency must be daily or weekly.", code="invalid_frequency")
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(payload.validated_data["timezone"])
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise BadRequestError("timezone must be a valid IANA time zone.",
                                  code="invalid_timezone") from exc
        row = payload.save(updated_by=actor.user_id)
        AuditEvent.objects.create(actor_user_id=actor.user_id,
                                  action=f"schedule.{scope}.create",
                                  object_type="backup_schedule", object_id=str(row.pk),
                                  outcome="success")
        return Response(BackupScheduleSerializer(row).data, status=status.HTTP_201_CREATED)


class BackupScheduleDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(request=BackupScheduleSerializer, responses=BackupScheduleSerializer)
    def patch(self, request, pk):
        row = BackupSchedule.objects.filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No such backup schedule.")
        actor = request.principal
        needed = ("badms.schedule_global.manage" if row.scope == "global"
                  else "badms.schedule_local.manage")
        if not actor.has_permission(needed):
            raise PermissionDeniedError("You do not have permission to manage this schedule.")
        payload = BackupScheduleSerializer(row, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        row = payload.save(updated_by=actor.user_id)
        AuditEvent.objects.create(actor_user_id=actor.user_id,
                                  action=f"schedule.{row.scope}.update",
                                  object_type="backup_schedule", object_id=str(row.pk),
                                  outcome="success")
        return Response(BackupScheduleSerializer(row).data)


class AuditEventListView(APIView):
    permission_classes = [MODULE]
    paginator = CursorPagination()

    @extend_schema(responses=AuditPageSerializer)
    def get(self, request):
        actor = request.principal
        rows = AuditEvent.objects.all()
        if actor.has_permission("badms.security.audit"):
            rows = rows.filter(action__in=("archive.sensitive_created", "archive.classify",
                                           "restore.sensitive_decision",
                                           "security_policy.update"))
        elif actor.has_permission("badms.audit.view"):
            rows = rows.exclude(action="archive.special.perform")
        elif actor.has_permission("badms.reports.department"):
            users = directory.get_users([actor.user_id])
            ref = users.get(actor.user_id)
            rows = rows.filter(department=ref.department) if ref and ref.department else rows.none()
        else:
            raise PermissionDeniedError("You do not have permission to view audit events.")
        page = self.paginator.paginate_queryset(rows.order_by("-id"), request, view=self)
        return self.paginator.get_paginated_response(AuditEventSerializer(page, many=True).data)


class DepartmentReportView(APIView):
    permission_classes = [MODULE, HasPermission("badms.reports.department")]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        users = directory.get_users([request.principal.user_id])
        ref = users.get(request.principal.user_id)
        if ref is None or not ref.department:
            return Response({"department": "", "archive_requests": 0,
                             "storage_extension_requests": 0})
        department = ref.department
        return Response({
            "department": department,
            "archive_requests": ArchiveRequest.objects.filter(department=department).count(),
            "storage_extension_requests": StorageExtensionRequest.objects.filter(
                department=department).count(),
        })


class SecurityReportView(APIView):
    permission_classes = [MODULE, HasPermission("badms.security.audit")]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        rows = (AuditEvent.objects.filter(action__in=("archive.sensitive_created",
                                                      "archive.classify",
                                                      "restore.sensitive_decision",
                                                      "security_policy.update"))
                .values("action", "outcome").annotate(total=Count("id"))
                .order_by("action", "outcome"))
        return Response({"events": list(rows)})


class MyStorageThresholdView(APIView):
    permission_classes = [MODULE, HasPermission("badms.storage_extension.create")]

    @extend_schema(responses=MyStorageThresholdSerializer)
    def get(self, request):
        row = StorageThreshold.objects.filter(user_id=request.principal.user_id).first()
        if row is None:
            quota = getattr(settings, "BADMS_USER_QUOTA_BYTES", None)
            return Response({"usage_bytes": 0, "quota_bytes": quota,
                             "is_full": False, "updated_at": None})
        return Response(StorageThresholdSerializer(row).data)


class SecurityPolicyView(APIView):
    permission_classes = [MODULE, HasPermission("badms.security_policy.manage")]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        row = SecurityPolicy.objects.filter(pk=1).first()
        retention = (row.retention_days if row else
                     getattr(settings, "BADMS_RETENTION_DAYS", {}))
        classes = {choice[0] for choice in ArchiveRequest.CLASSIFICATION}
        configured = (isinstance(retention, dict) and set(retention) == classes
                      and all(type(days) is int and days > 0
                              for days in retention.values()))
        return Response({"sensitive_at_rest": "AES-256",
                         "sensitive_in_transit": "AES-256",
                         "retention_days": retention,
                         "configured": configured})

    @extend_schema(request=SecurityPolicySerializer,
                   responses={200: OpenApiTypes.OBJECT})
    def put(self, request):
        serializer = SecurityPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row, _ = SecurityPolicy.objects.update_or_create(
            pk=1, defaults={"retention_days": serializer.validated_data["retention_days"],
                            "updated_by": request.principal.user_id})
        AuditEvent.objects.create(
            actor_user_id=request.principal.user_id, action="security_policy.update",
            object_type="security_policy", object_id="1", outcome="success",
            details={"retention_days": row.retention_days,
                     "sensitive_at_rest": "AES-256",
                     "sensitive_in_transit": "AES-256"})
        return Response({"sensitive_at_rest": "AES-256",
                         "sensitive_in_transit": "AES-256",
                         "retention_days": row.retention_days,
                         "configured": True})
