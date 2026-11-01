from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import DomainError, NotFoundError
from modules.psm import models as m
from modules.psm import selectors, services
from modules.psm.access import require


class UploadSerializer(serializers.Serializer):
    entity = serializers.ChoiceField(choices=["indent", "case", "vendor"])
    object_id = serializers.UUIDField()
    file = serializers.FileField(max_length=160)


class AttachmentView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=UploadSerializer,
        responses=OpenApiTypes.OBJECT,
        tags=["psm"],
        summary="Retain a private supporting document",
    )
    def post(self, request):
        form = UploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        principal = request.principal
        entity, pk, upload = data["entity"], data["object_id"], data["file"]
        if upload.size > 10 * 1024 * 1024:
            raise DomainError("Documents must be at most 10 MiB.")
        if entity == "vendor":
            require(principal, ["ps_admin"])
            obj = selectors.collection(principal, "vendors").filter(pk=pk).first()
        elif entity == "case":
            require(principal, ["employee", "department_admin", "department_head", "ps_admin"])
            obj = selectors.collection(principal, "cases").filter(pk=pk).first()
        else:
            require(principal, ["employee", "department_admin", "department_head", "ps_admin"])
            obj = selectors.indent(principal, pk)
        if obj is None:
            raise NotFoundError()
        row = m.Attachment.objects.create(
            entity=entity,
            object_id=pk,
            actor_id=principal.user_id,
            original_name=upload.name,
            file=upload,
        )
        services.audit(
            principal, obj, "document_retained", {"attachment": str(row.pk), "name": upload.name}
        )
        return Response({"id": str(row.pk), "original_name": row.original_name}, status=201)


class AttachmentDownloadView(APIView):
    @extend_schema(
        responses=OpenApiTypes.BINARY,
        tags=["psm"],
        summary="Download an authorized private PSM document",
    )
    def get(self, request, pk):
        row = selectors.collection(request.principal, "attachments").filter(pk=pk).first()
        if row is None:
            raise NotFoundError()
        try:
            handle = row.file.open("rb")
        except FileNotFoundError as exc:
            raise NotFoundError("The stored document is unavailable.") from exc
        return FileResponse(
            handle,
            as_attachment=True,
            filename=row.original_name,
            content_type="application/octet-stream",
        )
