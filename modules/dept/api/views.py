"""HTTP layer: parse, scope, delegate, serialise. Reads come from
`selectors.scoping`; writes go through `services`."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.dept.api import serializers as s
from modules.dept.selectors import scoping
from modules.dept.services import announcements as announcement_service
from modules.dept.services import feedback as feedback_service
from modules.dept.services import stock as stock_service

MODULE = HasModuleGrant("dept")


def _actor(request):
    return request.principal


# -- announcements ---------------------------------------------------------------
class AnnouncementListView(APIView):
    permission_classes = [MODULE, HasPermission("dept.announcement.view")]

    @extend_schema(responses=s.AnnouncementSerializer(many=True))
    def get(self, request):
        rows = scoping.announcements_for(_actor(request))
        return Response(s.AnnouncementSerializer(rows, many=True).data)

    @extend_schema(request=s.AnnouncementWriteSerializer,
                   responses=s.AnnouncementSerializer)
    def post(self, request):
        payload = s.AnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        created = announcement_service.publish(actor=_actor(request),
                                               **payload.validated_data)
        return Response(s.AnnouncementSerializer(created).data,
                        status=status.HTTP_201_CREATED)


class AnnouncementDetailView(APIView):
    permission_classes = [MODULE, HasPermission("dept.announcement.manage")]

    @extend_schema(request=s.AnnouncementEditSerializer,
                   responses=s.AnnouncementSerializer)
    def patch(self, request, pk):
        payload = s.AnnouncementEditSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        updated = announcement_service.edit(
            announcement_id=pk, actor=_actor(request), **payload.validated_data)
        return Response(s.AnnouncementSerializer(updated).data)

    @extend_schema(responses=s.AnnouncementSerializer)
    def delete(self, request, pk):
        deleted = announcement_service.set_status(
            announcement_id=pk, actor=_actor(request), status="deleted")
        return Response(s.AnnouncementSerializer(deleted).data)


class AnnouncementStatusView(APIView):
    permission_classes = [MODULE, HasPermission("dept.announcement.manage")]

    @extend_schema(request=s.AnnouncementStatusSerializer,
                   responses=s.AnnouncementSerializer)
    def post(self, request, pk):
        payload = s.AnnouncementStatusSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        updated = announcement_service.set_status(
            announcement_id=pk, actor=_actor(request),
            status=payload.validated_data["status"])
        return Response(s.AnnouncementSerializer(updated).data)


# -- inventory & stock ---------------------------------------------------------
class InventoryListView(APIView):
    permission_classes = [MODULE, HasPermission("dept.inventory.view")]

    @extend_schema(responses=s.InventoryItemSerializer(many=True))
    def get(self, request):
        return Response(s.InventoryItemSerializer(scoping.inventory(),
                                                  many=True).data)

    @extend_schema(request=s.InventoryWriteSerializer,
                   responses=s.InventoryItemSerializer)
    def post(self, request):
        payload = s.InventoryWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = stock_service.add_inventory(actor=_actor(request),
                                           **payload.validated_data)
        return Response(s.InventoryItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


class StockRequestListView(APIView):
    permission_classes = [MODULE, HasPermission("dept.inventory.view")]

    @extend_schema(responses=s.StockRequestSerializer(many=True))
    def get(self, request):
        rows = scoping.stock_requests_for(_actor(request))[:200]
        return Response(s.StockRequestSerializer(rows, many=True).data)

    @extend_schema(request=s.StockRequestWriteSerializer,
                   responses=s.StockRequestSerializer)
    def post(self, request):
        payload = s.StockRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        created = stock_service.request_stock(
            actor=_actor(request), item_id=data["item"],
            quantity=data["quantity"], purpose=data["purpose"])
        return Response(s.StockRequestSerializer(created).data,
                        status=status.HTTP_201_CREATED)


class StockRequestDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("dept.stock_request.decide")]

    @extend_schema(request=s.StockDecisionSerializer,
                   responses=s.StockRequestSerializer)
    def post(self, request, pk):
        payload = s.StockDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        decided = stock_service.decide(
            request_id=pk, actor=_actor(request),
            approve=payload.validated_data["approve"],
            note=payload.validated_data["note"])
        return Response(s.StockRequestSerializer(decided).data)


class StockRequestIssueView(APIView):
    permission_classes = [MODULE, HasPermission("dept.stock_request.issue")]

    @extend_schema(request=None, responses=s.StockRequestSerializer)
    def post(self, request, pk):
        issued = stock_service.issue(request_id=pk, actor=_actor(request))
        return Response(s.StockRequestSerializer(issued).data)


class IssuedHistoryView(APIView):
    permission_classes = [MODULE, HasPermission("dept.inventory.view")]

    @extend_schema(responses=s.StockRequestSerializer(many=True))
    def get(self, request):
        rows = scoping.issued_history_for(_actor(request))[:200]
        return Response(s.StockRequestSerializer(rows, many=True).data)


class StockLogView(APIView):
    permission_classes = [MODULE, HasPermission("dept.stock_log.view")]

    @extend_schema(responses=s.StockMovementSerializer(many=True))
    def get(self, request):
        return Response(s.StockMovementSerializer(scoping.stock_log()[:200],
                                                  many=True).data)


# -- feedback ------------------------------------------------------------------
class FeedbackListView(APIView):
    permission_classes = [MODULE, HasPermission("dept.feedback.access")]

    @extend_schema(responses=s.FeedbackSerializer(many=True))
    def get(self, request):
        rows = scoping.feedback_for(_actor(request))[:200]
        return Response(s.FeedbackSerializer(rows, many=True).data)

    @extend_schema(request=s.FeedbackWriteSerializer,
                   responses=s.FeedbackSerializer)
    def post(self, request):
        payload = s.FeedbackWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        created = feedback_service.submit(actor=_actor(request),
                                          **payload.validated_data)
        return Response(s.FeedbackSerializer(created).data,
                        status=status.HTTP_201_CREATED)


class FeedbackMoveView(APIView):
    permission_classes = [MODULE, HasPermission("dept.feedback.review",
                                                "dept.feedback.resolve")]

    @extend_schema(request=s.FeedbackMoveSerializer,
                   responses=s.FeedbackSerializer)
    def post(self, request, pk):
        payload = s.FeedbackMoveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        moved = feedback_service.move(feedback_id=pk, actor=_actor(request),
                                      **payload.validated_data)
        return Response(s.FeedbackSerializer(moved).data)
