"""VMS API Views and Endpoints.
Gated with HasModuleGrant and HasPermission, with @extend_schema annotations.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api import serializers as s
from modules.vms.selectors.scoping import (
    get_visible_alerts_for_principal,
    get_visible_visits_for_principal,
)
from modules.vms.services.gate import (
    execute_check_out,
    reconcile_offline_gate_events,
    verify_qr_and_check_in,
    verify_zone_access,
)
from modules.vms.services.registration import (
    approve_visit,
    reject_visit,
    request_or_create_visit,
)
from modules.vms.services.security import (
    add_to_blacklist,
    trigger_emergency_muster,
)


class VisitListCreateView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit.create")]
    throttle_scope = "vms_register"

    @extend_schema(
        summary="List visible visits",
        responses={200: s.VisitResponseSerializer(many=True)},
    )
    def get(self, request):
        qs = get_visible_visits_for_principal(request.principal)
        data = s.VisitResponseSerializer(qs, many=True).data
        return Response(data)

    @extend_schema(
        summary="Request a new visit or register walk-in",
        request=s.VisitRequestSerializer,
        responses={201: s.VisitResponseSerializer},
    )
    def post(self, request):
        serializer = s.VisitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vdata = serializer.validated_data

        visitor_info = {
            "first_name": vdata["first_name"],
            "last_name": vdata["last_name"],
            "phone": vdata["phone"],
            "email": vdata["email"],
            "id_type": vdata["id_type"],
            "id_number": vdata["id_number"],
            "organization": vdata.get("organization", ""),
        }

        user_id = getattr(request.principal, "user_id", None)
        visit = request_or_create_visit(
            visitor_data=visitor_info,
            host_user_id=vdata["host_user_id"],
            purpose=vdata["purpose"],
            valid_from=vdata["valid_from"],
            valid_to=vdata["valid_to"],
            allowed_zones=vdata.get("allowed_zones"),
            visit_type=vdata.get("visit_type", "pre_registered"),
            is_multi_entry=vdata.get("is_multi_entry", False),
            creator_user_id=user_id,
        )
        return Response(s.VisitResponseSerializer(visit).data, status=status.HTTP_201_CREATED)


class VisitApproveView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit.approve")]
    throttle_scope = "vms_write"

    @extend_schema(
        request=None, summary="Host approves visit", responses={200: s.VisitResponseSerializer}
    )
    def post(self, request, pk: int):
        user_id = getattr(request.principal, "user_id", None) or 1
        visit = approve_visit(visit_id=pk, host_user_id=user_id)
        return Response(s.VisitResponseSerializer(visit).data)


class VisitRejectView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit.approve")]
    throttle_scope = "vms_write"

    @extend_schema(
        request=s.VisitRejectRequestSerializer,
        summary="Host rejects visit",
        responses={200: s.VisitResponseSerializer},
    )
    def post(self, request, pk: int):
        user_id = getattr(request.principal, "user_id", None) or 1
        reason = request.data.get("reason", "Host unavailable")
        visit = reject_visit(visit_id=pk, host_user_id=user_id, reason=reason)
        return Response(s.VisitResponseSerializer(visit).data)


class GateVerifyQRCheckInView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.scan")]
    throttle_scope = "vms_gate"

    @extend_schema(
        summary="Scan QR and check-in visitor",
        request=s.QRScanRequestSerializer,
        responses={200: s.VisitResponseSerializer},
    )
    def post(self, request):
        ser = s.QRScanRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        guard_id = getattr(request.principal, "user_id", None) or 1

        visit = verify_qr_and_check_in(
            qr_code_hash=ser.validated_data["qr_code_hash"],
            guard_user_id=guard_id,
            gate_name=ser.validated_data.get("gate_name", "Main Gate"),
            reader_machine_id=ser.validated_data.get("reader_machine_id", ""),
        )
        return Response(s.VisitResponseSerializer(visit).data)


class GateCheckOutView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.scan")]
    throttle_scope = "vms_gate"

    @extend_schema(
        summary="Check out visitor",
        request=s.CheckOutRequestSerializer,
        responses={200: s.VisitResponseSerializer},
    )
    def post(self, request):
        ser = s.CheckOutRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        guard_id = getattr(request.principal, "user_id", None) or 1

        visit = execute_check_out(
            visit_id=ser.validated_data["visit_id"],
            guard_user_id=guard_id,
            gate_name=ser.validated_data.get("gate_name", "Main Gate"),
        )
        return Response(s.VisitResponseSerializer(visit).data)


class GateZoneVerifyView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.scan")]
    throttle_scope = "vms_gate"

    @extend_schema(
        summary="Verify zone access for visitor",
        request=s.ZoneVerifyRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.ZoneVerifyRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        guard_id = getattr(request.principal, "user_id", None) or 1

        allowed = verify_zone_access(
            visit_id=ser.validated_data["visit_id"],
            requested_zone=ser.validated_data["requested_zone"],
            guard_user_id=guard_id,
        )
        return Response({"allowed": allowed, "zone": ser.validated_data["requested_zone"]})


class GateOfflineSyncView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.scan")]
    throttle_scope = "vms_gate"

    @extend_schema(
        summary="Reconcile offline gate logs",
        request=s.OfflineSyncRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.OfflineSyncRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        guard_id = getattr(request.principal, "user_id", None) or 1

        result = reconcile_offline_gate_events(
            records=ser.validated_data["records"],
            guard_user_id=guard_id,
        )
        return Response(result)


class GateAlertListView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.security.admin")]
    throttle_scope = "vms_read"

    @extend_schema(
        summary="List gate alerts",
        responses={200: s.GateAlertSerializer(many=True)},
    )
    def get(self, request):
        alerts = get_visible_alerts_for_principal(request.principal)
        return Response(s.GateAlertSerializer(alerts, many=True).data)


class BlacklistManageView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.security.admin")]
    throttle_scope = "vms_write"

    @extend_schema(
        summary="Add to blacklist",
        request=s.BlacklistCreateSerializer,
        responses={201: s.BlacklistResponseSerializer},
    )
    def post(self, request):
        ser = s.BlacklistCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        admin_id = getattr(request.principal, "user_id", None)

        entry = add_to_blacklist(
            id_type=ser.validated_data["id_type"],
            id_number=ser.validated_data["id_number"],
            full_name=ser.validated_data["full_name"],
            phone=ser.validated_data.get("phone", ""),
            reason=ser.validated_data["reason"],
            severity=ser.validated_data.get("severity", "critical"),
            added_by=admin_id,
        )
        return Response(s.BlacklistResponseSerializer(entry).data, status=status.HTTP_201_CREATED)


class EmergencyMusterView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.emergency.muster")]
    throttle_scope = "vms_write"

    @extend_schema(
        request=None,
        summary="Trigger emergency muster roll-call",
        responses={201: s.EmergencyMusterSerializer},
    )
    def post(self, request):
        admin_id = getattr(request.principal, "user_id", None) or 1
        muster = trigger_emergency_muster(admin_user_id=admin_id)
        return Response(s.EmergencyMusterSerializer(muster).data, status=status.HTTP_201_CREATED)
