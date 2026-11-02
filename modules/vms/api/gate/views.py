"""Gate endpoints. Thin: parse, call services/gate.py, shape the response."""
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.vms.api.gate import serializers as s
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import gate as gate_svc
from modules.vms.services import legacy_flow, offline_sync, zone_access
from modules.vms.services.common import authz

LIST_LIMIT = 200


def _failures(failures):
    return s.FailureSerializer(failures, many=True).data


def result_response(res, ok_detail="Checked in."):
    """403 for a denial or unknown pass, 200 otherwise (BW-VMS-09)."""
    if res.outcome == gate_svc.UNKNOWN:
        return Response({"detail": "Pass not found.", "code": "unknown_credential",
                         "failures": [], "override_eligible": False}, status=403)
    if res.outcome == gate_svc.DENIED:
        return Response({
            "detail": res.failures[0].message, "code": res.failures[0].code,
            "failures": _failures(res.failures), "override_eligible": res.override_eligible,
            "visit_log_id": res.log.pk}, status=403)
    vr = res.visit_request
    return Response({
        "detail": ok_detail, "visit_request_id": vr.pk, "visit_log_id": res.log.pk,
        "visitor_name": vr.visitor.full_name, "vip_override": res.vip_override})


class GateValidateView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = s.GateValidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        res = gate_svc.validate_and_check_in(
            security_actor=request.principal, credential=ser.credential(),
            gate_id=d["gate_id"], zone_id=d.get("zone_id"), device_id=d["device_id"])
        return result_response(res)


class GateCheckoutView(APIView):
    """Legacy route, kept as is until lane D's visit/check-out supersedes it."""
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = s.GateCheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        legacy_flow.gate_checkout(actor=request.principal,
                                  qr_token=ser.validated_data["qr_token"])
        return Response({"detail": "Checked out."})


class GateOverrideView(APIView):
    permission_classes = [HasPermission("vms.gate.override")]

    def post(self, request):
        ser = s.OverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        res = gate_svc.override(admin_actor=request.principal, **ser.validated_data)
        return result_response(res, "Checked in by override.")


class EscalationCreateView(APIView):
    permission_classes = [HasPermission("vms.gate.escalate")]

    def post(self, request):
        ser = s.EscalationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        esc = gate_svc.escalate(security_actor=request.principal, **ser.validated_data)
        return Response({"id": esc.pk, "status": esc.status}, status=201)


class EscalationResolveView(APIView):
    permission_classes = [HasPermission("vms.gate.override")]

    def post(self, request, pk):
        ser = s.NoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        esc = gate_svc.resolve_escalation(admin_actor=request.principal, escalation_id=pk,
                                          note=ser.validated_data["note"])
        return Response({"id": esc.pk, "status": esc.status})


class ManualEntryView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request):
        ser = s.ManualEntrySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        res = gate_svc.record_manual_entry(security_actor=request.principal,
                                           **ser.validated_data)
        if res.outcome == "checked_out":
            return Response({"detail": "Checked out.", "visit_log_id": res.log.pk})
        return result_response(res, "Entry recorded.")


class DenialListView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def get(self, request):
        authz.require_role(request.principal, "security")
        status = request.query_params.get("status", "open")
        rows = gate_sel.denials(request.principal.user_id, status)[:LIST_LIMIT]
        return Response({"results": s.DenialSerializer(rows, many=True).data})


class AlertListView(APIView):
    permission_classes = [HasPermission("vms.monitor.view")]

    def get(self, request):
        authz.require_role(request.principal, "security")
        rows = gate_sel.alerts(request.principal.user_id,
                               status=request.query_params.get("status"),
                               kind=request.query_params.get("kind"))[:LIST_LIMIT]
        return Response({"results": s.AlertSerializer(rows, many=True).data})


class AlertHandleView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    def post(self, request, pk):
        ser = s.AlertHandleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        alert = zone_access.handle_alert(actor=request.principal, alert_id=pk,
                                         **ser.validated_data)
        return Response(s.AlertSerializer(alert).data)


class SyncView(APIView):
    permission_classes = [HasPermission("vms.gate.sync")]

    def post(self, request):
        ser = s.SyncSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        events = [{**e, "event": str(e["event"])} for e in d["events"]]
        out = offline_sync.sync(security_actor=request.principal, gate_id=d["gate_id"],
                                events=events)
        return Response(out)


class CachedRosterView(APIView):
    permission_classes = [HasPermission("vms.gate.sync")]

    def get(self, request):
        try:
            gate_id = int(request.query_params.get("gate_id", ""))
        except ValueError:
            raise BadRequestError("gate_id is required.") from None
        rows = offline_sync.cached_roster(security_actor=request.principal, gate_id=gate_id)
        return Response({"results": rows})
