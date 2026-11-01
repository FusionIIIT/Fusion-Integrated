"""DRF ViewSets and endpoints for VMS."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from modules.vms.api.serializers import (
    VisitRequestSerializer,
    PreRegisterInputSerializer,
    HostDecisionInputSerializer,
    VisitorPassSerializer,
    GateValidationInputSerializer,
    GateCheckoutInputSerializer,
    VisitLogSerializer,
    CampusGateSerializer,
)
from modules.vms.services.operations import (
    submit_pre_registration,
    record_host_decision,
    validate_and_check_in_at_gate,
    check_out_at_gate,
)
from modules.vms.selectors.queries import (
    get_all_requests,
    get_pending_requests_for_host,
    get_active_passes,
    get_active_on_site_visits,
    get_all_campus_gates,
)
from modules.vms.contracts import (
    PreRegisterDTO,
    HostDecisionDTO,
    GateValidationDTO,
    GateCheckoutDTO,
)
from modules.vms.domain.errors import VMSDomainError


class PreRegisterView(APIView):
    """VMS-B-01 PreRegistrationBoundary: Register a new visit."""
    def post(self, request):
        ser = PreRegisterInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dto = PreRegisterDTO(**ser.validated_data)
        try:
            req_obj = submit_pre_registration(dto)
            return Response(VisitRequestSerializer(req_obj).data, status=status.HTTP_201_CREATED)
        except VMSDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        qs = get_all_requests()
        return Response(VisitRequestSerializer(qs, many=True).data)


class HostPendingRequestsView(APIView):
    """VMS-B-02 HostDecisionBoundary: Fetch pending requests for host."""
    def get(self, request):
        user_id = request.user.id if request.user and request.user.is_authenticated else int(request.query_params.get("user_id", 1))
        qs = get_pending_requests_for_host(user_id)
        return Response(VisitRequestSerializer(qs, many=True).data)


class HostDecisionView(APIView):
    """VMS-B-02 HostDecisionBoundary: Decide visit request."""
    def post(self, request, request_id):
        ser = HostDecisionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = request.user.id if request.user and request.user.is_authenticated else int(request.data.get("user_id", 1))
        dto = HostDecisionDTO(
            request_id=request_id,
            host_id=user_id,
            outcome=ser.validated_data["outcome"],
            allowed_start=ser.validated_data.get("allowed_start"),
            allowed_end=ser.validated_data.get("allowed_end"),
            permitted_zones=ser.validated_data.get("permitted_zones"),
            special_instructions=ser.validated_data.get("special_instructions", ""),
        )
        try:
            decision, pass_obj = record_host_decision(dto)
            return Response({
                "decision_id": decision.decision_id,
                "outcome": decision.outcome,
                "pass": VisitorPassSerializer(pass_obj).data if pass_obj else None,
            })
        except VMSDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class GateValidationView(APIView):
    """VMS-B-03 GateValidationBoundary: Check-in validation at gate."""
    def post(self, request):
        ser = GateValidationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verifier_id = request.user.id if request.user and request.user.is_authenticated else 1
        dto = GateValidationDTO(
            credential_data=ser.validated_data["credential_data"],
            gate_id=ser.validated_data["gate_id"],
            verifier_id=verifier_id,
            verifier_notes=ser.validated_data.get("verifier_notes", ""),
        )
        verdict = validate_and_check_in_at_gate(dto)
        return Response({
            "allowed": verdict.allowed,
            "reason": verdict.reason,
            "visitor_name": verdict.visitor_name,
            "pass_id": verdict.pass_id,
            "pass_status": verdict.pass_status,
            "permitted_zones": verdict.permitted_zones,
            "visit_id": verdict.visit_id,
        }, status=status.HTTP_200_OK if verdict.allowed else status.HTTP_403_FORBIDDEN)


class GateCheckoutView(APIView):
    """VMS-B-04 GateCheckoutBoundary: Checkout at gate."""
    def post(self, request):
        ser = GateCheckoutInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        verifier_id = request.user.id if request.user and request.user.is_authenticated else 1
        dto = GateCheckoutDTO(
            pass_id=ser.validated_data["pass_id"],
            gate_id=ser.validated_data["gate_id"],
            verifier_id=verifier_id,
            verifier_notes=ser.validated_data.get("verifier_notes", ""),
        )
        try:
            visit_log = check_out_at_gate(dto)
            return Response(VisitLogSerializer(visit_log).data)
        except VMSDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class ActivePassesView(APIView):
    """List all currently active passes."""
    def get(self, request):
        passes = get_active_passes()
        return Response(VisitorPassSerializer(passes, many=True).data)


class ActiveVisitsView(APIView):
    """List all on-site visitors."""
    def get(self, request):
        logs = get_active_on_site_visits()
        return Response(VisitLogSerializer(logs, many=True).data)


class CampusGatesView(APIView):
    """List operational campus gates."""
    def get(self, request):
        gates = get_all_campus_gates()
        return Response(CampusGateSerializer(gates, many=True).data)
