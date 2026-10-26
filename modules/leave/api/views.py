"""REST API endpoints for ELM module - Model 2 (Qwen 14B)."""
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    CalendarReleaseInputSerializer,
    LeaveAccountSerializer,
    LeaveRequestInputSerializer,
    LeaveRequestSerializer,
    OfflineSyncInputSerializer,
)
from modules.leave.models import (
    HolidayCalendarRelease,
    LeaveHierarchyConfig,
    LeavePolicyConfig,
    LeaveRequest,
    LeaveSLASettings,
)
from modules.leave.selectors import leave_selectors
from modules.leave.services import leave_services

MODULE = HasModuleGrant("leave")


class LeaveAccountListView(APIView):
    """EL-UC-012: View employee's current leave balances."""

    permission_classes = [MODULE, HasPermission("leave.request.view_self")]

    def get(self, request):
        user_id = str(request.principal.user_id)
        year = int(request.query_params.get("year", 2026))
        accounts = leave_selectors.get_user_accounts(user_id=user_id, year=year)
        serializer = LeaveAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class LeaveRequestListView(APIView):
    """EL-UC-001 & EL-UC-012: Apply for leave or list user's leave requests."""

    def get_permissions(self):
        codes = {
            "GET": "leave.request.view_self",
            "POST": "leave.request.create",
        }
        code = codes.get(self.request.method)
        if code is None:
            return [MODULE()]
        return [MODULE(), HasPermission(code)()]

    def get(self, request):
        user_id = str(request.principal.user_id)
        requests = leave_selectors.get_user_leave_requests(user_id=user_id)
        serializer = LeaveRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id = str(request.principal.user_id)
        role = request.principal.active_role or request.principal.kind
        employee_type = request.principal.kind
        serializer = LeaveRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            req = leave_services.submit_leave_request(
                applicant_id=user_id, applicant_role=role,
                department=getattr(request.principal, "department", ""),
                employee_type=employee_type, **serializer.validated_data,
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubstituteActionView(APIView):
    """EL-UC-002: Substitute Accept or Decline."""

    permission_classes = [MODULE, HasPermission("leave.substitute.review")]

    def post(self, request, pk):
        sub_id = str(request.principal.user_id)
        accept = request.data.get("accept", True)
        try:
            req = leave_services.process_substitute_response(pk, sub_id, accept)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnitHeadActionView(APIView):
    """EL-UC-003: Unit head approve/reject (CL/RH) or recommend (higher sanction)."""

    permission_classes = [MODULE, HasPermission("leave.request.review")]

    def post(self, request, pk):
        uh_id = str(request.principal.user_id)
        action = request.data.get("action")
        remarks = request.data.get("remarks", "")
        try:
            req = leave_services.review_unit_head(pk, uh_id, action, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EstablishmentRouteView(APIView):
    """EL-UC-004: Establishment routing."""

    permission_classes = [MODULE, HasPermission("leave.request.assign")]

    def post(self, request, pk):
        est_id = str(request.principal.user_id)
        remarks = request.data.get("remarks", "")
        try:
            req = leave_services.route_establishment(pk, est_id, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SanctionActionView(APIView):
    """EL-UC-005: Final Sanctioning Decision."""

    permission_classes = [MODULE, HasPermission("leave.request.approve")]

    def post(self, request, pk):
        sanction_id = str(request.principal.user_id)
        approve = request.data.get("approve", True)
        remarks = request.data.get("remarks", "")
        try:
            req = leave_services.sanction_decision(pk, sanction_id, approve, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawRequestView(APIView):
    """EL-UC-007: Immediate withdrawal."""

    permission_classes = [MODULE, HasPermission("leave.request.delete")]

    def post(self, request, pk):
        user_id = str(request.principal.user_id)
        try:
            req = leave_services.withdraw_request(pk, user_id)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResumptionActionView(APIView):
    """EL-UC-010 & EL-UC-011: Resumption submission and review."""

    def get_permissions(self):
        codes = {
            "SUBMIT": "leave.resumption.create",
            "REVIEW": "leave.resumption.review",
        }
        code = codes.get(self.request.data.get("action"), "leave.permission.invalid")
        return [MODULE(), HasPermission(code)()]

    def post(self, request, pk):
        sub_action = request.data.get("action")  # 'SUBMIT' or 'REVIEW'
        user_id = str(request.principal.user_id)
        try:
            if sub_action == "SUBMIT":
                actual_date = request.data.get("actual_date")
                notes = request.data.get("notes", "")
                req = leave_services.submit_resumption(pk, user_id, actual_date, notes)
            else:
                remarks = request.data.get("remarks", "")
                req = leave_services.review_resumption(pk, user_id, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveInboxView(APIView):
    """EL-UC-012: Pending workflow items assigned to the authenticated actor."""
    permission_classes = [MODULE, HasPermission("leave.request.view")]

    def get(self, request):
        rows = leave_selectors.get_actor_inbox(str(request.principal.user_id))
        return Response(LeaveRequestSerializer(rows, many=True).data)


class LeavePolicyConfigView(APIView):
    """Maintain current policy values; this baseline has no publish lifecycle."""
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]
    policy_fields = {
        "annual_entitlement", "allows_half_day", "allows_carry_forward",
        "is_continuous_count", "requires_substitute_default", "requires_medical_proof",
    }

    def get(self, request):
        rows = LeavePolicyConfig.objects.order_by("category").values(
            "category", "annual_entitlement", "allows_half_day", "allows_carry_forward",
            "is_continuous_count", "requires_substitute_default", "requires_medical_proof",
            "updated_at",
        )
        return Response(list(rows))

    def put(self, request, category):
        unknown = set(request.data) - self.policy_fields
        if unknown:
            return Response({"error": f"Unsupported policy fields: {', '.join(sorted(unknown))}"},
                            status=status.HTTP_400_BAD_REQUEST)
        values = dict(request.data)
        for name in ("allows_half_day", "allows_carry_forward", "is_continuous_count",
                     "requires_substitute_default", "requires_medical_proof"):
            if name in values and not isinstance(values[name], bool):
                return Response(
                    {"error": f"{name} must be a boolean."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if "annual_entitlement" in values:
            try:
                values["annual_entitlement"] = float(values["annual_entitlement"])
            except (TypeError, ValueError):
                return Response(
                    {"error": "annual_entitlement must be numeric."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            obj = leave_services.save_policy_config(category, values)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"category": obj.category, **{
            field: getattr(obj, field) for field in self.policy_fields
        }})


class LeaveHierarchyConfigView(APIView):
    """Maintain current department/designation/category route configuration."""
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]
    route_fields = {"unit_head_id", "establishment_user_id", "sanctioning_authority_id"}

    def get(self, request):
        rows = LeaveHierarchyConfig.objects.order_by(
            "department", "applicant_role", "category"
        ).values(
            "id", "department", "applicant_role", "category", "unit_head_id",
            "establishment_user_id", "sanctioning_authority_id", "updated_at",
        )
        return Response(list(rows))

    def put(self, request):
        data = request.data
        required = ("department", "applicant_role", "category")
        allowed_fields = set(required) | self.route_fields
        if any(not data.get(key) for key in required) or set(data) - allowed_fields:
            return Response(
                {"error": "Provide department, applicant_role, category, and only route fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        values = {key: data[key] for key in self.route_fields if key in data}
        if any(not isinstance(value, str) for value in values.values()):
            return Response(
                {"error": "Route IDs must be strings."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            obj = leave_services.save_hierarchy_config(
                data["department"], data["applicant_role"], data["category"], values
            )
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": obj.pk, "department": obj.department,
                         "applicant_role": obj.applicant_role, "category": obj.category,
                         "unit_head_id": obj.unit_head_id,
                         "establishment_user_id": obj.establishment_user_id,
                         "sanctioning_authority_id": obj.sanctioning_authority_id})


class HolidayCalendarReleaseView(APIView):
    """Stage a replacement calendar without changing currently effective dates."""
    permission_classes = [MODULE, HasPermission("leave.calendar.publish")]

    def get(self, request):
        releases = HolidayCalendarRelease.objects.order_by("-created_at")
        return Response([{
            "id": release.pk, "name": release.name, "is_current": release.is_current,
            "created_by": release.created_by, "created_at": release.created_at,
            "published_at": release.published_at,
            "entries": list(release.entries.order_by("date").values(
                "date", "title", "is_restricted_holiday"
            )),
        } for release in releases])

    def put(self, request, pk):
        serializer = CalendarReleaseInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            release = leave_services.revise_holiday_calendar(
                pk, serializer.validated_data["name"], serializer.validated_data["entries"]
            )
        except HolidayCalendarRelease.DoesNotExist:
            return Response(
                {"error": "Calendar release not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": release.pk, "name": release.name, "is_current": False})

    def post(self, request):
        serializer = CalendarReleaseInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            release = leave_services.stage_holiday_calendar(
                serializer.validated_data["name"], str(request.principal.user_id),
                serializer.validated_data["entries"],
            )
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": release.pk, "name": release.name, "is_current": False},
                        status=status.HTTP_201_CREATED)


class PublishHolidayCalendarView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.publish")]

    def post(self, request, pk):
        try:
            release = leave_services.publish_holiday_calendar(pk)
        except HolidayCalendarRelease.DoesNotExist:
            return Response(
                {"error": "Calendar release not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": release.pk, "name": release.name,
                         "is_current": release.is_current, "published_at": release.published_at})


class OfflineLeaveSyncView(APIView):
    """CFR-EL-027: Synchronize an already sanctioned offline leave record."""
    permission_classes = [MODULE, HasPermission("leave.record.manage")]

    def post(self, request):
        if request.principal.active_role != "leave_administrator":
            return Response(
                {"error": "Offline synchronization is restricted to Leave Administrators."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = OfflineSyncInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            req = leave_services.synchronize_offline_sanctioned_leave(
                admin_id=str(request.principal.user_id), **serializer.validated_data
            )
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveRecordCorrectionView(APIView):
    """CFR-EL-026: Correct descriptive fields without changing sanction state."""
    permission_classes = [MODULE, HasPermission("leave.record.manage")]
    correction_fields = {
        "purpose", "department", "station_destination", "station_address", "resumption_notes"
    }

    def patch(self, request, pk):
        changes = {key: value for key, value in request.data.items() if key != "reason"}
        if set(changes) - self.correction_fields:
            return Response({"error": "This endpoint cannot change workflow or sanction fields."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            req = leave_services.maintain_leave_record(
                pk, str(request.principal.user_id), changes, request.data.get("reason", "")
            )
        except LeaveRequest.DoesNotExist:
            return Response({"error": "Leave record not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(req).data)


class LeaveSLAConfigView(APIView):
    """Maintain reminder/escalation thresholds for SLA-controlled tasks."""
    permission_classes = [MODULE, HasPermission("leave.policy.manage")]
    fields = {"reminder_hours", "escalation_hours", "escalation_authority"}

    def get(self, request):
        rows = LeaveSLASettings.objects.order_by("task_code").values(
            "task_code", "reminder_hours", "escalation_hours", "escalation_authority"
        )
        return Response(list(rows))

    def put(self, request, task_code):
        unknown = set(request.data) - self.fields
        if unknown:
            return Response(
                {"error": "Unsupported SLA fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        values = dict(request.data)
        for field in ("reminder_hours", "escalation_hours"):
            if field in values and (
                isinstance(values[field], bool) or not str(values[field]).isdigit()
            ):
                return Response({"error": f"{field} must be a non-negative integer."},
                                status=status.HTTP_400_BAD_REQUEST)
            if field in values:
                values[field] = int(values[field])
        try:
            item = leave_services.save_sla_config(task_code, values)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"task_code": item.task_code, "reminder_hours": item.reminder_hours,
                         "escalation_hours": item.escalation_hours,
                         "escalation_authority": item.escalation_authority})
