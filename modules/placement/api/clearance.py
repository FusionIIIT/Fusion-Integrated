"""Post-offer obligations (rules 22 and 24)."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.placement.api import serializers as s
from modules.placement.models import PlacementRecord
from modules.placement.selectors import scoping
from modules.placement.services import clearance as service
from modules.placement.services import records as record_service

MODULE = HasModuleGrant("placement")
P_VIEW_SELF = "placement.own_application.view"
P_MANAGE = "placement.record.manage"
#: Reading the worklist is a report; recording a placement is not.
P_VIEW_REPORTS = "placement.report.view"


def _actor(request):
    return getattr(request, "principal", None)


def _own_records(user_id: int):
    return (PlacementRecord.objects
            .filter(user_id=user_id, is_active=True)
            .select_related("company").order_by("-created_at"))


@extend_schema(responses=s.PlacementRecordDetailSerializer(many=True))
class MyRecordsView(APIView):
    """The caller's own placements and what each still owes."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        rows = _own_records(_actor(request).user_id)
        return Response({
            "results": s.PlacementRecordDetailSerializer(rows, many=True).data})


@extend_schema(responses=s.ClearanceSerializer)
class MyClearanceView(APIView):
    """Rule 24, for the caller. Scoped by the credential, never by a parameter."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        user_id = _actor(request).user_id
        verdict = service.no_dues_clearance(user_id=user_id)
        return Response({"user_id": user_id, "cleared": verdict.cleared,
                         "blocking": list(verdict.blocking),
                         "message": verdict.message})


@extend_schema(request=s.SubmitOfferLetterSerializer,
               responses=s.PlacementRecordDetailSerializer)
class SubmitOfferLetterView(APIView):
    """Rule 24 — attach the signed copy to release the no-dues hold."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    throttle_scope = "placement_write"

    def post(self, request, pk):
        payload = s.SubmitOfferLetterSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = service.submit_offer_letter(
            record_id=pk, user_id=_actor(request).user_id,
            document_id=payload.validated_data["document_id"])
        return Response(s.PlacementRecordDetailSerializer(record).data)


@extend_schema(request=s.NotJoiningSerializer,
               responses=s.NotJoiningResultSerializer)
class NotJoiningView(APIView):
    """Rule 22 — telling the Placement Cell you will not join."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    throttle_scope = "placement_write"

    def post(self, request, pk):
        payload = s.NotJoiningSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record, verdict = service.declare_not_joining(
            record_id=pk, user_id=_actor(request).user_id,
            reason=payload.validated_data["reason"])
        return Response({
            "record": s.PlacementRecordDetailSerializer(record).data,
            "accepted": verdict.accepted, "is_late": verdict.is_late,
            "message": verdict.message,
        })


@extend_schema(responses=s.PlacementRecordDetailSerializer(many=True))
class OutstandingLettersView(APIView):
    """The office's worklist: placed students who still owe a letter."""

    permission_classes = [MODULE, HasPermission(P_VIEW_REPORTS, P_MANAGE)]

    def get(self, request):
        rows = service.outstanding(season=request.query_params.get("season"))
        return Response({
            "results": s.PlacementRecordDetailSerializer(rows, many=True).data})


@extend_schema(request=s.OffCampusRecordSerializer,
               responses={201: s.PlacementRecordDetailSerializer})
class OffCampusRecordView(APIView):
    """Rules 5 and 24 — an off-campus placement the Cell was told about."""

    permission_classes = [MODULE, HasPermission(P_MANAGE)]
    throttle_scope = "placement_write"

    def post(self, request):
        payload = s.OffCampusRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = service.record_off_campus(actor=_actor(request),
                                           **payload.validated_data)
        return Response(s.PlacementRecordDetailSerializer(record).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(
    parameters=[
        OpenApiParameter("season", str, description="Placement season, for example 2026-27."),
        OpenApiParameter("user_id", int, description="One person's records."),
    ],
    examples=[OpenApiExample("One record", response_only=True, value={
        "id": 7, "user_id": 4021, "company": {"id": 3, "name": "Acme"},
        "season": "2026-27", "source": "campus", "kind": "fte",
        "ctc_lpa": "12.00", "is_active": True,
        "created_at": "2026-11-02T10:00:00Z", "updated_at": "2026-11-02T10:00:00Z"})])
class OfficeRecordsView(generics.ListAPIView):
    """Every placement record the office may maintain (PC-UC-010, PC-AFR-030)."""

    serializer_class = s.OfficeRecordSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_REPORTS, P_MANAGE)]

    def get_queryset(self):
        rows = scoping.placement_records_for(_actor(self.request))
        params = self.request.query_params
        if params.get("season"):
            rows = rows.filter(policy__season=params["season"])
        if params.get("user_id"):
            try:
                rows = rows.filter(user_id=int(params["user_id"]))
            except ValueError as exc:
                raise BadRequestError("user_id must be a number.",
                                      code="invalid_filter") from exc
        return rows.order_by("-created_at")


class RecordCorrectionView(APIView):
    """A TPO correction to one record; the record's history is kept (PC-BR-029)."""

    permission_classes = [MODULE, HasPermission(P_MANAGE)]
    throttle_scope = "placement_record_write"

    @extend_schema(
        request=s.RecordCorrectionSerializer, responses=s.OfficeRecordSerializer,
        examples=[
            OpenApiExample("Correct the package", request_only=True, value={
                "reason": "The company revised the offer letter.", "ctc_lpa": "14.50"}),
            OpenApiExample("Corrected", response_only=True, value={
                "id": 7, "user_id": 4021, "company": {"id": 3, "name": "Acme"},
                "season": "2026-27", "source": "campus", "kind": "fte",
                "ctc_lpa": "14.50", "is_active": True,
                "created_at": "2026-11-02T10:00:00Z",
                "updated_at": "2026-11-09T09:30:00Z"})])
    def patch(self, request, pk):
        payload = s.RecordCorrectionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = record_service.correct(record_id=pk, actor=_actor(request),
                                        **payload.validated_data)
        return Response(s.OfficeRecordSerializer(record).data)


@extend_schema(
    responses=s.RecordRevisionSerializer(many=True),
    examples=[OpenApiExample("One correction", response_only=True, value={
        "results": [{"id": 1, "by_user_id": 62,
                     "reason": "The company revised the offer letter.",
                     "before": {"ctc_lpa": "12.00", "kind": "fte", "is_active": True},
                     "after": {"ctc_lpa": "14.50", "kind": "fte", "is_active": True},
                     "created_at": "2026-11-09T09:30:00Z"}]})])
class RecordRevisionsView(APIView):
    """What a record said before each correction (PC-UC-010 step 4)."""

    permission_classes = [MODULE, HasPermission(P_VIEW_REPORTS, P_MANAGE)]

    def get(self, request, pk):
        record = scoping.placement_records_for(_actor(request)).filter(pk=pk).first()
        if record is None:
            raise NotFoundError("No such placement record.")
        rows = record.revisions.order_by("-created_at")
        return Response({
            "results": s.RecordRevisionSerializer(rows, many=True).data})
