"""Notification inbox (host/staff and visitor), arrivals, ops outbox."""
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.vms.api.notify.serializers import (
    ArrivalSerializer,
    NotificationSerializer,
    OutboxSerializer,
)
from modules.vms.auth import IsVisitorSession, VisitorSessionAuthentication
from modules.vms.selectors import notifications as sel
from modules.vms.services import delivery

VIEW_SELF = HasPermission("vms.notification.view_self")
AUDIT_VIEW = HasPermission("vms.audit.view")


def _flag(request, name) -> bool:
    return request.query_params.get(name, "").lower() in {"1", "true", "yes"}


def _page(request, qs):
    limit = sel.clamp_limit(request.query_params.get("limit"))
    return {"results": NotificationSerializer(qs[:limit], many=True).data}


# --- host / staff ---------------------------------------------------------------------

class InboxView(APIView):
    permission_classes = [VIEW_SELF]

    def get(self, request):
        qs = sel.inbox_for_user(request.principal.user_id,
                                unread_only=_flag(request, "unread"))
        return Response(_page(request, qs))


class UnreadCountView(APIView):
    permission_classes = [VIEW_SELF]

    def get(self, request):
        return Response({"unread": sel.unread_count_for_user(request.principal.user_id)})


class MarkReadView(APIView):
    permission_classes = [VIEW_SELF]

    def post(self, request, pk):
        row = delivery.mark_read(pk, user_id=request.principal.user_id)
        return Response(NotificationSerializer(row).data)


class ReadAllView(APIView):
    permission_classes = [VIEW_SELF]

    def post(self, request):
        n = delivery.mark_all_read(user_id=request.principal.user_id)
        return Response({"marked": n})


class ArrivalsView(APIView):
    permission_classes = [VIEW_SELF]

    def get(self, request):
        limit = sel.clamp_limit(request.query_params.get("limit"), default=20)
        rows = sel.arrivals_for_host(request.principal.user_id, limit)
        return Response({"results": ArrivalSerializer(rows, many=True).data})


# --- ops outbox -------------------------------------------------------------------------

class OutboxView(APIView):
    permission_classes = [AUDIT_VIEW]

    def get(self, request):
        qs = sel.outbox(status=request.query_params.get("status") or None,
                        topic=request.query_params.get("topic") or None)
        limit = sel.clamp_limit(request.query_params.get("limit"))
        return Response({"results": OutboxSerializer(qs[:limit], many=True).data})


class OutboxRetryView(APIView):
    permission_classes = [AUDIT_VIEW]

    def post(self, request, pk):
        row = delivery.retry_failed(pk, actor=request.principal)
        return Response(OutboxSerializer(row).data)


# --- visitor ----------------------------------------------------------------------------

class VisitorAuthMixin:
    authentication_classes = [VisitorSessionAuthentication]
    permission_classes = [IsVisitorSession]


class VisitorInboxView(VisitorAuthMixin, APIView):
    def get(self, request):
        qs = sel.inbox_for_visitor(request.principal.visitor_id,
                                   unread_only=_flag(request, "unread"))
        data = _page(request, qs)
        data["unread"] = sel.unread_count_for_visitor(request.principal.visitor_id)
        return Response(data)


class VisitorMarkReadView(VisitorAuthMixin, APIView):
    def post(self, request, pk):
        row = delivery.mark_read(pk, visitor_id=request.principal.visitor_id)
        return Response(NotificationSerializer(row).data)

