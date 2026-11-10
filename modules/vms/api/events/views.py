"""Event endpoints (lane G). Thin: parse, call services/bulk_events.py, shape the response."""
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api.events import serializers as s
from modules.vms.models import EventBatch
from modules.vms.selectors import events as sel
from modules.vms.services import bulk_events as svc

MODULE = HasModuleGrant("vms")

LIST_LIMIT = 500


def _event(ev) -> dict:
    return {"id": ev.pk, "name": ev.name, "organizer": ev.organizer,
            "valid_from": ev.valid_from, "valid_until": ev.valid_until, "status": ev.status,
            "slots": ev.slots, "fast_lane": ev.fast_lane,
            "walkin_rate_limit": ev.walkin_rate_limit,
            "zone_ids": sorted(ev.zones.values_list("pk", flat=True)),
            "created_by_user_id": ev.created_by_user_id}


def _attendee(a) -> dict:
    return {"id": a.pk, "name": a.name, "email": a.email, "phone": a.phone,
            "id_doc_type": a.id_doc_type, "slot_start": a.slot_start, "slot_end": a.slot_end,
            "pass_id": a.visit_pass_id, "status": a.status}


def _get(pk) -> EventBatch:
    ev = EventBatch.objects.filter(pk=pk).first()
    if ev is None:
        raise NotFoundError("Event not found.")
    return ev


def _kwargs(data) -> dict:
    out = dict(data)
    if "slots" in out:
        out["slots"] = [{"start": x["start"], "end": x["end"], "capacity": x.get("capacity")}
                        for x in out["slots"]]
    return out


class EventListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]

    def get(self, request):
        rows = sel.events(status=request.query_params.get("status"))[:LIST_LIMIT]
        return Response([_event(e) for e in rows])

    def post(self, request):
        ser = s.EventWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ev = svc.create_event(admin_actor=request.principal, **_kwargs(ser.validated_data))
        return Response(_event(ev), status=201)


class EventDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]

    @extend_schema(operation_id="vms_events_detail")
    def get(self, request, pk):
        return Response(_event(_get(pk)))

    def patch(self, request, pk):
        ser = s.EventWriteSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ev = svc.update_event(admin_actor=request.principal, event_id=pk,
                              **_kwargs(ser.validated_data))
        return Response(_event(ev))


class AttendeeListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]

    def get(self, request, pk):
        _get(pk)
        rows = sel.attendees(pk, status=request.query_params.get("status"))[:5000]
        return Response([_attendee(a) for a in rows])


class AttendeeUploadView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        ser = s.UploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        report = svc.upload_attendees(admin_actor=request.principal, event_id=pk,
                                      file=ser.validated_data["file"])
        return Response(report.as_dict(), status=201 if report.accepted else 200)


class AttendeeDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]
    parser_classes = [JSONParser, FormParser]

    def delete(self, request, pk, aid):
        ser = s.ReasonSerializer(data=request.data or request.query_params)
        ser.is_valid(raise_exception=True)
        att = svc.revoke_attendee(admin_actor=request.principal, event_id=pk, attendee_id=aid,
                                  reason=ser.validated_data["reason"])
        return Response(_attendee(att))


class ApproveView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]

    def post(self, request, pk):
        ser = s.ApproveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(svc.approve_batch(admin_actor=request.principal, event_id=pk,
                                          attendee_ids=ser.validated_data["attendee_ids"]))


class CancelView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage")]

    def post(self, request, pk):
        ser = s.ReasonSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(svc.cancel_event(admin_actor=request.principal, event_id=pk,
                                         reason=ser.validated_data["reason"]))


class AttendanceView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage", "vms.monitor.view")]

    def get(self, request, pk):
        return Response(sel.attendance(_get(pk)))


class ThroughputView(APIView):
    permission_classes = [MODULE, HasPermission("vms.event.manage", "vms.monitor.view")]

    def get(self, request, pk):
        raw = request.query_params.get("bucket_minutes", "5")
        if not raw.isdigit() or not 1 <= int(raw) <= 60:
            raise BadRequestError("bucket_minutes must be 1-60.", code="invalid_bucket")
        return Response(sel.throughput(_get(pk), int(raw)))


class FastLaneManifestView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.sync")]

    def get(self, request, pk):
        ev = _get(pk)
        if not ev.fast_lane:
            raise ConflictError("Fast-lane scanning is not enabled for this event.",
                                code="fast_lane_disabled")
        return Response({"event_id": ev.pk, "passes": sel.fast_lane_manifest(ev)})
