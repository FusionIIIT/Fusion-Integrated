"""Emergency muster endpoints. Thin: parse, call services/muster.py, shape."""
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.vms.api.muster import serializers as s
from modules.vms.services import muster as svc

LIST_LIMIT = 2000


def _shape(muster) -> dict:
    return {**s.MusterSerializer(muster).data, "counts": svc.counts(muster),
            "reason": (muster.summary or {}).get("reason", "")}


class MusterTriggerView(APIView):
    permission_classes = [HasPermission("vms.muster.trigger")]

    def post(self, request):
        ser = s.TriggerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        muster = svc.trigger(actor=request.principal, reason=ser.validated_data["reason"])
        return Response(_shape(muster), status=201)


class MusterCurrentView(APIView):
    permission_classes = [HasPermission("vms.monitor.view")]

    def get(self, request):
        muster = svc.current_for(actor=request.principal)
        return Response({"muster": _shape(muster) if muster else None})


class MusterDetailView(APIView):
    permission_classes = [HasPermission("vms.monitor.view")]

    def get(self, request, pk):
        return Response(_shape(svc.get(actor=request.principal, muster_id=pk)))


class MusterRosterView(APIView):
    permission_classes = [HasPermission("vms.monitor.view")]

    def get(self, request, pk):
        status = request.query_params.get("status") or None
        if status and status not in ("unaccounted", "accounted", "evacuated"):
            raise BadRequestError("Unknown status filter.")
        rows = svc.roster_entries(actor=request.principal, muster_id=pk, status=status)
        return Response({"count": len(rows),
                         "results": s.RosterEntrySerializer(rows[:LIST_LIMIT], many=True).data})


class RollCallView(APIView):
    permission_classes = [HasPermission("vms.muster.rollcall")]

    def post(self, request, pk):
        ser = s.RollCallSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(svc.roll_call(actor=request.principal, muster_id=pk,
                                      **ser.validated_data))


class BulkRollCallView(APIView):
    permission_classes = [HasPermission("vms.muster.rollcall")]

    def post(self, request, pk):
        ser = s.BulkRollCallSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(svc.bulk_roll_call(
            actor=request.principal, muster_id=pk,
            marks=[dict(m) for m in ser.validated_data["marks"]]))


class ReconcileView(APIView):
    permission_classes = [HasPermission("vms.muster.rollcall")]

    def post(self, request, pk):
        ser = s.ReconcileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(svc.reconcile_cached(
            actor=request.principal, muster_id=pk,
            entries=[dict(e) for e in ser.validated_data["entries"]]))


class CloseView(APIView):
    permission_classes = [HasPermission("vms.muster.trigger")]

    def post(self, request, pk):
        ser = s.CloseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        muster = svc.close(actor=request.principal, muster_id=pk, **ser.validated_data)
        return Response({**_shape(muster), "summary": muster.summary})


class ReportView(APIView):
    permission_classes = [HasPermission("vms.monitor.view")]

    def get(self, request, pk):
        return Response(svc.report(actor=request.principal, muster_id=pk))


class ReportCsvView(APIView):
    permission_classes = [HasPermission("vms.report.export")]

    def get(self, request, pk):
        name, text = svc.report_csv(actor=request.principal, muster_id=pk)
        resp = HttpResponse(text, content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{name}"'
        return resp
