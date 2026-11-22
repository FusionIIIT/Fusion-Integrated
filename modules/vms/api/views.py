import csv
import io
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.csv import stream as stream_csv
from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.vms.api.serializers import (
    DecisionSerializer,
    EventControlsSerializer,
    EventGuestImportSerializer,
    EventRecordSerializer,
    GateEscalationSerializer,
    GateOverrideDecisionSerializer,
    IntegrationSerializer,
    ManualVisitLogSerializer,
    OfflineEntrySerializer,
    PolicySerializer,
    PreAuthorizationSerializer,
    RegistrationSerializer,
    RegistryEntrySerializer,
    RoleAssignmentSerializer,
    VipPermissionSerializer,
    VisitExtensionDecisionSerializer,
    VisitRequestSerializer,
    WalkInSerializer,
    ZoneElevationSerializer,
)
from modules.vms.models import (
    AccessPolicyVersion,
    AuditEvent,
    EmergencyMuster,
    EventGuestBatchRow,
    EventRecord,
    GateAttempt,
    IntegrationSetting,
    PreAuthorization,
    RegistryVersion,
    VipPermission,
    VisitorDocument,
    VisitRequest,
    VmsRoleAssignment,
    ZoneAlert,
)
from modules.vms.selectors import reports as report_selectors
from modules.vms.selectors.visits import pending_host_visits, visible_visits
from modules.vms.services import configuration as config_service
from modules.vms.services import policies as policy_service
from modules.vms.services import roles as role_service
from modules.vms.services import security as security_service
from modules.vms.services.visits import (
    authenticate_visitor,
    cache_offline_entry,
    checkout_visit,
    create_preauthorization,
    decide_gate_override,
    decide_visit,
    decide_visit_extension,
    escalate_gate_attempt,
    record_manual_visit_log,
    register_visit,
    register_walk_in,
    revoke_preauthorization,
    terminate_visit,
    validate_pass,
)

logger = logging.getLogger(__name__)


def _with_identity_upload(upload, callback):
    from django.core.exceptions import ValidationError

    from modules.vms.services.document_storage import remove_upload, save_upload

    info = None
    try:
        info = save_upload(upload)
        visit = callback(info)
    except ValidationError as exc:
        if info:
            remove_upload(info["storage_key"])
        raise serializers.ValidationError(exc.messages) from exc
    except Exception:
        if info:
            remove_upload(info["storage_key"])
        raise
    from modules.vms.tasks import scan_visitor_document

    try:
        scan_visitor_document.delay(visit.identity_documents.get().pk)
    except Exception:
        # The bounded beat sweep retries pending rows if the broker is down.
        logger.exception("Could not enqueue visitor identity document scan")
    return visit


def _active_role(request):
    return str(getattr(request.principal, "active_role", "")).casefold()


def _require_operational_role(request, role, *, scope_type="campus", scope_value=""):
    active_role = _active_role(request).replace("_", " ")
    if active_role in {"super admin", "superadmin"}:
        return
    if not role_service.has_active_assignment(
        user_id=request.principal.user_id, role=role, scope_type=scope_type, scope_value=scope_value
    ):
        raise PermissionDeniedError("No active VMS role assignment covers this operation.")


def _require_muster_role(request):
    role = _active_role(request).replace("_", " ")
    if role in {"super admin", "superadmin"}:
        return
    if role == "admin":
        _require_operational_role(request, "admin")
    elif role in {"security personnel", "security"}:
        _require_operational_role(request, "security")
    else:
        raise PermissionDeniedError("Admin or Security Personnel assignment is required.")


def _require_event_view_role(request):
    role = _active_role(request).replace("_", " ")
    if role in {"super admin", "superadmin", "admin"}:
        _require_operational_role(request, "admin")
    elif role in {"security", "security personnel"}:
        _require_operational_role(request, "security")
    else:
        raise PermissionDeniedError("Admin or Security Personnel assignment is required.")


class RegistrationView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "vms_registration"
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data.copy()
        upload = fields.pop("identity_document")
        visit = _with_identity_upload(
            upload, lambda info: register_visit(**fields, document_info=info)
        )
        return Response({"id": visit.pk, "status": visit.status}, status=201)


class PublicHostLookupView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "vms_registration"

    def get(self, request):
        query = str(request.query_params.get("q", "")).strip()
        if len(query) < 2:
            raise BadRequestError(
                "Enter at least two characters to search for a host.", code="host_search_too_short"
            )
        people = [
            *directory.search(query, kind="faculty", limit=15),
            *directory.search(query, kind="staff", limit=15),
        ]
        people.sort(key=lambda person: person.display_name.casefold())
        results = [
            {"user_id": p.user_id, "display_name": p.display_name, "department": p.department}
            for p in people[:20]
        ]
        # Local IAM may not have an ERP directory projection for the synthetic
        # demo identity. Make the seeded demo Host selectable in development;
        # never expose a non-directory identity from a production deployment.
        if (
            settings.DEBUG
            and settings.VMS_DEMO_HOST_DISPLAY_NAME.casefold().find(query.casefold()) >= 0
            and all(p["user_id"] != settings.VMS_DEMO_HOST_USER_ID for p in results)
        ):
            results.append(
                {
                    "user_id": settings.VMS_DEMO_HOST_USER_ID,
                    "display_name": settings.VMS_DEMO_HOST_DISPLAY_NAME,
                    "department": "Demo",
                }
            )
        return Response(results[:20])


class VisitorRequestsView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "vms_visitor_access"

    def get(self, request):
        visitor = authenticate_visitor(request.headers.get("X-Visitor-Token", ""))
        visits = visitor.visit_requests.order_by("-created_at")[:100]
        return Response(VisitRequestSerializer(visits, many=True).data)


class VisitorSelfCheckoutView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "vms_visitor_access"

    def post(self, request, visit_id):
        visitor = authenticate_visitor(request.headers.get("X-Visitor-Token", ""))
        if not VisitRequest.objects.filter(pk=visit_id, visitor=visitor, status="on_site").exists():
            raise NotFoundError("Active visit not found.")
        visit = checkout_visit(
            visit_id=visit_id, actor_id=None, actor_kind="visitor", location="visitor self-checkout"
        )
        return Response({"id": visit.pk, "status": visit.status})


class VisitorDocumentView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.document.view")]

    def get(self, request, document_id):
        role = _active_role(request).replace("_", " ")
        document = (
            VisitorDocument.objects.select_related("request")
            .filter(pk=document_id, scan_status="clean")
            .first()
        )
        if document is None:
            raise NotFoundError("Document not found.")
        if role in {"security", "security personnel"}:
            user_id = request.principal.user_id
            checkpoint = str(request.query_params.get("checkpoint", ""))[:100]
            scoped = role_service.has_active_assignment(
                user_id=user_id, role="security", scope_type="campus"
            )
            scoped = scoped or (
                checkpoint
                and role_service.has_active_assignment(
                    user_id=user_id, role="security", scope_type="gate", scope_value=checkpoint
                )
            )
            scoped = scoped or any(
                role_service.has_active_assignment(
                    user_id=user_id, role="security", scope_type="zone", scope_value=zone
                )
                for zone in document.request.approved_zones
            )
            if not scoped:
                raise PermissionDeniedError("No active VMS assignment covers this document.")
        elif role in {"admin", "super admin", "superadmin"}:
            _require_operational_role(request, "admin")
        else:
            raise PermissionDeniedError("Security Personnel or Admin access is required.")
        AuditEvent.objects.create(
            actor_user_id=request.principal.user_id,
            actor_kind=role,
            action="visitor_document.read",
            object_type="VisitorDocument",
            object_id=str(document.pk),
            reason="authorized identity review",
        )
        from modules.vms.services.document_storage import upload_path

        try:
            source = upload_path(document.storage_key).open("rb")
        except (OSError, ValueError) as exc:
            raise NotFoundError("Document not found.") from exc
        response = FileResponse(
            source,
            as_attachment=True,
            filename=document.filename,
            content_type=document.content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class VisitListView(APIView):
    permission_classes = [
        HasModuleGrant("vms"),
        HasPermission("vms.visit_request.view", "vms.visit_request.view_self"),
    ]

    def get(self, request):
        principal = request.principal
        permissions = frozenset(getattr(principal, "permissions", ()))
        visits = visible_visits(user_id=principal.user_id, permissions=permissions)
        return Response(
            VisitRequestSerializer(visits.order_by("-created_at")[:200], many=True).data
        )


class HostInboxView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.approve")]

    def get(self, request):
        qs = pending_host_visits(user_id=request.principal.user_id)
        return Response(VisitRequestSerializer(qs[:100], many=True).data)


class AdminReviewInboxView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.approve")]

    def get(self, request):
        if _active_role(request) not in {"admin", "super admin", "super_admin"}:
            return Response({"detail": "Admin review access required."}, status=403)
        _require_operational_role(request, "admin")
        qs = VisitRequest.objects.filter(
            status__in=["pending_admin_contingency", "pending_urgent_review"]
        )
        return Response(VisitRequestSerializer(qs.select_related("visitor")[:100], many=True).data)


class GateOverrideView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.override")]

    def get(self, request):
        _require_operational_role(request, "admin")
        attempts = GateAttempt.objects.filter(result="override_pending", overridden_at__isnull=True)
        return Response(
            [
                {
                    "id": item.pk,
                    "visit_id": item.request_id,
                    "failure_code": item.failure_code,
                    "checkpoint": item.checkpoint,
                    "attempted_at": item.attempted_at,
                    "result": item.result,
                }
                for item in attempts.order_by("-attempted_at")[:200]
            ]
        )

    def post(self, request, attempt_id):
        _require_operational_role(request, "admin")
        serializer = GateOverrideDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = decide_gate_override(
            attempt_id=attempt_id, actor_id=request.principal.user_id, **serializer.validated_data
        )
        return Response(
            {"id": attempt.pk, "result": attempt.result, "failure_code": attempt.failure_code}
        )


class GateEscalationView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.validate")]

    def post(self, request, attempt_id):
        attempt = GateAttempt.objects.filter(pk=attempt_id, result="denied").first()
        if attempt is None:
            raise NotFoundError("Denied gate attempt not found.")
        _require_operational_role(
            request, "security", scope_type="gate", scope_value=attempt.checkpoint
        )
        serializer = GateEscalationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = escalate_gate_attempt(
            attempt_id=attempt_id, actor_id=request.principal.user_id, **serializer.validated_data
        )
        return Response({"id": attempt.pk, "result": attempt.result}, status=202)


class VisitDecisionView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.approve")]

    def post(self, request, visit_id, decision):
        if decision not in {"approve", "reject"}:
            return Response({"detail": "Decision must be approve or reject."}, status=400)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = _active_role(request)
        actor_kind = "admin" if role in {"admin", "super admin", "super_admin"} else "host"
        if actor_kind == "admin":
            _require_operational_role(request, "admin")
        visit = decide_visit(
            visit_id=visit_id,
            actor_id=request.principal.user_id,
            actor_kind=actor_kind,
            decision=decision,
            **serializer.validated_data,
        )
        return Response(VisitRequestSerializer(visit).data)


class VisitTerminationView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.update")]

    def post(self, request, visit_id):
        role = _active_role(request).replace("_", " ")
        actor_kind = "admin" if role in {"admin", "super admin", "superadmin"} else "host"
        if actor_kind == "admin":
            _require_operational_role(request, "admin")
        elif role not in {"faculty", "staff", "host"}:
            raise PermissionDeniedError("Host or Admin access is required.")
        reason = request.data.get("reason", "")
        if not isinstance(reason, str) or len(reason) > 500:
            raise BadRequestError("A termination reason under 500 characters is required.")
        visit = terminate_visit(
            visit_id=visit_id,
            actor_id=request.principal.user_id,
            actor_kind=actor_kind,
            reason=reason,
        )
        return Response(VisitRequestSerializer(visit).data)


class VisitExtensionDecisionView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.update")]

    def post(self, request, visit_id):
        _require_operational_role(request, "admin")
        serializer = VisitExtensionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = decide_visit_extension(
            visit_id=visit_id, actor_id=request.principal.user_id, **serializer.validated_data
        )
        return Response(VisitRequestSerializer(visit).data)


class GateValidateView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.validate")]
    throttle_scope = "vms_gate"

    def post(self, request):
        checkpoint = str(request.data.get("checkpoint", ""))[:100]
        _require_operational_role(request, "security", scope_type="gate", scope_value=checkpoint)
        visit = validate_pass(
            token=request.data.get("credential", ""),
            actor_id=request.principal.user_id,
            checkpoint=checkpoint,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        event = visit.event if visit.event_id else None
        return Response(
            {
                "visit_id": visit.pk,
                "status": visit.status,
                "event": (
                    {
                        "id": event.pk,
                        "name": event.name,
                        "fast_lane_enabled": event.fast_lane_enabled,
                        "overflow_limit": event.overflow_limit,
                        "rate_limit_per_minute": event.rate_limit_per_minute,
                    }
                    if event
                    else None
                ),
            }
        )


class GateCheckoutView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_log.create")]

    def post(self, request, visit_id):
        checkpoint = str(request.data.get("checkpoint", ""))[:100]
        _require_operational_role(request, "security", scope_type="gate", scope_value=checkpoint)
        visit = checkout_visit(
            visit_id=visit_id, actor_id=request.principal.user_id, location=checkpoint
        )
        return Response({"visit_id": visit.pk, "status": visit.status})


class ManualVisitLogView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_log.create")]

    def post(self, request, visit_id):
        serializer = ManualVisitLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data
        checkpoint = fields.pop("location", "")
        _require_operational_role(request, "security", scope_type="gate", scope_value=checkpoint)
        log = record_manual_visit_log(
            visit_id=visit_id, actor_id=request.principal.user_id, location=checkpoint, **fields
        )
        return Response(
            {"id": log.pk, "visit_id": log.request_id, "event_type": log.event_type}, status=201
        )


class WalkInRegistrationView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.validate")]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = WalkInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data.copy()
        checkpoint = fields.pop("checkpoint", "")
        upload = fields.pop("identity_document")
        _require_operational_role(request, "security", scope_type="gate", scope_value=checkpoint)
        visit = _with_identity_upload(
            upload,
            lambda info: register_walk_in(
                **fields, actor_id=request.principal.user_id, document_info=info
            ),
        )
        return Response(
            {"id": visit.pk, "status": visit.status, "ends_at": visit.ends_at}, status=201
        )


class OfflineGateEntryView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.validate")]

    def post(self, request):
        serializer = OfflineEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data.copy()
        checkpoint = fields.pop("checkpoint", "")
        _require_operational_role(request, "security", scope_type="gate", scope_value=checkpoint)
        event = cache_offline_entry(
            **fields,
            checkpoint=checkpoint,
            actor_id=request.principal.user_id,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response({"event_id": str(event.event_uuid), "status": event.status}, status=202)


class LiveVisitorsView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasModuleGrant("vms"),
        HasPermission("vms.visit_request.view"),
    ]

    def get(self, request):
        qs = (
            VisitRequest.objects.filter(status="on_site")
            .select_related("visitor")
            .order_by("starts_at")[:500]
        )
        return Response(VisitRequestSerializer(qs, many=True).data)


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from modules.vms.services.document_storage import clamav_available

        scanner_ready = clamav_available()
        return Response(
            {
                "module": "vms",
                "status": "available" if scanner_ready else "degraded",
                "document_scanner": "available" if scanner_ready else "unavailable",
                "at": timezone.now(),
            },
            status=200 if scanner_ready else 503,
        )


class ZoneAccessView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.gate.validate")]

    def post(self, request, visit_id):
        zone = str(request.data.get("zone", ""))[:80]
        _require_operational_role(request, "security", scope_type="zone", scope_value=zone)
        event = security_service.record_zone_access(
            visit_id=visit_id,
            zone=zone,
            actor_id=request.principal.user_id,
            allowed=True,
            metadata={"checkpoint": str(request.data.get("checkpoint", ""))[:100]},
        )
        return Response({"decision": event.decision, "reason_code": event.reason_code})


class ZoneElevateView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.zone.manage")]

    def post(self, request, visit_id):
        serializer = ZoneElevationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _require_operational_role(
            request, "admin", scope_type="zone", scope_value=serializer.validated_data["zone"]
        )
        elevation = security_service.elevate_zone(
            visit_id=visit_id,
            actor_id=request.principal.user_id,
            **serializer.validated_data,
        )
        return Response({"id": elevation.pk, "valid_until": elevation.valid_until}, status=201)


class EmergencyMusterView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.muster.manage")]

    def get(self, request):
        _require_muster_role(request)
        muster = EmergencyMuster.objects.filter(status="active").first()
        if not muster:
            return Response({"active": None})
        roster = muster.roll_calls.select_related("request__visitor").order_by("request_id")
        return Response(
            {
                "active": {
                    "id": muster.pk,
                    "location": muster.location,
                    "instructions": muster.instructions,
                    "triggered_at": muster.triggered_at,
                    "roster": [
                        {
                            "visit_id": r.request_id,
                            "visitor": r.request.visitor.display_name,
                            "status": r.status,
                            "note": r.note,
                        }
                        for r in roster
                    ],
                }
            }
        )

    def post(self, request):
        _require_muster_role(request)
        muster = security_service.trigger_muster(
            actor_id=request.principal.user_id,
            location=request.data.get("location", ""),
            instructions=request.data.get("instructions", ""),
        )
        return Response({"id": muster.pk, "roster_count": muster.roster_count}, status=201)


class MusterRollCallView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.muster.manage")]

    def post(self, request, muster_id, visit_id):
        _require_muster_role(request)
        roll = security_service.record_roll_call(
            muster_id=muster_id,
            visit_id=visit_id,
            actor_id=request.principal.user_id,
            status=request.data.get("status", ""),
            note=request.data.get("note", ""),
        )
        return Response({"visit_id": roll.request_id, "status": roll.status})


class MusterCompleteView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.muster.manage")]

    def post(self, request, muster_id):
        _require_muster_role(request)
        muster = security_service.complete_muster(
            muster_id=muster_id, actor_id=request.principal.user_id
        )
        return Response({"id": muster.pk, "status": muster.status, "report": muster.report})


class ZoneAlertView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.view")]

    def get(self, request):
        alerts = ZoneAlert.objects.filter(status="open").select_related(
            "access_event__request", "access_event__request__visitor"
        )[:200]
        return Response(
            [
                {
                    "id": a.pk,
                    "visit_id": a.access_event.request_id,
                    "visitor": a.access_event.request.visitor.display_name,
                    "zone": a.access_event.zone,
                    "reason": a.access_event.reason_code,
                    "occurred_at": a.access_event.occurred_at,
                }
                for a in alerts
            ]
        )

    def post(self, request, alert_id=None):
        if alert_id is None:
            return Response({"detail": "Alert id is required."}, status=400)
        alert = security_service.handle_zone_alert(
            alert_id=alert_id,
            actor_id=request.principal.user_id,
            note=request.data.get("note", ""),
            status=request.data.get("status", "handled"),
        )
        return Response({"id": alert.pk, "status": alert.status})


class PolicyVersionsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.policy.manage")]

    def get(self, request):
        rows = AccessPolicyVersion.objects.order_by("-version")[:50]
        return Response(
            [
                {
                    "id": p.pk,
                    "version": p.version,
                    "status": p.status,
                    "effective_from": p.effective_from,
                    "maximum_visit_minutes": p.maximum_visit_minutes,
                    "walk_in_minutes": p.walk_in_minutes,
                    "visiting_hours_start": p.visiting_hours_start,
                    "visiting_hours_end": p.visiting_hours_end,
                    "restricted_zones": p.restricted_zones,
                    "reminder_minutes": p.reminder_minutes,
                }
                for p in rows
            ]
        )

    def post(self, request):
        serializer = PolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = policy_service.create_policy(
            actor_id=request.principal.user_id, fields=serializer.validated_data
        )
        return Response(
            {"id": policy.pk, "version": policy.version, "status": policy.status}, status=201
        )


class PolicyPublishView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.policy.manage")]

    def post(self, request, policy_id):
        policy = policy_service.publish_policy(
            policy_id=policy_id, actor_id=request.principal.user_id
        )
        return Response({"id": policy.pk, "version": policy.version, "status": policy.status})


class RegistryVersionsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.registry.manage")]

    def get(self, request):
        rows = RegistryVersion.objects.order_by("-version")[:50]
        return Response(
            [
                {
                    "id": r.pk,
                    "version": r.version,
                    "status": r.status,
                    "effective_from": r.effective_from,
                }
                for r in rows
            ]
        )

    def post(self, request):
        registry = policy_service.create_registry_version(actor_id=request.principal.user_id)
        return Response({"id": registry.pk, "version": registry.version}, status=201)


class RegistryBlacklistEntryView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.registry.manage")]

    def post(self, request, registry_id):
        serializer = RegistryEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = policy_service.add_blacklist_entry(
            registry_id=registry_id, actor_id=request.principal.user_id, **serializer.validated_data
        )
        return Response({"id": entry.pk, "version_id": registry_id}, status=201)


class RegistrySafeListEntryView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.registry.manage")]

    def post(self, request, registry_id):
        serializer = RegistryEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data
        if not fields.get("expires_at"):
            return Response({"detail": "Safe-list expiry is required."}, status=400)
        entry = policy_service.add_safelist_entry(
            registry_id=registry_id, actor_id=request.principal.user_id, **fields
        )
        return Response({"id": entry.pk, "version_id": registry_id}, status=201)


class RegistryPublishView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.registry.manage")]

    def post(self, request, registry_id):
        registry = policy_service.publish_registry(
            registry_id=registry_id, actor_id=request.principal.user_id
        )
        return Response({"id": registry.pk, "version": registry.version, "status": registry.status})


class AuditEventsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.audit.view")]

    def get(self, request):
        rows = AuditEvent.objects.order_by("-occurred_at")[:200]
        return Response(
            [
                {
                    "id": a.pk,
                    "actor_user_id": a.actor_user_id,
                    "actor_kind": a.actor_kind,
                    "action": a.action,
                    "object_type": a.object_type,
                    "object_id": a.object_id,
                    "occurred_at": a.occurred_at,
                    "reason": a.reason,
                }
                for a in rows
            ]
        )


class RoleAssignmentsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.role.manage")]

    def get(self, request):
        rows = VmsRoleAssignment.objects.filter(revoked_at__isnull=True).order_by("user_id")[:500]
        return Response(
            [
                {
                    "id": a.pk,
                    "user_id": a.user_id,
                    "role": a.role,
                    "scope_type": a.scope_type,
                    "scope_value": a.scope_value,
                    "starts_at": a.starts_at,
                    "ends_at": a.ends_at,
                }
                for a in rows
            ]
        )

    def post(self, request):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = role_service.assign_role(
            **serializer.validated_data, actor_id=request.principal.user_id
        )
        return Response(
            {"id": assignment.pk, "user_id": assignment.user_id, "role": assignment.role},
            status=201,
        )


class RoleAssignmentRevokeView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.role.manage")]

    def post(self, request, assignment_id):
        assignment = role_service.revoke_role(
            assignment_id=assignment_id, actor_id=request.principal.user_id
        )
        return Response({"id": assignment.pk, "revoked_at": assignment.revoked_at})


class IntegrationSettingsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.integration.manage")]

    def get(self, request):
        rows = IntegrationSetting.objects.order_by("integration_type")
        return Response(
            [
                {
                    "integration_type": s.integration_type,
                    "endpoint": s.endpoint,
                    "enabled": s.enabled,
                    "available": s.available,
                    "config": s.config,
                    "updated_at": s.updated_at,
                }
                for s in rows
            ]
        )

    def put(self, request, integration_type):
        serializer = IntegrationSerializer(
            data={**request.data, "integration_type": integration_type}
        )
        serializer.is_valid(raise_exception=True)
        setting = config_service.update_integration(
            **serializer.validated_data, actor_id=request.principal.user_id
        )
        return Response(
            {
                "integration_type": setting.integration_type,
                "enabled": setting.enabled,
                "available": setting.available,
            }
        )


class VipPermissionsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.vip.manage")]

    def get(self, request):
        rows = VipPermission.objects.filter(revoked_at__isnull=True).select_related("visitor")[:500]
        return Response(
            [
                {
                    "id": p.pk,
                    "visitor_id": p.visitor_id,
                    "visitor_name": p.visitor.display_name,
                    "zones": p.zones,
                    "valid_from": p.valid_from,
                    "valid_until": p.valid_until,
                    "reason": p.reason,
                }
                for p in rows
            ]
        )

    def post(self, request):
        serializer = VipPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data
        permission = config_service.grant_vip_permission(
            visitor_id=fields["visitor_id"],
            zones=fields["zones"],
            valid_from=fields["valid_from"],
            valid_until=fields["valid_until"],
            actor_id=request.principal.user_id,
            reason=fields["reason"],
        )
        return Response({"id": permission.pk, "visitor_id": permission.visitor_id}, status=201)


class VipPermissionRevokeView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.vip.manage")]

    def post(self, request, permission_id):
        reason = request.data.get("reason", "")
        if not isinstance(reason, str) or len(reason) > 500:
            return Response({"detail": "Reason must be text under 500 characters."}, status=400)
        permission = config_service.revoke_vip_permission(
            permission_id=permission_id, actor_id=request.principal.user_id, reason=reason
        )
        return Response({"id": permission.pk, "revoked_at": permission.revoked_at})


class EventsView(APIView):
    permission_classes = [
        HasModuleGrant("vms"),
        HasPermission("vms.event.view", "vms.event.manage"),
    ]

    def get(self, request):
        _require_event_view_role(request)
        minute_ago = timezone.now() - timedelta(minutes=1)
        rows = EventRecord.objects.annotate(
            guest_count=Count("visit_requests", distinct=True),
            on_site_count=Count(
                "visit_requests", filter=Q(visit_requests__status="on_site"), distinct=True
            ),
            total_entries=Count(
                "visit_requests__visit_logs",
                filter=Q(visit_requests__visit_logs__event_type="entry"),
                distinct=True,
            ),
            entries_last_minute=Count(
                "visit_requests__visit_logs",
                filter=Q(
                    visit_requests__visit_logs__event_type="entry",
                    visit_requests__visit_logs__occurred_at__gt=minute_ago,
                ),
                distinct=True,
            ),
        ).order_by("-starts_at")[:500]
        return Response(
            [
                {
                    "id": e.pk,
                    "name": e.name,
                    "external_event_id": e.external_event_id,
                    "starts_at": e.starts_at,
                    "ends_at": e.ends_at,
                    "zones": e.zones,
                    "status": e.status,
                    "fast_lane_enabled": e.fast_lane_enabled,
                    "overflow_limit": e.overflow_limit,
                    "rate_limit_per_minute": e.rate_limit_per_minute,
                    "guest_count": e.guest_count,
                    "on_site_count": e.on_site_count,
                    "total_entries": e.total_entries,
                    "entries_last_minute": e.entries_last_minute,
                }
                for e in rows
            ]
        )

    def post(self, request):
        _require_operational_role(request, "admin")
        serializer = EventRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = config_service.create_event(
            **serializer.validated_data, actor_id=request.principal.user_id
        )
        return Response({"id": event.pk, "status": event.status}, status=201)


class EventControlsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.event.manage")]

    def patch(self, request, event_id):
        _require_operational_role(request, "admin")
        serializer = EventControlsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = config_service.update_event_controls(
            event_id=event_id, actor_id=request.principal.user_id, **serializer.validated_data
        )
        return Response(
            {
                "id": event.pk,
                "status": event.status,
                "fast_lane_enabled": event.fast_lane_enabled,
                "overflow_limit": event.overflow_limit,
                "rate_limit_per_minute": event.rate_limit_per_minute,
            }
        )


class EventLifecycleView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.event.manage")]

    def post(self, request, event_id, action):
        _require_operational_role(request, "admin")
        if action not in {"activate", "complete"}:
            raise BadRequestError("Unsupported event lifecycle action.")
        event = config_service.transition_event(
            event_id=event_id, actor_id=request.principal.user_id, action=action
        )
        return Response({"id": event.pk, "status": event.status})


def _parse_event_guest_csv(raw: bytes) -> list[int]:
    content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
    if reader.fieldnames != ["visit_id"]:
        raise ValueError("CSV must contain exactly one visit_id column.")
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("Guest list CSV has a missing or extra field.")
    return [int(row["visit_id"]) for row in rows]


class EventGuestImportView(APIView):
    permission_classes = [
        HasModuleGrant("vms"),
        HasPermission("vms.event.view", "vms.event.manage"),
    ]
    parser_classes = [FormParser, MultiPartParser]

    def get(self, request, event_id):
        _require_event_view_role(request)
        event = EventRecord.objects.filter(pk=event_id).first()
        if event is None:
            raise NotFoundError("Event not found.")
        return Response(
            [
                {
                    "visit_id": row.request_id or row.submitted_visit_id,
                    "status": row.status,
                    "reason": row.reason,
                    "batch_id": row.batch_id,
                }
                for row in EventGuestBatchRow.objects.filter(batch__event=event)
                .select_related("batch")
                .order_by("-created_at")[:1000]
            ]
        )

    def post(self, request, event_id):
        _require_operational_role(request, "admin")
        upload = request.FILES.get("file")
        if upload is None:
            raise BadRequestError("Upload a CSV guest list.", code="event_import_required")
        if upload.size > 1024 * 1024:
            raise BadRequestError(
                "Guest list CSV must be no larger than 1 MB.", code="event_import_too_large"
            )
        try:
            payload = {"visit_ids": _parse_event_guest_csv(upload.read(1024 * 1024 + 1))}
        except (UnicodeDecodeError, csv.Error, TypeError, ValueError) as exc:
            raise BadRequestError(
                "Guest list CSV is invalid: " + str(exc), code="invalid_event_import"
            ) from exc
        serializer = EventGuestImportSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        batch = config_service.import_event_guests(
            event_id=event_id,
            visit_ids=serializer.validated_data["visit_ids"],
            actor_id=request.principal.user_id,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        rows = list(batch.rows.order_by("id").values("submitted_visit_id", "status", "reason"))
        return Response({"batch_id": batch.pk, "results": rows}, status=201)


class PreAuthorizationsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.create")]

    def get(self, request):
        rows = (
            PreAuthorization.objects.filter(
                host_user_id=request.principal.user_id, revoked_at__isnull=True
            )
            .select_related("visitor")
            .order_by("-valid_until")[:200]
        )
        return Response(
            [
                {
                    "id": a.pk,
                    "visitor_id": a.visitor_id,
                    "visitor_name": a.visitor.display_name,
                    "zones": a.zones,
                    "valid_from": a.valid_from,
                    "valid_until": a.valid_until,
                    "reason": a.reason,
                }
                for a in rows
            ]
        )

    def post(self, request):
        serializer = PreAuthorizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        authorization = create_preauthorization(
            host_user_id=request.principal.user_id, **serializer.validated_data
        )
        return Response(
            {"id": authorization.pk, "visitor_id": authorization.visitor_id}, status=201
        )


class PreAuthorizationRevokeView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.visit_request.create")]

    def post(self, request, authorization_id):
        authorization = revoke_preauthorization(
            authorization_id=authorization_id, host_user_id=request.principal.user_id
        )
        return Response({"id": authorization.pk, "revoked_at": authorization.revoked_at})


def _date_filters(query_params):
    start_raw, end_raw = query_params.get("starts_at"), query_params.get("ends_at")
    starts_at = parse_datetime(start_raw) if start_raw else None
    ends_at = parse_datetime(end_raw) if end_raw else None
    if (start_raw and starts_at is None) or (end_raw and ends_at is None):
        raise BadRequestError(
            "Date filters must use ISO-8601 datetime values.", code="invalid_date_filter"
        )
    if starts_at and ends_at and ends_at <= starts_at:
        raise BadRequestError("ends_at must be after starts_at.", code="invalid_date_range")
    return {"starts_at": starts_at, "ends_at": ends_at}


class VisitorReportsView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.report.view")]

    def get(self, request):
        filters = _date_filters(request.query_params)
        return Response(
            {
                "summary": report_selectors.visit_summary(**filters),
                "daily": report_selectors.daily_counts(**filters),
            }
        )


class VisitorExportView(APIView):
    permission_classes = [HasModuleGrant("vms"), HasPermission("vms.report.view")]
    throttle_scope = "export"

    def get(self, request):
        filters = _date_filters(request.query_params)
        rows = report_selectors.visitor_export_rows(**filters)
        return stream_csv(
            filename="vms-visitors.csv",
            header=[
                "Visit ID",
                "Visitor",
                "Host ID",
                "Purpose",
                "Status",
                "Starts",
                "Ends",
                "Zones",
            ],
            rows=rows,
        )
