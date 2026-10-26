from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    ActionReasonSerializer,
    DecisionSerializer,
    ExtensionSerializer,
    LeaveApplicationInputSerializer,
    LeaveApplicationSerializer,
    LeaveCalendarDateSerializer,
    LeaveCalendarSerializer,
    LeaveHierarchySerializer,
    LeavePolicySerializer,
    OfflineLeaveRecordSerializer,
    ResumptionSerializer,
    RetryAfterDeclineSerializer,
    SubstituteResponseSerializer,
    VacationPeriodSerializer,
)
from modules.elm.models import (
    LeaveApplication,
    LeaveCalendar,
    LeaveCalendarDate,
    LeaveHierarchy,
    LeaveNotice,
    LeavePolicy,
    LeaveSLAConfig,
    VacationPeriod,
)
from modules.elm.services import (
    _balance,
    _employee_kind,
    _record,
    create_cancellation,
    create_extension,
    create_leave_application,
    create_resumption,
    decide_request,
    post_application_balance,
    process_sla_thresholds,
    process_year_end,
    respond_substitute,
    retry_after_substitute_decline,
    withdraw_request,
)

MODULE = HasModuleGrant("elm")
P_VIEW_SELF = "elm.leave.view_self"
P_VIEW_ALL = "elm.leave.view_all"
P_CREATE = "elm.leave.create"
P_SUBSTITUTE = "elm.leave.substitute"
P_REVIEW = "elm.leave.review"
P_SANCTION = "elm.leave.sanction"
P_MANAGE = "elm.leave.manage"
P_EXPORT = "elm.leave.export"


def _actor(request):
    return request.principal


def _accessible(app, actor):
    is_pending_substitute = (
        app.substitute_user_id == actor.user_id and app.status == "awaiting_substitute"
    )
    return (
        app.applicant_user_id == actor.user_id
        or app.current_assignee_user_id == actor.user_id
        or is_pending_substitute
        or actor.has_permission(P_VIEW_ALL)
        or actor.has_permission(P_MANAGE)
    )


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_requests_list",
        request=None,
        responses=OpenApiTypes.OBJECT,
    ),
    post=extend_schema(
        operation_id="elm_leave_requests_create",
        request=LeaveApplicationInputSerializer,
        responses={201: LeaveApplicationSerializer},
    ),
)
class LeaveRequestListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            codes = (P_CREATE,)
        elif self.request.query_params.get("scope") == "assigned":
            codes = (P_VIEW_ALL, P_REVIEW, P_SANCTION, P_SUBSTITUTE, P_MANAGE)
        else:
            codes = (P_VIEW_SELF, P_VIEW_ALL, P_REVIEW, P_SANCTION, P_SUBSTITUTE, P_MANAGE)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        qs = LeaveApplication.objects.all()
        scope = request.query_params.get("scope")
        if scope == "mine":
            qs = qs.filter(applicant_user_id=actor.user_id)
        elif scope == "assigned":
            assigned = Q(current_assignee_user_id=actor.user_id) | Q(
                substitute_user_id=actor.user_id, status="awaiting_substitute"
            )
            if actor.has_permission(P_MANAGE):
                assigned |= Q(
                    current_assignee_user_id__isnull=True,
                    status__in=(
                        "awaiting_unit_head",
                        "awaiting_establishment",
                        "awaiting_sanction",
                        "awaiting_cancellation_sanction",
                        "awaiting_resumption_review",
                        "action_required",
                    ),
                )
            qs = qs.filter(assigned)
        elif actor.has_permission(P_VIEW_ALL) or actor.has_permission(P_MANAGE):
            pass
        elif (
            actor.has_permission(P_REVIEW)
            or actor.has_permission(P_SANCTION)
            or actor.has_permission(P_SUBSTITUTE)
        ):
            qs = qs.filter(
                Q(applicant_user_id=actor.user_id)
                | Q(current_assignee_user_id=actor.user_id)
                | Q(substitute_user_id=actor.user_id, status="awaiting_substitute")
            )
        else:
            qs = qs.filter(applicant_user_id=actor.user_id)
        status_filter = request.query_params.get("status")
        category_filter = request.query_params.get("category")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)
        data = LeaveApplicationSerializer(qs[:200], many=True).data
        return Response({"results": data, "next": None})

    def post(self, request):
        payload = LeaveApplicationInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = create_leave_application(_actor(request), payload.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_request_retrieve",
        request=None,
        responses=LeaveApplicationSerializer,
    )
)
class LeaveRequestDetailView(APIView):
    permission_classes = [
        MODULE,
        HasPermission(P_VIEW_SELF, P_VIEW_ALL, P_REVIEW, P_SANCTION, P_SUBSTITUTE, P_MANAGE),
    ]

    def get(self, request, pk):
        app = get_object_or_404(LeaveApplication, pk=pk)
        if not _accessible(app, _actor(request)):
            raise PermissionDenied("You cannot view this leave request.")
        return Response(LeaveApplicationSerializer(app).data)


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_substitute_response",
        request=SubstituteResponseSerializer,
        responses=OpenApiTypes.OBJECT,
    )
)
class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def post(self, request, pk):
        payload = SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = get_object_or_404(LeaveApplication, pk=pk)
        return Response(
            LeaveApplicationSerializer(
                respond_substitute(_actor(request), app, payload.validated_data["response"])
            ).data
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_retry_after_decline",
        request=RetryAfterDeclineSerializer,
        responses=LeaveApplicationSerializer,
    )
)
class RetryAfterDeclineView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        payload = RetryAfterDeclineSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = get_object_or_404(LeaveApplication, pk=pk)
        updated = retry_after_substitute_decline(
            _actor(request),
            app,
            payload.validated_data.get("substitute_user_id"),
        )
        return Response(LeaveApplicationSerializer(updated).data)


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_decision",
        request=DecisionSerializer,
        responses=OpenApiTypes.OBJECT,
    )
)
class LeaveDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW, P_SANCTION, P_MANAGE)]

    def post(self, request, pk):
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = get_object_or_404(LeaveApplication, pk=pk)
        actor = _actor(request)
        if app.status in {
            "awaiting_unit_head",
            "awaiting_cancellation_unit_head",
            "awaiting_establishment",
        } and not (actor.has_permission(P_REVIEW) or actor.has_permission(P_MANAGE)):
            raise PermissionDenied("This action requires ELM review permission.")
        if app.status in {
            "awaiting_sanction",
            "awaiting_cancellation_sanction",
            "awaiting_resumption_review",
        } and not (actor.has_permission(P_SANCTION) or actor.has_permission(P_MANAGE)):
            raise PermissionDenied("This action requires ELM sanction permission.")
        return Response(
            LeaveApplicationSerializer(
                decide_request(
                    actor,
                    app,
                    payload.validated_data["decision"],
                    payload.validated_data.get("note", ""),
                )
            ).data
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_withdraw",
        request=ActionReasonSerializer,
        responses=OpenApiTypes.OBJECT,
    )
)
class WithdrawRequestView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        payload = ActionReasonSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = get_object_or_404(LeaveApplication, pk=pk)
        return Response(
            LeaveApplicationSerializer(
                withdraw_request(_actor(request), app, payload.validated_data["reason"])
            ).data
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_cancel",
        request=ActionReasonSerializer,
        responses=OpenApiTypes.OBJECT,
    )
)
class CancelLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        payload = ActionReasonSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        parent = get_object_or_404(
            LeaveApplication, pk=pk, request_type__in=("leave", "offline", "extension")
        )
        return Response(
            LeaveApplicationSerializer(
                create_cancellation(_actor(request), parent, payload.validated_data["reason"])
            ).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_extend",
        request=ExtensionSerializer,
        responses=OpenApiTypes.OBJECT,
    )
)
class ExtendLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        payload = ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        parent = get_object_or_404(
            LeaveApplication, pk=pk, request_type__in=("leave", "extension", "offline")
        )
        data = payload.validated_data
        return Response(
            LeaveApplicationSerializer(
                create_extension(
                    _actor(request),
                    parent,
                    data["start_date"],
                    data["end_date"],
                    data.get("reason", ""),
                    data.get("substitute_user_id"),
                )
            ).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_resume",
        request=ResumptionSerializer,
        responses=OpenApiTypes.OBJECT,
    )
)
class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        payload = ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        parent = get_object_or_404(
            LeaveApplication, pk=pk, request_type__in=("leave", "extension", "offline")
        )
        data = payload.validated_data
        return Response(
            LeaveApplicationSerializer(
                create_resumption(
                    _actor(request), parent, data["actual_resumption_date"], data.get("details", "")
                )
            ).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_balances_list",
        request=None,
        responses=OpenApiTypes.OBJECT,
    )
)
class LeaveBalanceView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW_ALL, P_MANAGE)]

    def get(self, request):
        actor = _actor(request)
        requested_user = request.query_params.get("user_id")
        if requested_user and (actor.has_permission(P_VIEW_ALL) or actor.has_permission(P_MANAGE)):
            try:
                user_id = int(requested_user)
            except ValueError as exc:
                raise ValidationError({"user_id": "Must be an integer."}) from exc
            if user_id < 1 or user_id > 2147483647:
                raise ValidationError({"user_id": "Must be a positive 32-bit user ID."})
            kind = request.query_params.get("employee_kind", "staff")
        else:
            user_id = actor.user_id
            kind = _employee_kind(actor)
        if kind not in {"faculty", "staff"}:
            raise ValidationError({"employee_kind": "Must be faculty or staff."})
        try:
            year = int(request.query_params.get("year", timezone.localdate().year))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"year": "Must be a valid calendar year."}) from exc
        if year < 1900 or year > 9999:
            raise ValidationError({"year": "Must be between 1900 and 9999."})
        rows = []
        for policy in LeavePolicy.objects.filter(enabled=True).order_by("category"):
            balance = _balance(user_id, kind, year, policy.category)
            rows.append(
                {
                    "year": year,
                    "category": policy.category,
                    "entitlement": str(balance.entitlement),
                    "carried_in": str(balance.carried_in),
                    "converted_in": str(balance.converted_in),
                    "consumed": str(balance.consumed),
                    "lapsed": str(balance.lapsed),
                    "converted_out": str(balance.converted_out),
                    "available": str(balance.available),
                }
            )
        return Response({"results": rows})


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_application_export",
        request=None,
        responses=OpenApiTypes.STR,
    )
)
class LeaveApplicationExportView(APIView):
    permission_classes = [MODULE, HasPermission(P_EXPORT)]

    def get(self, request, pk):
        app = get_object_or_404(LeaveApplication, pk=pk)
        if app.applicant_user_id != _actor(request).user_id and not _actor(request).has_permission(
            P_VIEW_ALL
        ):
            raise PermissionDenied("You may export only your own leave application.")
        lines = [
            "Fusion ERP — Employee Leave Management",
            f"Request ID: EL-{app.pk}",
            f"Type: {app.request_type}",
            f"Employee ID: {app.applicant_user_id}",
            f"Category: {app.category}",
            f"Period: {app.start_date} to {app.end_date}",
            f"Requested days: {app.requested_days}",
            f"Purpose: {app.purpose}",
            f"Station Leave: {'Yes' if app.station_leave else 'No'}",
            f"Status: {app.status}",
            f"Decision: {app.final_decision or 'Pending'}",
            f"Decision note: {app.final_decision_note}",
        ]
        return Response("\n".join(lines), content_type="text/plain; charset=utf-8")


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_policies_list",
        request=None,
        responses=LeavePolicySerializer(many=True),
    )
)
class LeavePolicyListView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request):
        return Response(
            LeavePolicySerializer(LeavePolicy.objects.order_by("category"), many=True).data
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_policy_retrieve",
        request=None,
        responses=LeavePolicySerializer,
    ),
    patch=extend_schema(
        operation_id="elm_leave_policy_update",
        request=LeavePolicySerializer,
        responses=LeavePolicySerializer,
    ),
)
class LeavePolicyDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request, category):
        policy = get_object_or_404(LeavePolicy, category=category)
        return Response(LeavePolicySerializer(policy).data)

    def patch(self, request, category):
        policy = get_object_or_404(LeavePolicy, category=category)
        payload = LeavePolicySerializer(policy, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        payload.save()
        return Response(payload.data)


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_calendars_list",
        request=None,
        responses=LeaveCalendarSerializer(many=True),
    ),
    post=extend_schema(
        operation_id="elm_calendars_create",
        request=LeaveCalendarSerializer,
        responses={201: LeaveCalendarSerializer},
    ),
)
class LeaveCalendarView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request):
        return Response(LeaveCalendarSerializer(LeaveCalendar.objects.all()[:100], many=True).data)

    def post(self, request):
        payload = LeaveCalendarSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        calendar = payload.save(created_by_user_id=_actor(request).user_id)
        return Response(LeaveCalendarSerializer(calendar).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_calendar_dates_list",
        request=None,
        responses=LeaveCalendarDateSerializer(many=True),
    ),
    post=extend_schema(
        operation_id="elm_calendar_dates_create",
        request=LeaveCalendarDateSerializer,
        responses={201: LeaveCalendarDateSerializer},
    ),
)
class LeaveCalendarDateView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request, pk):
        get_object_or_404(LeaveCalendar, pk=pk)
        rows = LeaveCalendarDate.objects.filter(calendar_id=pk)
        return Response(LeaveCalendarDateSerializer(rows, many=True).data)

    def post(self, request, pk):
        get_object_or_404(LeaveCalendar, pk=pk, status="draft")
        payload = LeaveCalendarDateSerializer(data={**request.data, "calendar": pk})
        payload.is_valid(raise_exception=True)
        return Response(
            LeaveCalendarDateSerializer(payload.save()).data, status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_calendar_publish",
        request=None,
        responses=LeaveCalendarSerializer,
    )
)
class PublishLeaveCalendarView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def post(self, request, pk):
        with transaction.atomic():
            calendar = get_object_or_404(LeaveCalendar.objects.select_for_update(), pk=pk)
            LeaveCalendar.objects.filter(status="published", year=calendar.year).exclude(
                pk=calendar.pk
            ).update(status="draft", updated_at=timezone.now())
            calendar.status = "published"
            calendar.published_by_user_id = _actor(request).user_id
            calendar.published_at = timezone.now()
            calendar.save(
                update_fields=["status", "published_by_user_id", "published_at", "updated_at"]
            )
        return Response(LeaveCalendarSerializer(calendar).data)


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_hierarchy_list",
        request=None,
        responses=LeaveHierarchySerializer(many=True),
    ),
    post=extend_schema(
        operation_id="elm_leave_hierarchy_create",
        request=LeaveHierarchySerializer,
        responses={201: LeaveHierarchySerializer},
    ),
)
class LeaveHierarchyView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request):
        return Response(
            LeaveHierarchySerializer(LeaveHierarchy.objects.all()[:500], many=True).data
        )

    def post(self, request):
        payload = LeaveHierarchySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row, created = LeaveHierarchy.objects.update_or_create(
            unit_key=payload.validated_data["unit_key"], defaults=payload.validated_data
        )
        return Response(
            LeaveHierarchySerializer(row).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_vacation_periods_list",
        request=None,
        responses=OpenApiTypes.OBJECT,
    ),
    post=extend_schema(
        operation_id="elm_vacation_periods_create",
        request=VacationPeriodSerializer,
        responses={201: VacationPeriodSerializer},
    ),
)
class VacationPeriodListCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request):
        rows = VacationPeriod.objects.order_by("start_date", "id")[:500]
        return Response({"results": VacationPeriodSerializer(rows, many=True).data})

    def post(self, request):
        payload = VacationPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        period = payload.save()
        return Response(VacationPeriodSerializer(period).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_vacation_period_retrieve",
        request=None,
        responses=VacationPeriodSerializer,
    ),
    patch=extend_schema(
        operation_id="elm_vacation_period_update",
        request=VacationPeriodSerializer,
        responses=VacationPeriodSerializer,
    ),
    put=extend_schema(
        operation_id="elm_vacation_period_replace",
        request=VacationPeriodSerializer,
        responses=VacationPeriodSerializer,
    ),
    delete=extend_schema(
        operation_id="elm_vacation_period_delete",
        request=None,
        responses={204: OpenApiTypes.NONE},
    ),
)
class VacationPeriodDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request, pk):
        period = get_object_or_404(VacationPeriod, pk=pk)
        return Response(VacationPeriodSerializer(period).data)

    def patch(self, request, pk):
        period = get_object_or_404(VacationPeriod, pk=pk)
        payload = VacationPeriodSerializer(period, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        return Response(VacationPeriodSerializer(payload.save()).data)

    def put(self, request, pk):
        period = get_object_or_404(VacationPeriod, pk=pk)
        payload = VacationPeriodSerializer(period, data=request.data)
        payload.is_valid(raise_exception=True)
        return Response(VacationPeriodSerializer(payload.save()).data)

    def delete(self, request, pk):
        period = get_object_or_404(VacationPeriod, pk=pk)
        period.active = False
        period.save(update_fields=["active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_offline_leave_record_create",
        request=OfflineLeaveRecordSerializer,
        responses={201: LeaveApplicationSerializer},
    )
)
class OfflineLeaveRecordView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    @transaction.atomic
    def post(self, request):
        payload = OfflineLeaveRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if LeaveApplication.objects.filter(
            request_type="offline",
            evidence_reference=data["evidence_reference"],
        ).exists():
            raise ValidationError(
                {"evidence_reference": "This offline sanction has already been recorded."}
            )
        start, end, category = data["start_date"], data["end_date"], data["category"]
        from modules.elm.services import _days_by_year

        days_by_year = _days_by_year(category, start, end)
        total = sum((Decimal(value) for value in days_by_year.values()), Decimal("0"))
        if total <= 0:
            raise ValidationError(
                {"period": "The selected period contains no countable leave days."}
            )
        try:
            # Nested atomic creates a savepoint so a concurrent duplicate can be
            # translated into a validation response without poisoning the outer
            # transaction.
            with transaction.atomic():
                app = LeaveApplication.objects.create(
                    applicant_user_id=data["applicant_user_id"],
                    employee_kind=data["employee_kind"],
                    department=data["department"],
                    request_type="offline",
                    category=category,
                    start_date=start,
                    end_date=end,
                    requested_days=total,
                    requested_days_by_year=days_by_year,
                    purpose=data["purpose"],
                    status="approved",
                    final_decision="approved",
                    final_decided_at=timezone.now(),
                    final_decision_note=(
                        "Recorded from prior offline sanction; no second approval workflow."
                    ),
                    evidence_reference=data["evidence_reference"],
                )
        except IntegrityError as exc:
            if LeaveApplication.objects.filter(
                request_type="offline",
                evidence_reference=data["evidence_reference"],
            ).exists():
                raise ValidationError(
                    {"evidence_reference": "This offline sanction has already been recorded."}
                ) from exc
            raise
        post_application_balance(app, _actor(request).user_id)
        _record(
            app,
            _actor(request).user_id,
            "offline_synchronized",
            "offline",
            "approved",
            app.evidence_reference,
        )
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_sla_config_retrieve",
        request=None,
        responses=OpenApiTypes.OBJECT,
    ),
    put=extend_schema(
        operation_id="elm_leave_sla_config_update",
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
    ),
)
class LeaveSLAConfigView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def get(self, request):
        config = LeaveSLAConfig.objects.order_by("id").first() or LeaveSLAConfig.objects.create()
        return Response(
            {
                "reminder_after_hours": config.reminder_after_hours,
                "escalation_after_hours": config.escalation_after_hours,
                "escalation_user_id": config.escalation_user_id,
            }
        )

    def put(self, request):
        config = LeaveSLAConfig.objects.order_by("id").first() or LeaveSLAConfig.objects.create()
        reminder = request.data.get("reminder_after_hours", config.reminder_after_hours)
        escalation = request.data.get("escalation_after_hours", config.escalation_after_hours)
        if (
            isinstance(reminder, bool)
            or isinstance(escalation, bool)
            or (isinstance(reminder, float) and not reminder.is_integer())
            or (isinstance(escalation, float) and not escalation.is_integer())
        ):
            raise ValidationError({"thresholds": "SLA thresholds must be whole-number hours."})
        try:
            reminder, escalation = int(reminder), int(escalation)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"thresholds": "SLA thresholds must be integer hours."}) from exc
        if reminder < 1 or escalation <= reminder or reminder > 65535 or escalation > 65535:
            raise ValidationError(
                {
                    "thresholds": (
                        "Use positive hour thresholds up to 65535, "
                        "with escalation greater than reminder."
                    )
                }
            )
        raw_escalation_user = request.data.get("escalation_user_id")
        if raw_escalation_user in (None, ""):
            escalation_user = None
        else:
            if isinstance(raw_escalation_user, bool) or (
                isinstance(raw_escalation_user, float) and not raw_escalation_user.is_integer()
            ):
                raise ValidationError(
                    {"escalation_user_id": "Must be a whole positive integer or blank."}
                )
            try:
                escalation_user = int(raw_escalation_user)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    {"escalation_user_id": "Must be a positive integer or blank."}
                ) from exc
            if escalation_user < 1 or escalation_user > 2147483647:
                raise ValidationError(
                    {"escalation_user_id": "Must be a positive 32-bit integer or blank."}
                )
        config.reminder_after_hours = reminder
        config.escalation_after_hours = escalation
        config.escalation_user_id = escalation_user
        config.save()
        return Response(
            {
                "reminder_after_hours": reminder,
                "escalation_after_hours": escalation,
                "escalation_user_id": config.escalation_user_id,
            }
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="elm_leave_notices_list",
        request=None,
        responses=OpenApiTypes.OBJECT,
    )
)
class LeaveNoticesView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        rows = LeaveNotice.objects.filter(user_id=_actor(request).user_id)[:100]
        return Response(
            {
                "results": [
                    {
                        "id": r.id,
                        "kind": r.kind,
                        "message": r.message,
                        "application_id": r.application_id,
                        "created_at": r.created_at,
                        "read_at": r.read_at,
                    }
                    for r in rows
                ]
            }
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_year_end_process",
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
    )
)
class LeaveYearEndView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def post(self, request):
        year = request.data.get("year")
        if isinstance(year, bool) or (isinstance(year, float) and not year.is_integer()):
            raise ValidationError({"year": "Provide a whole-number calendar year."})
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"year": "Provide a calendar year."}) from exc
        if year < 1900 or year > 9999:
            raise ValidationError({"year": "Must be between 1900 and 9999."})
        run = process_year_end(year, _actor(request).user_id)
        return Response(
            {
                "year": run.year,
                "processed_accounts": run.processed_accounts,
                "exceptions": run.exceptions,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    post=extend_schema(
        operation_id="elm_leave_sla_process",
        request=None,
        responses=OpenApiTypes.OBJECT,
    )
)
class ProcessSLAView(APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE)]

    def post(self, request):
        created = process_sla_thresholds()
        return Response({"events_created": created})
