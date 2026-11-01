"""HTTP layer: parse, scope, delegate, serialise.

Both gates on every view: the module grant, then the permission the action
needs. Querysets come from selectors, so a foreign request is a 404.

Ref: 03_VMS_Use_Case_Specifications_v1.3
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.visitors.api import serializers as s
from modules.visitors.models import (
    AccessPolicy,
    BlacklistEntry,
    VisitRequest,
    ZoneDefinition,
)
from modules.visitors.selectors import queues
from modules.visitors.services import visitor as visitor_service

MODULE = HasModuleGrant("visitors")

P_REGISTER = "visitors.visit.register"
P_VIEW_SELF = "visitors.visit.view_self"
P_HOST_DECIDE = "visitors.visit.host_decide"
P_HOST_VIEW = "visitors.visit.host_view"
P_GATE_OPS = "visitors.gate.operate"
P_GATE_OVERRIDE = "visitors.gate.override"
P_ZONE_VALIDATE = "visitors.zone.validate"
P_ZONE_ELEVATE = "visitors.zone.elevate"
P_ADMIN_DECIDE = "visitors.admin.decide"
P_ADMIN_REPORT = "visitors.admin.report"
P_BLACKLIST = "visitors.blacklist.manage"
P_MUSTER = "visitors.muster.trigger"
P_MUSTER_ROLL = "visitors.muster.roll_call"
P_POLICY = "visitors.policy.manage"
P_TERMINATE = "visitors.visit.terminate"


def _actor(request):
    return getattr(request, "principal", None)


def _get(queryset, pk):
    row = queryset.filter(pk=pk).first()
    if row is None:
        raise NotFoundError("Not found.")
    return row


# --- Visitor views (VMS-UC-010, 011, 012, 030, 031) -------------------------

class PreRegisterView(APIView):
    """VMS-UC-010: pre-register a visit."""
    permission_classes = [MODULE, HasPermission(P_REGISTER)]

    @extend_schema(request=s.PreRegisterSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request):
        payload = s.PreRegisterSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.pre_register_visit(
            _actor(request), **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data, status=201)


class MyVisitsView(generics.ListAPIView):
    """VMS-UC-011: visitor's own visit requests and history."""
    serializer_class = s.VisitRequestSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.my_visit_requests(_actor(self.request))


class VisitDetailView(APIView):
    """VMS-UC-012: access visit/pass detail."""
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request, pk):
        visit = _get(queues.my_visit_requests(_actor(request)), pk)
        return Response(s.VisitRequestSerializer(visit).data)


# --- Host views (VMS-UC-013, 014, 015, 016) ---------------------------------

class HostPendingView(generics.ListAPIView):
    """VMS-UC-013: visits awaiting this host's approval."""
    serializer_class = s.VisitRequestSerializer
    permission_classes = [MODULE, HasPermission(P_HOST_DECIDE)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.host_pending_approvals(_actor(self.request))


class HostDecideView(APIView):
    """VMS-UC-013: approve or reject a visit request."""
    permission_classes = [MODULE, HasPermission(P_HOST_DECIDE)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.decide_visit(
            _actor(request), pk, **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data)


class HostArrivalsView(generics.ListAPIView):
    """VMS-UC-015: visitors currently on site for this host."""
    serializer_class = s.VisitRequestSerializer
    permission_classes = [MODULE, HasPermission(P_HOST_VIEW)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.host_visitor_arrivals(_actor(self.request))


class HostTerminateView(APIView):
    """VMS-UC-016: host terminates a visit early."""
    permission_classes = [MODULE, HasPermission(P_TERMINATE)]

    @extend_schema(request=s.TerminateSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request, pk):
        payload = s.TerminateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.terminate_visit(
            _actor(request), pk, **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data)


# --- Security Personnel views (VMS-UC-017, 018, 020, 021, 022, 028) ---------

class WalkInRegisterView(APIView):
    """VMS-UC-017: register walk-in visitor at gate."""
    permission_classes = [MODULE, HasPermission(P_GATE_OPS)]

    @extend_schema(request=s.WalkInSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request):
        payload = s.WalkInSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.register_walkin(
            _actor(request), **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data, status=201)


class GateValidateView(APIView):
    """VMS-UC-018: validate visitor pass at gate."""
    permission_classes = [MODULE, HasPermission(P_GATE_OPS)]

    @extend_schema(request=s.GateValidationSerializer,
                   responses=s.GateLogSerializer)
    def post(self, request, pk):
        payload = s.GateValidationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        gl = visitor_service.validate_pass_at_gate(
            _actor(request), pk, **payload.validated_data)
        return Response(s.GateLogSerializer(gl).data)


class GateOverrideView(APIView):
    """VMS-UC-019: process manual gate override."""
    permission_classes = [MODULE, HasPermission(P_GATE_OVERRIDE)]

    @extend_schema(request=s.OverrideSerializer,
                   responses=s.GateLogSerializer)
    def post(self, request, pk):
        payload = s.OverrideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        gl = visitor_service.manual_gate_override(
            _actor(request), pk, **payload.validated_data)
        return Response(s.GateLogSerializer(gl).data)


class GateCheckoutView(APIView):
    """VMS-UC-021: check out visitor at gate."""
    permission_classes = [MODULE, HasPermission(P_GATE_OPS)]

    @extend_schema(request=s.CheckoutSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request, pk):
        payload = s.CheckoutSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.checkout_visitor(
            _actor(request), pk, **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data)


class LiveDashboardView(generics.ListAPIView):
    """VMS-UC-022: monitor live visitor dashboard."""
    serializer_class = s.VisitRequestSerializer
    permission_classes = [MODULE, HasPermission(P_GATE_OPS)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.on_site_visitors()


class GateLogsView(generics.ListAPIView):
    """VMS-UC-020: gate log history for a visit."""
    serializer_class = s.GateLogSerializer
    permission_classes = [MODULE, HasPermission(P_GATE_OPS)]

    def get_queryset(self):
        return queues.gate_logs_for_visit(self.kwargs["pk"])


# --- Zone access views (VMS-UC-023, 024, 025) --------------------------------

class ZoneValidateView(APIView):
    """VMS-UC-023: validate zone access."""
    permission_classes = [MODULE, HasPermission(P_ZONE_VALIDATE)]

    @extend_schema(request=s.ZoneAccessSerializer,
                   responses=s.ZoneAccessLogSerializer)
    def post(self, request, pk):
        payload = s.ZoneAccessSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        entry = visitor_service.validate_zone_access(
            _actor(request), pk, **payload.validated_data)
        return Response(s.ZoneAccessLogSerializer(entry).data)


class ZoneElevationView(APIView):
    """VMS-UC-024: grant temporary zone elevation."""
    permission_classes = [MODULE, HasPermission(P_ZONE_ELEVATE)]

    @extend_schema(request=s.ZoneElevationSerializer,
                   responses=s.TemporaryZoneElevationSerializer)
    def post(self, request, pk):
        payload = s.ZoneElevationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        elev = visitor_service.grant_zone_elevation(
            _actor(request), pk, **payload.validated_data)
        return Response(s.TemporaryZoneElevationSerializer(elev).data, status=201)


class ZoneListView(generics.ListAPIView):
    """Zone definitions for reference."""
    serializer_class = s.ZoneDefinitionSerializer
    permission_classes = [MODULE, HasPermission(P_GATE_OPS)]
    queryset = ZoneDefinition.objects.none()

    def get_queryset(self):
        return queues.zone_list()


# --- Admin views (VMS-UC-005, 006, 007, 008, 009, 033, 034, 035, 036) -------

class AdminPendingView(generics.ListAPIView):
    """VMS-UC-033/034/035: visits needing admin decision."""
    serializer_class = s.VisitRequestSerializer
    permission_classes = [MODULE, HasPermission(P_ADMIN_DECIDE)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.admin_pending_approvals()


class AdminDecideView(APIView):
    """Admin approval/rejection (contingency, extension, urgent)."""
    permission_classes = [MODULE, HasPermission(P_ADMIN_DECIDE)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.decide_visit(
            _actor(request), pk, **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data)


class AdminTerminateView(APIView):
    """VMS-UC-036: admin terminates a visit early."""
    permission_classes = [MODULE, HasPermission(P_TERMINATE)]

    @extend_schema(request=s.TerminateSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request, pk):
        payload = s.TerminateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        visit = visitor_service.terminate_visit(
            _actor(request), pk, **payload.validated_data)
        return Response(s.VisitRequestSerializer(visit).data)


class ExtensionView(APIView):
    """VMS-UC-034: request visit extension."""
    permission_classes = [MODULE, HasPermission(P_ADMIN_DECIDE)]

    @extend_schema(request=s.ExtensionSerializer,
                   responses=s.VisitRequestSerializer)
    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        ext = visitor_service.request_extension(
            _actor(request), pk, **payload.validated_data)
        return Response(s.VisitRequestSerializer(ext).data, status=201)


class ReportView(generics.ListAPIView):
    """VMS-UC-007: generate visitor reports and analytics."""
    serializer_class = s.VisitRequestSerializer
    permission_classes = [MODULE, HasPermission(P_ADMIN_REPORT)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.all_visits(
            date_from=self.request.query_params.get("date_from"),
            date_to=self.request.query_params.get("date_to"),
            status=self.request.query_params.get("status"),
        )


class BlacklistView(generics.ListAPIView):
    """VMS-UC-006: blacklist/watchlist registry."""
    serializer_class = s.BlacklistEntrySerializer
    permission_classes = [MODULE, HasPermission(P_BLACKLIST)]
    queryset = BlacklistEntry.objects.none()

    def get_queryset(self):
        return queues.blacklist_entries()


class AccessPolicyView(generics.ListAPIView):
    """VMS-UC-005: access policy configuration."""
    serializer_class = s.AccessPolicySerializer
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    queryset = AccessPolicy.objects.none()

    def get_queryset(self):
        return AccessPolicy.objects.all()


# --- Emergency muster views (VMS-UC-026, 027, 032) --------------------------

class MusterTriggerView(APIView):
    """VMS-UC-026/032: trigger emergency muster."""
    permission_classes = [MODULE, HasPermission(P_MUSTER)]

    @extend_schema(request=s.MusterTriggerSerializer,
                   responses=s.EmergencyMusterSerializer)
    def post(self, request):
        payload = s.MusterTriggerSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        muster = visitor_service.trigger_muster(
            _actor(request), **payload.validated_data)
        return Response(s.EmergencyMusterSerializer(muster).data, status=201)


class MusterListView(generics.ListAPIView):
    """Active emergency musters."""
    serializer_class = s.EmergencyMusterSerializer
    permission_classes = [MODULE, HasPermission(P_MUSTER)]
    queryset = VisitRequest.objects.none()

    def get_queryset(self):
        return queues.active_musters()


class MusterRollCallView(generics.ListAPIView):
    """VMS-UC-027: roll-call entries for a muster."""
    serializer_class = s.MusterRollCallSerializer
    permission_classes = [MODULE, HasPermission(P_MUSTER_ROLL)]

    def get_queryset(self):
        return queues.muster_roll_call(self.kwargs["muster_id"])


class MusterAccountView(APIView):
    """VMS-UC-027: account a visitor during roll-call."""
    permission_classes = [MODULE, HasPermission(P_MUSTER_ROLL)]

    @extend_schema(request=s.RollCallSerializer,
                   responses=s.MusterRollCallSerializer)
    def post(self, request, muster_id, visit_id):
        payload = s.RollCallSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        rc = visitor_service.account_visitor_in_muster(
            _actor(request), muster_id, visit_id,
            **payload.validated_data)
        return Response(s.MusterRollCallSerializer(rc).data)
