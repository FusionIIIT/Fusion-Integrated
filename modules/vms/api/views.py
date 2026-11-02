"""DRF API ViewSets and operational endpoints for VMS."""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from modules.vms.models.visitors import (
    Visitor,
    BlacklistRecord,
    SafeListRecord,
)
from modules.vms.models.visits import (
    VisitRequest,
    VisitPass,
    VisitLog,
)
from modules.vms.models.access import (
    CampusZone,
    AccessPolicy,
    GateAlert,
)
from modules.vms.models.muster import (
    EmergencyMuster,
    MusterRollCall,
)
from modules.vms.api.serializers import (
    VisitorSerializer,
    VisitorRegistrationSerializer,
    VisitRequestSerializer,
    VisitRequestDecisionSerializer,
    VisitPassSerializer,
    GateCheckInSerializer,
    GateCheckOutSerializer,
    ZoneAccessCheckSerializer,
    ZoneElevationSerializer,
    BlacklistRecordSerializer,
    SafeListRecordSerializer,
    CampusZoneSerializer,
    GateAlertSerializer,
    EmergencyMusterSerializer,
    MusterRollCallSerializer,
    BulkEventUploadSerializer,
)
from modules.vms.services.visitor_service import (
    register_visitor,
    get_anonymized_visitor_record,
)
from modules.vms.services.pass_service import (
    issue_visit_pass,
    extend_pass_duration,
)
from modules.vms.services.visit_service import (
    create_visit_request,
    decide_visit_request,
    terminate_visit_early,
)
from modules.vms.services.gate_service import (
    validate_and_check_in_visitor,
    check_out_visitor,
)
from modules.vms.services.access_service import (
    validate_zone_access,
    grant_temporary_zone_elevation,
)
from modules.vms.services.muster_service import (
    start_emergency_muster,
    update_muster_roll_call,
    audit_muster_overstay_evictions,
    complete_emergency_muster,
)
from modules.vms.services.event_service import (
    process_bulk_event_attendees,
    process_event_checkout,
)
from modules.vms.services.exceptions import VMSDomainException


class VisitorViewSet(viewsets.ModelViewSet):
    """Visitor profile management and privacy-preserving queries."""
    queryset = Visitor.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = VisitorSerializer

    def create(self, request, *args, **kwargs):
        reg_serializer = VisitorRegistrationSerializer(data=request.data)
        reg_serializer.is_valid(raise_exception=True)
        try:
            visitor = register_visitor(**reg_serializer.validated_data)
            return Response(VisitorSerializer(visitor).data, status=status.HTTP_201_CREATED)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="anonymized")
    def anonymized(self, request, pk=None):
        visitor = self.get_object()
        return Response(get_anonymized_visitor_record(visitor))


class VisitRequestViewSet(viewsets.ModelViewSet):
    """Host approval lifecycle for visit requests."""
    queryset = VisitRequest.objects.all().order_by("-created_at")
    serializer_class = VisitRequestSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        visitor_id = data.get("visitor_id")
        visitor = Visitor.objects.filter(id=visitor_id).first()
        if not visitor:
            return Response({"error": "Valid visitor_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        host_user_id = data.get("host_user_id") or getattr(request.user, "user_id", 1001)
        purpose = data.get("purpose", "Official Meeting")
        intended_start = data.get("intended_start", timezone.now())
        intended_end = data.get("intended_end", timezone.now() + timezone.timedelta(hours=4))

        try:
            visit = create_visit_request(
                visitor=visitor,
                host_user_id=int(host_user_id),
                purpose=purpose,
                intended_start=intended_start,
                intended_end=intended_end,
            )
            return Response(VisitRequestSerializer(visit).data, status=status.HTTP_201_CREATED)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        host_user_id = request.query_params.get("host_user_id") or getattr(request.user, "user_id", None)
        qs = VisitRequest.objects.filter(status="pending")
        if host_user_id:
            qs = qs.filter(host_user_id=int(host_user_id))
        return Response(VisitRequestSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request, pk=None):
        visit = self.get_object()
        serializer = VisitRequestDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decided_by = getattr(request.user, "user_id", 1001)

        try:
            decide_visit_request(
                visit=visit,
                decision=serializer.validated_data["decision"],
                decided_by_user_id=decided_by,
                instructions=serializer.validated_data.get("instructions", ""),
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
            )
            return Response(VisitRequestSerializer(visit).data)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="terminate")
    def terminate(self, request, pk=None):
        visit = self.get_object()
        user_id = getattr(request.user, "user_id", 1001)
        reason = request.data.get("reason", "Administrative early termination")
        try:
            terminate_visit_early(visit=visit, terminated_by_user_id=user_id, reason=reason)
            return Response(VisitRequestSerializer(visit).data)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)


class VisitPassViewSet(viewsets.ReadOnlyModelViewSet):
    """Pass inspection and active credential lookups."""
    queryset = VisitPass.objects.all().order_by("-created_at")
    serializer_class = VisitPassSerializer

    @action(detail=False, methods=["get"], url_path="by-qr")
    def by_qr(self, request):
        token = request.query_params.get("qr_code_hash")
        p = VisitPass.objects.filter(qr_code_hash=token).first()
        if not p:
            return Response({"error": "Pass not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(VisitPassSerializer(p).data)


class GateTerminalViewSet(viewsets.ViewSet):
    """Gate terminal operations: scanning, check-in, check-out, and walk-in passes."""

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        serializer = GateCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        security_user_id = getattr(request.user, "user_id", 9999)

        try:
            p = validate_and_check_in_visitor(
                qr_code_hash=serializer.validated_data["qr_code_hash"],
                gate_machine_id=serializer.validated_data["gate_machine_id"],
                security_user_id=security_user_id,
                gate_name=serializer.validated_data["gate_name"],
            )
            return Response(VisitPassSerializer(p).data, status=status.HTTP_200_OK)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        serializer = GateCheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        security_user_id = getattr(request.user, "user_id", 9999)

        try:
            p = check_out_visitor(
                pass_number=serializer.validated_data["pass_number"],
                security_user_id=security_user_id,
                gate_machine_id=serializer.validated_data["gate_machine_id"],
                gate_name=serializer.validated_data["gate_name"],
            )
            return Response(VisitPassSerializer(p).data, status=status.HTTP_200_OK)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="walk-in")
    def walk_in(self, request):
        """Walk-in on-the-spot registration and immediate pass issuance (BR-032)."""
        reg_serializer = VisitorRegistrationSerializer(data=request.data)
        reg_serializer.is_valid(raise_exception=True)
        security_user_id = getattr(request.user, "user_id", 9999)

        try:
            visitor = register_visitor(**reg_serializer.validated_data)
            now = timezone.now()
            visit = VisitRequest.objects.create(
                visitor=visitor,
                host_user_id=security_user_id,
                purpose=request.data.get("purpose", "Walk-in Campus Visit"),
                intended_start=now,
                intended_end=now + timezone.timedelta(hours=4),
                actual_arrival=now,
                status="on_site",
            )
            # BR-032: Default 4 hours walk-in pass
            pass_record = issue_visit_pass(visit=visit, pass_type="walk_in")
            return Response(VisitPassSerializer(pass_record).data, status=status.HTTP_201_CREATED)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)


class ZoneAccessViewSet(viewsets.ViewSet):
    """Zone access scanning and elevation controls."""

    @action(detail=False, methods=["post"], url_path="validate")
    def validate_zone(self, request):
        serializer = ZoneAccessCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = VisitPass.objects.filter(pass_number=serializer.validated_data["pass_number"]).first()
        if not p:
            return Response({"error": "Pass not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            validate_zone_access(
                pass_record=p,
                zone_code=serializer.validated_data["zone_code"],
                gate_machine_id=serializer.validated_data["gate_machine_id"],
                verifier_user_id=getattr(request.user, "user_id", 9999),
            )
            return Response({"status": "granted", "message": "Access Granted"})
        except VMSDomainException as exc:
            return Response({"status": "denied", "error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=["post"], url_path="elevate")
    def elevate_zone(self, request):
        serializer = ZoneElevationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        p = VisitPass.objects.filter(pass_number=serializer.validated_data["pass_number"]).first()
        if not p:
            return Response({"error": "Pass not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            grant_temporary_zone_elevation(
                pass_record=p,
                zone_code=serializer.validated_data["zone_code"],
                granted_by_user_id=getattr(request.user, "user_id", 1001),
                reason=serializer.validated_data["reason"],
            )
            return Response(VisitPassSerializer(p).data)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)


class EmergencyMusterViewSet(viewsets.ModelViewSet):
    """Emergency evacuation muster initiation, roll-call, and final reporting."""
    queryset = EmergencyMuster.objects.all().order_by("-started_at")
    serializer_class = EmergencyMusterSerializer

    def create(self, request, *args, **kwargs):
        user_id = getattr(request.user, "user_id", 9999)
        reason = request.data.get("reason", "Campus Emergency Evacuation")
        muster = start_emergency_muster(initiated_by_user_id=user_id, reason=reason)
        return Response(EmergencyMusterSerializer(muster).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="roster")
    def roster(self, request, pk=None):
        muster = self.get_object()
        entries = muster.roll_calls.all()
        return Response(MusterRollCallSerializer(entries, many=True).data)

    @action(detail=True, methods=["post"], url_path="mark-roll-call")
    def mark_roll_call(self, request, pk=None):
        muster = self.get_object()
        visitor_id = request.data.get("visitor_id")
        call_status = request.data.get("status", "safe")
        user_id = getattr(request.user, "user_id", 9999)
        notes = request.data.get("notes", "")

        try:
            entry = update_muster_roll_call(
                muster=muster,
                visitor_id=int(visitor_id),
                status=call_status,
                checked_by_user_id=user_id,
                notes=notes,
            )
            return Response(MusterRollCallSerializer(entry).data)
        except VMSDomainException as exc:
            return Response({"error": exc.message}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="audit-evictions")
    def audit_evictions(self, request, pk=None):
        """Enforces BR-045: >15 minute muster alerts."""
        muster = self.get_object()
        alerts_count = audit_muster_overstay_evictions(muster)
        return Response({"eviction_alerts_created": alerts_count})

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        muster = self.get_object()
        concluded = complete_emergency_muster(muster)
        return Response(EmergencyMusterSerializer(concluded).data)


class BlacklistViewSet(viewsets.ModelViewSet):
    queryset = BlacklistRecord.objects.all().order_by("-created_at")
    serializer_class = BlacklistRecordSerializer


class SafeListViewSet(viewsets.ModelViewSet):
    queryset = SafeListRecord.objects.all().order_by("-created_at")
    serializer_class = SafeListRecordSerializer


class CampusZoneViewSet(viewsets.ModelViewSet):
    queryset = CampusZone.objects.all().order_by("code")
    serializer_class = CampusZoneSerializer


class GateAlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GateAlert.objects.all().order_by("-created_at")
    serializer_class = GateAlertSerializer


class BulkEventViewSet(viewsets.ViewSet):
    """Bulk event upload and mass pass provisioning (BR-021)."""

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        serializer = BulkEventUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = getattr(request.user, "user_id", 1001)

        try:
            passes = process_bulk_event_attendees(
                event_name=serializer.validated_data["event_name"],
                organizer_user_id=user_id,
                attendees=serializer.validated_data["attendees"],
                duration_hours=serializer.validated_data.get("duration_hours", 8),
                allowed_zones=serializer.validated_data.get("allowed_zones"),
            )
            return Response(VisitPassSerializer(passes, many=True).data, status=status.HTTP_201_CREATED)
        except VMSDomainException as exc:
            return Response({"error": exc.message, "rule_id": exc.rule_id}, status=status.HTTP_400_BAD_REQUEST)
