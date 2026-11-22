"""API views for VMS module."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vms.api import serializers as s
from modules.vms.domain.state_machine import (
    InvalidStateTransitionError,
    MissingJustificationError,
)
from modules.vms.domain.validation import ValidationError
from modules.vms.selectors import (
    get_dashboard_metrics,
    get_latest_muster_roster,
    get_live_onsite_visitors,
    get_muster_summary,
    get_pass_by_id,
    get_visit_by_id,
    list_audit_logs,
    list_blacklist_entries,
    list_policies,
    list_visits_scoped,
)
from modules.vms.services import (
    BlacklistViolationError,
    DuplicateVisitError,
    add_to_blacklist,
    bulk_register_visitors,
    check_in_visitor,
    check_out_visitor,
    contingency_approve,
    create_access_policy,
    create_pre_authorization,
    decide_visit_request,
    extend_visit,
    grant_zone_elevation,
    manual_gate_override,
    offline_batch_sync,
    pre_register_visit,
    publish_access_policy,
    record_roll_call,
    safe_list_entry,
    terminate_visit,
    trigger_emergency_muster,
    validate_pass_at_gate,
    validate_zone_access,
    walk_in_register,
)

MODULE = HasModuleGrant("vms")


def _get_caller_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None):
        return int(principal.user_id)
    user = getattr(request, "user", None)
    if user and getattr(user, "pk", None):
        return int(user.pk)
    return 1


def _get_caller_roles(request) -> list[str]:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "roles"):
        return list(principal.roles)
    return ["Admin"]


class PreRegisterView(APIView):
    permission_classes = [HasPermission("vms.visit.preregister")]

    @extend_schema(request=s.PreRegisterInputSerializer, responses={201: s.VisitRequestSerializer})
    def post(self, request):
        serializer = s.PreRegisterInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            visit = pre_register_visit(
                name=d["name"],
                email=d["email"],
                phone=d["phone"],
                host_id=d["host_id"],
                purpose=d["purpose"],
                scheduled_start=d["scheduled_start"],
                scheduled_end=d["scheduled_end"],
                id_document_type=d.get("id_document_type", "AADHAAR"),
                id_document_number=d["id_document_number"],
                organization=d.get("organization", ""),
                access_zones=d.get("access_zones", ["Main Gate"]),
                is_urgent_exception=d.get("is_urgent_exception", False),
                external_event_ref=d.get("external_event_ref", ""),
            )
            return Response(s.VisitRequestSerializer(visit).data, status=status.HTTP_201_CREATED)
        except DuplicateVisitError as e:
            raise ConflictError(str(e)) from e
        except (BlacklistViolationError, PermissionError) as e:
            raise ConflictError(str(e)) from e
        except (ValidationError, ValueError) as e:
            raise BadRequestError(str(e)) from e


class WalkInView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.validate")]

    @extend_schema(request=s.WalkInInputSerializer, responses={201: s.VisitRequestSerializer})
    def post(self, request):
        serializer = s.WalkInInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            visit = walk_in_register(
                name=d["name"],
                email=d["email"],
                phone=d["phone"],
                host_id=d["host_id"],
                purpose=d["purpose"],
                id_document_type=d.get("id_document_type", "AADHAAR"),
                id_document_number=d["id_document_number"],
                operator_id=_get_caller_id(request),
                organization=d.get("organization", ""),
                duration_hours=d.get("duration_hours", 4),
                auto_approve=d.get("auto_approve", False),
            )
            return Response(s.VisitRequestSerializer(visit).data, status=status.HTTP_201_CREATED)
        except (BlacklistViolationError, PermissionError) as e:
            raise ConflictError(str(e)) from e
        except ValueError as e:
            raise BadRequestError(str(e)) from e


class BulkRegisterView(APIView):
    permission_classes = [MODULE, HasPermission("vms.bulk.manage")]

    @extend_schema(
        request=s.BulkRegisterInputSerializer, responses={201: s.VisitRequestSerializer(many=True)}
    )
    def post(self, request):
        serializer = s.BulkRegisterInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            visits = bulk_register_visitors(
                records=d["records"],
                host_id=d["host_id"],
                purpose=d["purpose"],
                scheduled_start=d["scheduled_start"],
                scheduled_end=d["scheduled_end"],
                external_event_ref=d.get("external_event_ref", ""),
            )
            return Response(
                s.VisitRequestSerializer(visits, many=True).data, status=status.HTTP_201_CREATED
            )
        except (KeyError, ValueError, ValidationError) as e:
            raise BadRequestError(str(e)) from e


class VisitListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.view")]

    @extend_schema(responses={200: s.VisitRequestSerializer(many=True)})
    def get(self, request):
        user_id = _get_caller_id(request)
        roles = _get_caller_roles(request)
        status_filter = request.query_params.get("status")
        host_id = request.query_params.get("host_id")
        search = request.query_params.get("search")

        visits = list_visits_scoped(
            user_id=user_id,
            roles=roles,
            status=status_filter,
            host_id=int(host_id) if host_id else None,
            search=search,
        )
        return Response(s.VisitRequestSerializer(visits, many=True).data)


class VisitDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.view")]

    @extend_schema(responses={200: s.VisitRequestSerializer})
    def get(self, request, pk: int):
        visit = get_visit_by_id(pk)
        if not visit:
            raise NotFoundError(f"Visit #{pk} not found.")
        return Response(s.VisitRequestSerializer(visit).data)


class VisitDecideView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.decide")]

    @extend_schema(request=s.DecisionInputSerializer, responses={200: s.VisitRequestSerializer})
    def post(self, request, pk: int):
        serializer = s.DecisionInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            caller_id = _get_caller_id(request)
            visit = get_visit_by_id(pk)
            if not visit:
                raise NotFoundError(f"Visit #{pk} not found.")
            effective_host_id = (
                visit.host_id if "Admin" in _get_caller_roles(request) else caller_id
            )

            updated = decide_visit_request(
                visit_id=pk,
                host_id=effective_host_id,
                decision=d["decision"],
                reason=d.get("reason", ""),
            )
            return Response(s.VisitRequestSerializer(updated).data)
        except PermissionError as e:
            raise PermissionDeniedError(str(e)) from e
        except (MissingJustificationError, ValueError) as e:
            raise BadRequestError(str(e)) from e
        except InvalidStateTransitionError as e:
            raise ConflictError(str(e)) from e


class VisitContingencyApproveView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.decide")]

    @extend_schema(request=s.ContingencyInputSerializer, responses={200: s.VisitRequestSerializer})
    def post(self, request, pk: int):
        serializer = s.ContingencyInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        try:
            visit = contingency_approve(
                visit_id=pk,
                admin_id=_get_caller_id(request),
                reason=serializer.validated_data["reason"],
            )
            return Response(s.VisitRequestSerializer(visit).data)
        except InvalidStateTransitionError as e:
            raise ConflictError(str(e)) from e


class VisitExtendView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.decide")]

    @extend_schema(request=s.ExtensionInputSerializer, responses={200: s.VisitRequestSerializer})
    def post(self, request, pk: int):
        serializer = s.ExtensionInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            visit = extend_visit(
                visit_id=pk,
                hours=d["hours"],
                operator_id=_get_caller_id(request),
                reason=d.get("reason", ""),
            )
            return Response(s.VisitRequestSerializer(visit).data)
        except ValueError as e:
            raise BadRequestError(str(e)) from e


class VisitTerminateView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.decide")]

    @extend_schema(request=s.TerminateInputSerializer, responses={200: s.VisitRequestSerializer})
    def post(self, request, pk: int):
        serializer = s.TerminateInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        try:
            visit = terminate_visit(
                visit_id=pk,
                operator_id=_get_caller_id(request),
                reason=serializer.validated_data["reason"],
            )
            return Response(s.VisitRequestSerializer(visit).data)
        except MissingJustificationError as e:
            raise BadRequestError(str(e)) from e
        except InvalidStateTransitionError as e:
            raise ConflictError(str(e)) from e


class PassDetailView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.view")]

    @extend_schema(responses={200: s.PassSerializer})
    def get(self, request, pk: int):
        pass_record = get_pass_by_id(pk)
        if not pass_record:
            raise NotFoundError(f"Pass #{pk} not found.")
        return Response(s.PassSerializer(pass_record).data)


class GateValidateView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.validate")]

    @extend_schema(
        request=s.GateValidateInputSerializer,
        responses={
            200: s.GateValidateResponseSerializer,
            422: s.GateValidateResponseSerializer,
        },
    )
    def post(self, request):
        serializer = s.GateValidateInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        is_valid, message, pass_record = validate_pass_at_gate(
            qr_token=d["qr_token"],
            gate_name=d.get("gate_name", "Main Gate"),
            operator_id=_get_caller_id(request),
        )
        data = {
            "is_valid": is_valid,
            "message": message,
            "pass_record": s.PassSerializer(pass_record).data if pass_record else None,
        }
        res_status = status.HTTP_200_OK if is_valid else status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response(data, status=res_status)


class GateCheckInView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.validate")]

    @extend_schema(request=s.GateCheckInInputSerializer, responses={200: s.GateCheckLogSerializer})
    def post(self, request):
        serializer = s.GateCheckInInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            log = check_in_visitor(
                pass_id=d["pass_id"],
                gate_name=d.get("gate_name", "Main Gate"),
                operator_id=_get_caller_id(request),
            )
            return Response(s.GateCheckLogSerializer(log).data)
        except InvalidStateTransitionError as e:
            raise ConflictError(str(e)) from e


class GateCheckOutView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.validate")]

    @extend_schema(request=s.GateCheckOutInputSerializer, responses={200: s.GateCheckLogSerializer})
    def post(self, request):
        serializer = s.GateCheckOutInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            log = check_out_visitor(
                pass_id=d["pass_id"],
                gate_name=d.get("gate_name", "Main Exit Gate"),
                operator_id=_get_caller_id(request),
            )
            return Response(s.GateCheckLogSerializer(log).data)
        except InvalidStateTransitionError as e:
            raise ConflictError(str(e)) from e


class GateOverrideView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.override")]

    @extend_schema(request=s.GateOverrideInputSerializer, responses={200: s.GateCheckLogSerializer})
    def post(self, request):
        serializer = s.GateOverrideInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            log = manual_gate_override(
                pass_id=d["pass_id"],
                admin_id=_get_caller_id(request),
                reason=d["reason"],
                gate_name=d.get("gate_name", "Main Gate Override"),
            )
            return Response(s.GateCheckLogSerializer(log).data)
        except (MissingJustificationError, ValueError) as e:
            raise BadRequestError(str(e)) from e
        except PermissionError as e:
            raise PermissionDeniedError(str(e)) from e
        except InvalidStateTransitionError as e:
            raise ConflictError(str(e)) from e


class GateOfflineSyncView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.validate")]

    @extend_schema(
        request=s.OfflineSyncInputSerializer,
        responses={200: s.OfflineSyncResponseSerializer},
    )
    def post(self, request):
        serializer = s.OfflineSyncInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        result = offline_batch_sync(serializer.validated_data["events"])
        return Response(result)


class LiveDashboardView(APIView):
    permission_classes = [MODULE, HasPermission("vms.visit.view")]

    @extend_schema(responses={200: s.VisitRequestSerializer(many=True)})
    def get(self, request):
        onsite = get_live_onsite_visitors()
        return Response(s.VisitRequestSerializer(onsite, many=True).data)


class ZoneValidateView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.validate")]

    @extend_schema(
        request=s.ZoneValidateInputSerializer,
        responses={
            200: s.ZoneValidateResponseSerializer,
            403: s.ZoneValidateResponseSerializer,
        },
    )
    def post(self, request):
        serializer = s.ZoneValidateInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        allowed, msg = validate_zone_access(
            pass_id=d["pass_id"],
            zone_name=d["zone_name"],
            operator_id=_get_caller_id(request),
        )
        res_status = status.HTTP_200_OK if allowed else status.HTTP_403_FORBIDDEN
        return Response({"allowed": allowed, "message": msg}, status=res_status)


class ZoneElevateView(APIView):
    permission_classes = [MODULE, HasPermission("vms.gate.override")]

    @extend_schema(
        request=s.ZoneElevateInputSerializer,
        responses={201: s.ZoneElevateResponseSerializer},
    )
    def post(self, request):
        serializer = s.ZoneElevateInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            elevation = grant_zone_elevation(
                pass_id=d["pass_id"],
                zone_name=d["zone_name"],
                hours=d["hours"],
                admin_id=_get_caller_id(request),
                reason=d["reason"],
            )
            return Response(
                {
                    "id": elevation.pk,
                    "status": "ELEVATED",
                    "valid_to": elevation.valid_to,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e


class BlacklistListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.blacklist.manage")]

    @extend_schema(responses={200: s.BlacklistEntrySerializer(many=True)})
    def get(self, request):
        entries = list_blacklist_entries(request.query_params.get("status"))
        return Response(s.BlacklistEntrySerializer(entries, many=True).data)

    @extend_schema(request=s.BlacklistCreateSerializer, responses={201: s.BlacklistEntrySerializer})
    def post(self, request):
        serializer = s.BlacklistCreateSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        entry = add_to_blacklist(
            name=d["name"],
            id_document_type=d["id_document_type"],
            id_document_number=d["id_document_number"],
            phone=d.get("phone", ""),
            reason=d["reason"],
        )
        return Response(s.BlacklistEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class BlacklistSafeListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.blacklist.manage")]

    @extend_schema(request=s.SafeListInputSerializer, responses={200: s.BlacklistEntrySerializer})
    def post(self, request, pk: int):
        serializer = s.SafeListInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        try:
            entry = safe_list_entry(
                entry_id=pk,
                hours=d["hours"],
                admin_id=_get_caller_id(request),
                reason=d["reason"],
            )
            return Response(s.BlacklistEntrySerializer(entry).data)
        except ValueError as e:
            raise BadRequestError(str(e)) from e


class EmergencyMusterView(APIView):
    permission_classes = [MODULE, HasPermission("vms.emergency.trigger")]

    @extend_schema(
        request=s.EmergencyMusterInputSerializer,
        responses={201: s.EmergencyMusterResponseSerializer},
    )
    def post(self, request):
        serializer = s.EmergencyMusterInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        muster_id = trigger_emergency_muster(
            initiated_by_id=_get_caller_id(request),
            assembly_point=serializer.validated_data.get("assembly_point", "Central Ground"),
        )
        return Response(
            {"muster_id": muster_id, "status": "MUSTER_TRIGGERED"},
            status=status.HTTP_201_CREATED,
        )


class EmergencyRosterView(APIView):
    permission_classes = [MODULE, HasPermission("vms.emergency.trigger")]

    @extend_schema(responses={200: s.EmergencyRosterSerializer(many=True)})
    def get(self, request):
        roster = get_latest_muster_roster()
        summary = (
            get_muster_summary(roster[0].muster_id)
            if roster.exists()
            else {"total": 0, "accounted": 0, "unaccounted": 0}
        )
        return Response(
            {
                "summary": summary,
                "roster": s.EmergencyRosterSerializer(roster, many=True).data,
            }
        )


class EmergencyRollCallView(APIView):
    permission_classes = [MODULE, HasPermission("vms.emergency.rollcall")]

    @extend_schema(request=s.RollCallInputSerializer, responses={200: s.EmergencyRosterSerializer})
    def post(self, request, pk: int):
        serializer = s.RollCallInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        entry = record_roll_call(
            roster_id=pk,
            accounted_by_id=_get_caller_id(request),
            status=d.get("status", "ACCOUNTED"),
            notes=d.get("notes", ""),
        )
        return Response(s.EmergencyRosterSerializer(entry).data)


class AnalyticsDashboardView(APIView):
    permission_classes = [MODULE, HasPermission("vms.analytics.view")]

    @extend_schema(responses={200: s.AnalyticsDashboardSerializer})
    def get(self, request):
        return Response(get_dashboard_metrics())


class AuditLogListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.analytics.view")]

    @extend_schema(responses={200: s.GateCheckLogSerializer(many=True)})
    def get(self, request):
        logs = list_audit_logs()
        return Response(s.GateCheckLogSerializer(logs[:100], many=True).data)


class AccessPolicyListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.policy.manage")]

    @extend_schema(responses={200: s.AccessPolicySerializer(many=True)})
    def get(self, request):
        return Response(s.AccessPolicySerializer(list_policies(), many=True).data)

    @extend_schema(request=s.AccessPolicySerializer, responses={201: s.AccessPolicySerializer})
    def post(self, request):
        serializer = s.AccessPolicySerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        policy = create_access_policy(
            version=d["version"],
            visiting_hours_start=d.get("visiting_hours_start", "08:00"),
            visiting_hours_end=d.get("visiting_hours_end", "20:00"),
            max_duration_hours=d.get("max_duration_hours", 12),
            policy_notes=d.get("policy_notes", ""),
        )
        return Response(s.AccessPolicySerializer(policy).data, status=status.HTTP_201_CREATED)


class AccessPolicyPublishView(APIView):
    permission_classes = [MODULE, HasPermission("vms.policy.manage")]

    @extend_schema(request=None, responses={200: s.AccessPolicySerializer})
    def post(self, request, version: int):
        policy = publish_access_policy(version)
        return Response(s.AccessPolicySerializer(policy).data)


class PreAuthorizationListView(APIView):
    permission_classes = [MODULE, HasPermission("vms.preauth.manage")]

    @extend_schema(
        request=s.PreAuthorizationSerializer,
        responses={201: s.PreAuthorizationSerializer},
    )
    def post(self, request):
        serializer = s.PreAuthorizationSerializer(data=request.data)
        if not serializer.is_valid():
            raise BadRequestError(details=serializer.errors)
        d = serializer.validated_data
        preauth = create_pre_authorization(
            host_id=d.get("host_id", _get_caller_id(request)),
            visitor_email=d["visitor_email"],
            visitor_name=d["visitor_name"],
            valid_from=d["valid_from"],
            valid_to=d["valid_to"],
        )
        return Response(s.PreAuthorizationSerializer(preauth).data, status=status.HTTP_201_CREATED)
