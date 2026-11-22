"""API Views for Leave Management."""
from __future__ import annotations

import datetime
import csv
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.http import HttpResponse
from django.utils.html import escape
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.selectors import (
    get_application_by_id,
    get_my_applications,
    get_or_create_balance,
    get_ledger_history,
    get_pending_review_queue,
    get_pending_substitute_requests,
    get_published_holidays,
    get_vacation_periods,
)
from modules.leave.models import HolidayCalendar, LeavePolicyConfig, VacationPeriod
from modules.leave.services import (
    apply_for_leave,
    maintain_finalized_record,
    process_cancellation_decision,
    forward_to_sanctioning_authority,
    re_nominate_substitute,
    record_offline_leave,
    request_cancellation,
    request_extension,
    respond_to_substitute_request,
    review_by_unit_head,
    review_resumption_declaration,
    sanction_application,
    submit_resumption_declaration,
    withdraw_application,
)
from modules.leave.services.routing import resolve_application_route

MODULE = HasModuleGrant("leave")
P_CREATE = HasPermission("leave.application.create")
P_VIEW_SELF = HasPermission("leave.application.view_self")
P_SUBSTITUTE = HasPermission("leave.substitute.respond")
P_REVIEW = HasPermission("leave.application.review")
P_SANCTION = HasPermission("leave.application.sanction")
P_ADMIN = HasPermission("leave.admin.manage")
P_CALENDAR = HasPermission("leave.calendar.view")


def _actor_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "user_id"):
        return principal.user_id
    raise BadRequestError("Authenticated principal has no user id.", code="missing_actor")


def _require_assignment(request, pk: int, *assignment_fields: str):
    app = get_application_by_id(pk)
    actor_id = _actor_user_id(request)
    if not any(getattr(app, field) == actor_id for field in assignment_fields):
        raise PermissionDenied("This workflow item is not assigned to you.")
    return app


class MyBalancesView(APIView):
    """GET /api/v1/leave/balances/ - View current leave balance and ledger history."""

    permission_classes = [MODULE, P_VIEW_SELF]

    @extend_schema(responses={200: s.LeaveBalanceSerializer})
    def get(self, request):
        user_id = _actor_user_id(request)
        year = int(request.query_params.get("year", datetime.date.today().year))
        is_faculty = any(role.lower() == "faculty" for role in request.principal.roles)
        balance = get_or_create_balance(user_id, year=year, is_faculty=is_faculty)
        ledger = get_ledger_history(user_id, year=year)
        return Response({
            "balance": s.LeaveBalanceSerializer(balance).data,
            "ledger": s.LeaveLedgerEntrySerializer(ledger, many=True).data,
        })


class MyApplicationsView(APIView):
    """GET/POST /api/v1/leave/applications/ - View my applications or apply."""

    permission_classes = [MODULE, P_VIEW_SELF]

    def get_permissions(self):
        permissions = [MODULE, P_CREATE] if self.request.method == "POST" else [MODULE, P_VIEW_SELF]
        return [permission() for permission in permissions]

    @extend_schema(responses={200: s.LeaveApplicationSerializer(many=True)})
    def get(self, request):
        user_id = _actor_user_id(request)
        apps = get_my_applications(user_id)
        return Response(s.LeaveApplicationSerializer(apps, many=True).data)

    @extend_schema(request=s.ApplyLeaveSerializer, responses={201: s.LeaveApplicationSerializer})
    def post(self, request):
        user_id = _actor_user_id(request)
        serializer = s.ApplyLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        app = apply_for_leave(
            user_id=user_id,
            is_faculty=any(role.lower() == "faculty" for role in request.principal.roles),
            **resolve_application_route(
                category=serializer.validated_data["category"], applicant_id=user_id,
                roles=request.principal.roles, active_role=request.principal.active_role,
            ),
            **serializer.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    """GET/DELETE /api/v1/leave/applications/<id>/ - View details or withdraw."""

    permission_classes = [MODULE, P_VIEW_SELF]

    @extend_schema(responses={200: s.LeaveApplicationSerializer})
    def get(self, request, pk: int):
        user_id = _actor_user_id(request)
        app = get_application_by_id(pk, user_id=user_id)
        return Response(s.LeaveApplicationSerializer(app).data)

    @extend_schema(responses={200: s.LeaveApplicationSerializer})
    def delete(self, request, pk: int):
        user_id = _actor_user_id(request)
        reason = request.query_params.get("reason", "Withdrawn by employee")
        app = withdraw_application(user_id=user_id, application_id=pk, reason=reason)
        return Response(s.LeaveApplicationSerializer(app).data)


class ExportApplicationView(APIView):
    permission_classes = [MODULE, P_VIEW_SELF]

    def get(self, request, pk: int):
        app = get_application_by_id(pk, user_id=_actor_user_id(request))
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="leave-application-{app.pk}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Field", "Value"])
        for key, value in s.LeaveApplicationSerializer(app).data.items():
            if key not in {"substitute_requests", "actions"}:
                writer.writerow([key, value])
        writer.writerow(["history", ""])
        for action in app.actions.all():
            writer.writerow([action.created_at.isoformat(), f"{action.action}: {action.remarks}"])
        return response


class PrintableApplicationView(APIView):
    permission_classes = [MODULE, P_VIEW_SELF]

    def get(self, request, pk: int):
        app = get_application_by_id(pk, user_id=_actor_user_id(request))
        rows = {
            "Application": f"#{app.pk}", "Employee ID": str(app.user_id), "Category": app.category,
            "Dates": f"{app.start_date} to {app.end_date}", "Days": str(app.days_count),
            "Purpose": app.purpose, "Status": app.status.replace("_", " ").title(),
            "Station Leave": app.station_destination if app.is_station_leave else "No",
            "Sanctioning remarks": app.sanctioning_remarks,
        }
        body = "".join(f"<tr><th>{escape(label)}</th><td>{escape(value or '')}</td></tr>" for label, value in rows.items())
        html = (
            "<!doctype html><html><head><meta charset='utf-8'><title>Leave application</title>"
            "<style>body{font:16px Arial,sans-serif;max-width:800px;margin:40px auto;color:#172033}"
            "h1{font-size:24px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border:1px solid #ccd3df}"
            "th{width:28%;background:#f1f4f8}@media print{button{display:none}body{margin:0;max-width:none}}</style>"
            "</head><body><button onclick='window.print()'>Print</button><h1>Employee Leave Application</h1>"
            f"<table>{body}</table></body></html>"
        )
        return HttpResponse(html, content_type="text/html; charset=utf-8")


class RequestCancellationView(APIView):
    """POST /api/v1/leave/applications/<id>/cancel/ - Pre-start cancellation."""

    permission_classes = [MODULE, P_VIEW_SELF]

    @extend_schema(request=s.CancellationRequestSerializer, responses={200: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        serializer = s.CancellationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = request_cancellation(
            user_id=user_id,
            application_id=pk,
            reason=serializer.validated_data["reason"],
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class RequestExtensionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.extend")]

    @extend_schema(request=s.ExtensionRequestSerializer, responses={201: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        serializer = s.ExtensionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        roles = {role.lower() for role in request.principal.roles}
        app = request_extension(
            user_id=user_id, application_id=pk, is_faculty="faculty" in roles,
            **serializer.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class SubmitResumptionView(APIView):
    """POST /api/v1/leave/applications/<id>/resume/ - Declare duty resumption."""

    permission_classes = [MODULE, P_VIEW_SELF]

    @extend_schema(request=s.ResumptionSerializer, responses={200: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        serializer = s.ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = submit_resumption_declaration(
            user_id=user_id,
            application_id=pk,
            resumption_date=serializer.validated_data["resumption_date"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class MySubstituteRequestsView(APIView):
    """GET /api/v1/leave/substitutes/ - My pending substitute requests."""

    permission_classes = [MODULE, P_SUBSTITUTE]

    @extend_schema(responses={200: s.SubstituteRequestSerializer(many=True)})
    def get(self, request):
        user_id = _actor_user_id(request)
        reqs = get_pending_substitute_requests(user_id)
        return Response(s.SubstituteRequestSerializer(reqs, many=True).data)


class RespondSubstituteRequestView(APIView):
    """POST /api/v1/leave/substitutes/<id>/respond/ - Accept or decline."""

    permission_classes = [MODULE, P_SUBSTITUTE]

    @extend_schema(request=s.SubstituteResponseSerializer, responses={200: s.SubstituteRequestSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        serializer = s.SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub_req = respond_to_substitute_request(
            substitute_user_id=user_id,
            request_id=pk,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(s.SubstituteRequestSerializer(sub_req).data)


class ReNominateSubstituteView(APIView):
    """POST /api/v1/leave/applications/<id>/renominate-substitute/."""

    permission_classes = [MODULE, P_VIEW_SELF]

    @extend_schema(request=s.ReNominateSubstituteSerializer, responses={200: s.SubstituteRequestSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        serializer = s.ReNominateSubstituteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub_req = re_nominate_substitute(
            user_id=user_id,
            application_id=pk,
            new_substitute_user_id=serializer.validated_data["substitute_user_id"],
            responsibilities=serializer.validated_data.get("responsibilities", ""),
        )
        return Response(s.SubstituteRequestSerializer(sub_req).data)


class PendingApprovalsQueueView(APIView):
    """GET /api/v1/leave/approvals/ - Pending reviews inbox."""

    permission_classes = [MODULE, P_REVIEW]

    @extend_schema(responses={200: s.LeaveApplicationSerializer(many=True)})
    def get(self, request):
        user_id = _actor_user_id(request)
        queue = get_pending_review_queue(user_id=user_id)
        return Response(s.LeaveApplicationSerializer(queue, many=True).data)


class UnitHeadReviewView(APIView):
    """POST /api/v1/leave/approvals/<id>/unit-head-review/."""

    permission_classes = [MODULE, P_REVIEW]

    @extend_schema(request=s.UnitHeadReviewSerializer, responses={200: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        _require_assignment(request, pk, "unit_head_user_id")
        serializer = s.UnitHeadReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = review_by_unit_head(
            reviewer_user_id=user_id,
            application_id=pk,
            recommended=serializer.validated_data["recommended"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class SanctionDecisionView(APIView):
    """POST /api/v1/leave/approvals/<id>/sanction/."""

    permission_classes = [MODULE, P_SANCTION]

    @extend_schema(request=s.SanctionDecisionSerializer, responses={200: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        assigned = _require_assignment(request, pk, "sanctioning_authority_user_id")
        if assigned.unit_head_user_id is not None and assigned.unit_head_reviewed_at is None:
            raise PermissionDenied("Unit Head review must be completed before sanction.")
        if assigned.establishment_user_id is not None and assigned.establishment_reviewed_at is None:
            raise PermissionDenied("Establishment must forward this item before sanction.")
        serializer = s.SanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = sanction_application(
            sanctioner_user_id=user_id,
            application_id=pk,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class ReviewCancellationView(APIView):
    """POST /api/v1/leave/approvals/<id>/review-cancellation/."""

    permission_classes = [MODULE, P_SANCTION]

    @extend_schema(request=s.SanctionDecisionSerializer, responses={200: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        assigned = _require_assignment(request, pk, "sanctioning_authority_user_id")
        if assigned.unit_head_user_id is not None and assigned.unit_head_reviewed_at is None:
            raise PermissionDenied("Unit Head review must be completed before cancellation sanction.")
        if assigned.establishment_user_id is not None and assigned.establishment_reviewed_at is None:
            raise PermissionDenied("Establishment must forward this item before sanction.")
        serializer = s.SanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = process_cancellation_decision(
            reviewer_user_id=user_id,
            application_id=pk,
            decision=serializer.validated_data["decision"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class ForwardApprovalView(APIView):
    permission_classes = [MODULE, P_REVIEW]

    @extend_schema(responses={200: s.LeaveApplicationSerializer})
    def post(self, request, pk: int):
        app = _require_assignment(request, pk, "establishment_user_id")
        if app.unit_head_user_id is not None and app.unit_head_reviewed_at is None:
            raise PermissionDenied("Unit Head review must be completed before Establishment processing.")
        app = forward_to_sanctioning_authority(
            establishment_user_id=_actor_user_id(request), application_id=pk,
            remarks=request.data.get("remarks", ""),
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class ReviewResumptionView(APIView):
    """POST /api/v1/leave/approvals/<id>/review-resumption/."""

    permission_classes = [MODULE, P_SANCTION]

    def post(self, request, pk: int):
        user_id = _actor_user_id(request)
        _require_assignment(request, pk, "sanctioning_authority_user_id")
        remarks = request.data.get("remarks", "")
        app = review_resumption_declaration(
            reviewer_user_id=user_id,
            application_id=pk,
            remarks=remarks,
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class HolidayCalendarView(APIView):
    """GET/POST /api/v1/leave/calendar/."""

    permission_classes = [MODULE, P_CALENDAR]

    @extend_schema(responses={200: s.HolidayCalendarSerializer(many=True)})
    def get(self, request):
        year = int(request.query_params.get("year", datetime.date.today().year))
        holidays = get_published_holidays(year)
        vacations = get_vacation_periods(year)
        return Response({
            "holidays": s.HolidayCalendarSerializer(holidays, many=True).data,
            "vacation_periods": s.VacationPeriodSerializer(vacations, many=True).data,
        })


class HolidayCalendarAdminView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.manage")]

    @extend_schema(request=s.HolidayCalendarImportSerializer, responses={201: s.HolidayCalendarSerializer(many=True)})
    def post(self, request):
        serializer = s.HolidayCalendarImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        rows = []
        for item in serializer.validated_data["entries"]:
            if item["date"].year != year:
                raise BadRequestError("Every calendar date must match the selected year.", code="calendar_year_mismatch")
            rows.append(HolidayCalendar(**item, year=year, is_published=False))
        with transaction.atomic():
            HolidayCalendar.objects.bulk_create(rows)
        return Response(s.HolidayCalendarSerializer(rows, many=True).data, status=status.HTTP_201_CREATED)


class PublishHolidayCalendarView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.manage")]

    def post(self, request, year: int):
        ids = request.data.get("holiday_ids", [])
        rows = list(HolidayCalendar.objects.filter(pk__in=ids, year=year))
        if not rows or len(rows) != len(set(ids)):
            raise BadRequestError("Select at least one calendar entry to publish.", code="empty_calendar")
        dates = [row.date for row in rows]
        if len(dates) != len(set(dates)):
            raise BadRequestError("A published calendar cannot contain duplicate dates.", code="duplicate_calendar_date")
        with transaction.atomic():
            HolidayCalendar.objects.filter(year=year, is_published=True).update(is_published=False)
            HolidayCalendar.objects.filter(pk__in=[row.pk for row in rows]).update(is_published=True)
        return Response({"year": year, "published_count": len(rows)})


class LeaveConfigurationView(APIView):
    permission_classes = [MODULE, P_ADMIN]

    def get(self, request):
        return Response({row.key: {"value": row.value, "description": row.description}
                         for row in LeavePolicyConfig.objects.order_by("key")})

    @extend_schema(request=s.AdminConfigSerializer, responses={200: s.AdminConfigSerializer})
    def put(self, request):
        serializer = s.AdminConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data["key"]
        if not key.startswith(("route.", "policy.", "sla.")):
            raise BadRequestError("Configuration keys must use route., policy., or sla. prefixes.", code="invalid_config_key")
        value = serializer.validated_data["value"]
        if key.startswith("route."):
            category = key.split(".", 2)[1]
            if not isinstance(value, dict) or "unit_head_user_id" not in value:
                raise BadRequestError("Routes must include a Unit Head user ID.", code="invalid_leave_route")
            required_route_fields = ["unit_head_user_id"]
            if category not in {"CL", "RH"}:
                required_route_fields.append("sanctioning_authority_user_id")
            if any(field not in value for field in required_route_fields):
                raise BadRequestError("Higher-sanction routes must include the final authority user ID.", code="invalid_leave_route")
            try:
                route_ids = [int(value[field]) for field in required_route_fields]
                if "establishment_user_id" in value:
                    route_ids.append(int(value["establishment_user_id"]))
                if any(user_id < 1 for user_id in route_ids):
                    raise ValueError
            except (TypeError, ValueError):
                raise BadRequestError("Route user IDs must be positive integers.", code="invalid_leave_route")
        if key == "policy.entitlements":
            required = {"CL", "RH", "SCL", "EL", "VL", "COL"}
            if not isinstance(value, dict) or not required.issubset(value):
                raise BadRequestError("Entitlements must define CL, RH, SCL, EL, VL, and COL.", code="invalid_entitlements")
            try:
                amounts = [Decimal(str(value[category])) for category in required]
                if any(not amount.is_finite() or amount < 0 or amount > Decimal("999.9")
                       or amount.as_tuple().exponent < -1 for amount in amounts):
                    raise BadRequestError("Entitlements must be nonnegative values with at most one decimal place.", code="invalid_entitlements")
            except (InvalidOperation, TypeError, ValueError):
                raise BadRequestError("Entitlements must be numeric day values.", code="invalid_entitlements")
        if key in {"sla.reminder_hours", "sla.escalation_hours"}:
            try:
                if int(value) < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise BadRequestError("SLA thresholds must be positive whole hours.", code="invalid_sla_threshold")
        if key == "sla.escalation_user_id":
            try:
                if int(value) < 1:
                    raise ValueError
            except (TypeError, ValueError):
                raise BadRequestError("Escalation authority must be a positive user ID.", code="invalid_sla_authority")
        config, _ = LeavePolicyConfig.objects.update_or_create(
            key=key, defaults={"value": value,
                               "description": serializer.validated_data["description"]},
        )
        return Response({"key": config.key, "value": config.value, "description": config.description})


class VacationPeriodsSyncView(APIView):
    """Accept the current vacation-period snapshot from Academic Calendar."""
    permission_classes = [MODULE, HasPermission("leave.calendar.vacation_sync")]

    @extend_schema(request=s.VacationPeriodsSyncSerializer, responses={200: s.VacationPeriodSerializer(many=True)})
    def put(self, request):
        serializer = s.VacationPeriodsSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        periods = serializer.validated_data["periods"]
        for period in periods:
            if (period["start_date"].year != year or period["end_date"].year != year
                    or period["end_date"] < period["start_date"]):
                raise BadRequestError("Vacation periods must be valid intervals within the selected year.", code="invalid_vacation_period")
        with transaction.atomic():
            VacationPeriod.objects.filter(year=year).update(is_active=False)
            rows = VacationPeriod.objects.bulk_create([
                VacationPeriod(**period, year=year, is_active=True) for period in periods
            ])
        return Response(s.VacationPeriodSerializer(rows, many=True).data)


class OfflineLeaveSyncView(APIView):
    """POST /api/v1/leave/admin/offline-sync/."""

    permission_classes = [MODULE, P_ADMIN]

    @extend_schema(request=s.OfflineLeaveSerializer, responses={201: s.LeaveApplicationSerializer})
    def post(self, request):
        user_id = _actor_user_id(request)
        serializer = s.OfflineLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = record_offline_leave(
            admin_user_id=user_id,
            **serializer.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class MaintainLeaveRecordView(APIView):
    permission_classes = [MODULE, P_ADMIN]

    @extend_schema(request=s.LeaveRecordCorrectionSerializer, responses={200: s.LeaveApplicationSerializer})
    def patch(self, request, pk: int):
        serializer = s.LeaveRecordCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        reason = values.pop("reason")
        app = maintain_finalized_record(
            admin_user_id=_actor_user_id(request), application_id=pk,
            reason=reason, changes=values,
        )
        return Response(s.LeaveApplicationSerializer(app).data)
