"""Attaching a Drive link, and reaching one.

Reaching is the sensitive half: the link is a capability, so it is disclosed
only here and only after the scope check, which narrows the queryset before
the row is fetched — someone else's document is a 404, not a 403.
"""
from __future__ import annotations

from urllib.parse import quote

from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from core.files import storage
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.placement.api.serializers import DocumentLinkSerializer, ProfileDocumentSerializer
from modules.placement.authentication import RecruiterAuthentication
from modules.placement.models import Application, ProfileDocument
from modules.placement.selectors import scoping
from modules.placement.services import documents as document_service

MODULE = HasModuleGrant("placement_cell")
P_VIEW_SELF = "placement_cell.application.view_self"


def _actor(request):
    return getattr(request, "principal", None)


@extend_schema(responses=ProfileDocumentSerializer(many=True))
class MyDocumentsView(APIView):
    """GET  /placement/documents   my documents
        POST /placement/documents   attach a Drive link
    """

    authentication_classes = [RecruiterAuthentication,
                              *APIView.authentication_classes]
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    throttle_scope = "upload"

    def get(self, request):
        rows = ProfileDocument.objects.filter(
            user_id=_actor(request).user_id, is_active=True).order_by("-created_at")
        return Response({"results": ProfileDocumentSerializer(rows, many=True).data})

    @extend_schema(request=DocumentLinkSerializer,
                   responses={201: ProfileDocumentSerializer})
    def post(self, request):
        payload = DocumentLinkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        document = document_service.attach_link(
            user_id=_actor(request).user_id, **payload.validated_data)
        return Response(ProfileDocumentSerializer(document).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(responses={204: None})
class MyDocumentDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def delete(self, request, pk):
        document_service.remove(document_id=pk, user_id=_actor(request).user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses={
    302: OpenApiResponse(description="Redirect to the document. The Drive URL "
                                     "is disclosed here and nowhere else."),
    (200, "application/octet-stream"): OpenApiTypes.BINARY,
    404: OpenApiResponse(description="Absent, or outside the caller's scope — "
                                     "the two are deliberately the same answer."),
})
class DocumentDownloadView(APIView):
    """Readable by the owner, by staff, and by a recruiter the owner has a
    live application with — the same scope that governs the profile."""

    authentication_classes = [RecruiterAuthentication,
                              *APIView.authentication_classes]
    permission_classes = [MODULE]

    def get(self, request, pk):
        actor = _actor(request)

        # Narrowed by queryset, so a foreign document is absent, not forbidden.
        readable_user_ids = scoping.profiles_for(actor).values("user_id")
        document = (ProfileDocument.objects
                    .filter(pk=pk, is_active=True,
                            user_id__in=readable_user_ids)
                    .first())
        if document is None:
            raise NotFoundError("No such document.")

        if getattr(actor, "kind", None) == "recruiter":
            # A reachable profile is not enough: it must be on their own posting.
            attached = Application.objects.filter(
                posting__company_id=actor.company_id,
                user_id=document.user_id,
            ).exclude(status__in=("draft", "withdrawn", "auto_withdrawn")).exists()
            if not attached or document.kind not in ("resume", "certificate"):
                raise NotFoundError("No such document.")

        return _serve(document)


def _serve(document: ProfileDocument):
    if document.is_link:
        # A redirect, not a fetch: fetching would make this an SSRF primitive.
        response = HttpResponseRedirect(document.drive_url)
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response
    return _serve_stored(document)


def _serve_stored(document: ProfileDocument):
    """The pre-switch upload path, kept so older documents still open."""
    filename = document.original_filename or "download"
    disposition = (f"attachment; filename=\"{filename}\"; "
                   f"filename*=UTF-8''{quote(filename)}")

    internal = storage.internal_url(document.storage_key)
    if internal:
        response = HttpResponse(status=200)
        response["X-Accel-Redirect"] = internal
        response["Content-Type"] = document.content_type
    else:
        response = FileResponse(storage.open_stream(document.storage_key),
                                content_type=document.content_type)

    response["Content-Disposition"] = disposition
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response
