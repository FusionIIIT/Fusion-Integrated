from django.db.models import Q
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.badms.api.serializers import ArchiveRequestSerializer, AuditEventSerializer, BackupRunSerializer
from modules.badms.models import ArchiveRequest, AuditEvent, BackupRun
from modules.badms.services.archives import (classify_archive,
                                             complete_sensitive_archive,
                                             decide_archive)
from modules.badms.services.backups import create_backup
from modules.badms.services.audit import record
from modules.badms.services.encryption import decrypt_payload, encrypt_upload

MODULE = HasModuleGrant("badms")
P_BACKUP = "badms.backup.run"
P_BACKUP_VIEW = "badms.backup.view"
P_ARCHIVE_SUBMIT = "badms.archive.submit"
P_ARCHIVE_REVIEW = "badms.archive.review"
P_ARCHIVE_CLASSIFY = "badms.archive.classify"
P_ARCHIVE_SECURE = "badms.archive.secure"
P_AUDIT_VIEW = "badms.audit.view"


def _actor(request):
    return request.principal


class BackupListView(APIView):
    permission_classes = [MODULE, HasPermission(P_BACKUP_VIEW)]

    def get(self, request):
        actor = _actor(request)
        runs = BackupRun.objects.all()
        if not (actor.has_permission(P_BACKUP) or actor.has_permission(P_ARCHIVE_CLASSIFY)):
            runs = runs.filter(created_by=actor.user_id)
        runs = runs[:50]
        return Response(BackupRunSerializer(runs, many=True, context={"request": request}).data)


class BackupRunView(APIView):
    permission_classes = [MODULE, HasPermission(P_BACKUP)]

    def post(self, request):
        run = create_backup(_actor(request).user_id)
        return Response(BackupRunSerializer(run, context={"request": request}).data,
                        status=status.HTTP_201_CREATED if run.status == BackupRun.Status.SUCCESS
                        else status.HTTP_500_INTERNAL_SERVER_ERROR)


class BackupDownloadView(APIView):
    permission_classes = [MODULE, HasPermission(P_BACKUP)]

    def get(self, request, pk):
        run = get_object_or_404(BackupRun, pk=pk, status=BackupRun.Status.SUCCESS)
        response = FileResponse(run.artifact.open("rb"), as_attachment=True,
                                filename=run.artifact.name.rsplit("/", 1)[-1],
                                content_type="application/gzip")
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ArchiveListCreateView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [MODULE]

    def get(self, request):
        actor = _actor(request)
        if actor.has_permission(P_ARCHIVE_CLASSIFY):
            items = ArchiveRequest.objects.all()
        elif actor.has_permission(P_ARCHIVE_SECURE):
            items = ArchiveRequest.objects.filter(status=ArchiveRequest.Status.SECURITY_REVIEW)
        elif actor.has_permission(P_ARCHIVE_REVIEW):
            items = ArchiveRequest.objects.filter(department=actor.department)
        else:
            items = ArchiveRequest.objects.filter(requester_id=actor.user_id)
        return Response(ArchiveRequestSerializer(items[:100], many=True, context={"request": request}).data)

    def post(self, request):
        if not _actor(request).has_permission(P_ARCHIVE_SUBMIT):
            return Response({"detail": "You cannot submit archival requests."}, status=403)
        serializer = ArchiveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["attachment"] = encrypt_upload(
            serializer.validated_data["attachment"])
        item = serializer.save(requester_id=_actor(request).user_id,
                              department=_actor(request).department,
                              initial_classification=serializer.validated_data.get(
                                  "initial_classification", ArchiveRequest.Classification.ROUTINE))
        record(_actor(request).user_id, "archive.submitted", object_type="archive_request",
               object_id=item.pk, details={"status": item.status})
        return Response(ArchiveRequestSerializer(item, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


class ArchiveDecisionView(APIView):
    parser_classes = [JSONParser]
    permission_classes = [MODULE, HasPermission(P_ARCHIVE_REVIEW)]

    def post(self, request, pk):
        try:
            item = ArchiveRequest.objects.get(pk=pk, department=_actor(request).department)
            if item.status != ArchiveRequest.Status.SUBMITTED:
                return Response({"detail": "Only submitted requests can receive a HoD decision."}, status=400)
            item = decide_archive(pk, _actor(request).user_id,
                                  request.data.get("action", ""),
                                  note=request.data.get("note", ""))
        except ArchiveRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ArchiveRequestSerializer(item, context={"request": request}).data)


class ArchiveClassificationView(APIView):
    parser_classes = [JSONParser]
    permission_classes = [MODULE, HasPermission(P_ARCHIVE_CLASSIFY)]

    def post(self, request, pk):
        try:
            item = classify_archive(pk, _actor(request).user_id,
                                    request.data.get("classification", ""))
        except ArchiveRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ArchiveRequestSerializer(item, context={"request": request}).data)


class SensitiveArchiveCompleteView(APIView):
    parser_classes = [JSONParser]
    permission_classes = [MODULE, HasPermission(P_ARCHIVE_SECURE)]

    def post(self, request, pk):
        try:
            item = complete_sensitive_archive(pk, _actor(request).user_id)
        except ArchiveRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ArchiveRequestSerializer(item, context={"request": request}).data)


class ArchiveAttachmentView(APIView):
    permission_classes = [MODULE]

    def get(self, request, pk):
        actor = _actor(request)
        item = get_object_or_404(ArchiveRequest, pk=pk)
        authorized = (
            actor.has_permission(P_ARCHIVE_CLASSIFY)
            or actor.has_permission(P_ARCHIVE_SECURE)
            or (actor.has_permission(P_ARCHIVE_REVIEW)
                and item.department == actor.department)
            or item.requester_id == actor.user_id
        )
        if not authorized:
            return Response({"detail": "Request not found."}, status=404)
        try:
            with item.attachment.open("rb") as encrypted:
                payload = decrypt_payload(encrypted)
        except (ValueError, RuntimeError):
            return Response({"detail": "The archive could not be opened."}, status=500)
        return FileResponse(ContentFile(payload), as_attachment=True,
                            filename=item.file_name,
                            content_type="application/octet-stream")


class AuditListView(APIView):
    permission_classes = [MODULE, HasPermission(P_AUDIT_VIEW)]

    def get(self, request):
        actor = _actor(request)
        events = AuditEvent.objects.all()
        if actor.has_permission(P_ARCHIVE_CLASSIFY):
            pass
        elif actor.has_permission(P_ARCHIVE_REVIEW):
            ids = ArchiveRequest.objects.filter(department=actor.department).values("pk")
            events = events.filter(Q(actor_id=actor.user_id) |
                                   Q(object_type="archive_request", object_id__in=ids))
        elif actor.has_permission(P_ARCHIVE_SUBMIT):
            events = events.filter(Q(actor_id=actor.user_id) |
                                   Q(object_type="archive_request",
                                     object_id__in=ArchiveRequest.objects.filter(
                                         requester_id=actor.user_id).values("pk")))
        return Response(AuditEventSerializer(events[:100], many=True).data)
