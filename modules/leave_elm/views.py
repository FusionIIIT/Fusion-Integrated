from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave_elm import serializers as s
from modules.leave_elm import services
from modules.leave_elm.models import (
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeaveHierarchy,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveResumption,
    LeaveSLAConfig,
    LeaveYearEndConfig,
    VacationPeriod,
)

MODULE = HasModuleGrant("leave_elm")


class _LeaveView(APIView):
    permission_classes = [IsAuthenticated, MODULE]


@extend_schema(
    request=s.LeaveApplicationCreateSerializer,
    responses={201: s.LeaveApplicationSerializer},
)
class ApplyView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_APPLY)]

    def post(self, request):
        payload = s.LeaveApplicationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = services.apply_leave(request.principal, payload.validated_data)
        return Response(
            s.LeaveApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class MyApplicationsView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(
        services.P_VIEW_SELF, "leave_elm.view.all",
    )]
    serializer_class = s.LeaveApplicationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        actor = self.request.principal
        queryset = LeaveApplication.objects.all()
        if not services.has_permission(actor, "leave_elm.view.all"):
            queryset = queryset.filter(employee_id=actor.user_id)
        return queryset.prefetch_related("decisions").order_by("-created_at")


@extend_schema(responses=s.LeaveBalanceSerializer(many=True))
class MyBalancesView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_VIEW_SELF)]

    def get(self, request):
        actor = request.principal
        if actor.kind not in {"faculty", "staff"}:
            return Response({"detail": "Employee access only."}, status=403)
        year = timezone.localdate().year
        balances = [
            services.get_balance(actor.user_id, actor.kind, category, year)
            for category, _ in LeavePolicy.CATEGORIES
            if getattr(LeavePolicy.objects.get(category=category),
                       f"{actor.kind}_eligible")
        ]
        return Response(s.LeaveBalanceSerializer(balances, many=True).data)


@extend_schema(responses=s.LeaveLedgerSerializer(many=True))
class MyLedgerView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_VIEW_SELF)]

    def get(self, request):
        rows = LeaveLedgerEntry.objects.filter(
            balance__employee_id=request.principal.user_id,
        ).select_related("balance").order_by("-created_at")
        return Response(s.LeaveLedgerSerializer(rows[:200], many=True).data)


class ApprovalQueueView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(
        "leave_elm.review.queue",
        services.P_REVIEW_UNIT,
        services.P_REVIEW_ESTABLISHMENT,
        services.P_REVIEW_FINAL,
    )]
    serializer_class = s.LeaveApplicationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        actor = self.request.principal
        return LeaveApplication.objects.filter(
            assigned_user_id=actor.user_id,
            status__in=(
                "substitute_response", "unit_head_review",
                "establishment_review", "final_review",
            ),
        ).prefetch_related("decisions").order_by("assigned_at")


@extend_schema(
    request=s.LeaveDecisionInputSerializer,
    responses=s.LeaveApplicationSerializer,
)
class DecisionView(_LeaveView):
    permission_classes = [MODULE, HasPermission(
        services.P_REVIEW_UNIT,
        services.P_REVIEW_ESTABLISHMENT,
        services.P_REVIEW_FINAL,
    )]

    def post(self, request, application_id):
        payload = s.LeaveDecisionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = get_object_or_404(
            LeaveApplication,
            pk=application_id,
            assigned_user_id=request.principal.user_id,
        )
        decision = payload.validated_data["decision"]
        if app.status == "unit_head_review" and app.category not in {"CL", "RH"}:
            recommendation = payload.validated_data.get("recommendation")
            if recommendation is not None:
                decision = "approve" if recommendation == "recommended" else "reject"
        result = services.decide(
            request.principal, application_id, decision,
            payload.validated_data.get("note", ""),
        )
        return Response(s.LeaveApplicationSerializer(result).data)


@extend_schema(
    request=inline_serializer(
        name="SubstituteResponseInput",
        fields={"accept": serializers.BooleanField()},
    ),
    responses=s.LeaveApplicationSerializer,
)
class SubstituteResponseView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.substitute.respond")]

    def post(self, request, application_id):
        accepted = request.data.get("accept")
        if not isinstance(accepted, bool):
            return Response({"accept": "Must be true or false."}, status=400)
        result = services.respond_substitute(request.principal, application_id, accepted)
        return Response(s.LeaveApplicationSerializer(result).data)


@extend_schema(
    request=s.SubstituteReplacementSerializer,
    responses=s.LeaveApplicationSerializer,
)
class SubstituteReplacementView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_VIEW_SELF)]

    def post(self, request, application_id):
        payload = s.SubstituteReplacementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        result = services.replace_substitute(
            request.principal, application_id,
            payload.validated_data["substitute_user_id"],
        )
        return Response(s.LeaveApplicationSerializer(result).data)


@extend_schema(request=None, responses=s.LeaveApplicationSerializer)
class WithdrawView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_VIEW_SELF)]

    def post(self, request, application_id):
        result = services.withdraw(request.principal, application_id)
        return Response(s.LeaveApplicationSerializer(result).data)


@extend_schema(request=None, responses={201: s.LeaveApplicationSerializer})
class CancellationView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.cancel.self")]

    def post(self, request, application_id):
        result = services.request_cancellation(request.principal, application_id)
        return Response(s.LeaveApplicationSerializer(result).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(
    request=s.ExtensionSerializer,
    responses={201: s.LeaveApplicationSerializer},
)
class ExtensionView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.extend.self")]

    def post(self, request, application_id):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        result = services.request_extension(
            request.principal, application_id, payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(result).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(
    request=s.ResumptionInputSerializer,
    responses={201: s.LeaveResumptionSerializer},
)
class ResumptionView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.resume.self")]

    def post(self, request, application_id):
        payload = s.ResumptionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        result = services.submit_resumption(
            request.principal, application_id,
            payload.validated_data["actual_resume_date"],
            payload.validated_data["details"],
        )
        return Response(s.LeaveResumptionSerializer(result).data,
                        status=status.HTTP_201_CREATED)


class ResumptionQueueView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(services.P_REVIEW_FINAL)]
    serializer_class = s.LeaveResumptionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveResumption.objects.none()
        return LeaveResumption.objects.filter(
            assigned_user_id=self.request.principal.user_id,
            status="pending",
        ).order_by("created_at")


@extend_schema(
    request=s.ResumptionReviewSerializer,
    responses=s.LeaveResumptionSerializer,
)
class ResumptionDecisionView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_REVIEW_FINAL)]

    def post(self, request, resumption_id):
        payload = s.ResumptionReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        resumption = services.review_resumption(
            request.principal, resumption_id,
            payload.validated_data["decision"],
            payload.validated_data.get("note", ""),
        )
        return Response(s.LeaveResumptionSerializer(resumption).data)


class PolicyListView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.policy")]
    http_method_names = ["get", "head", "options"]

    @extend_schema(
        operation_id="leave_admin_policy_list",
        responses=s.LeavePolicySerializer(many=True),
    )
    def get(self, request):
        return Response(s.LeavePolicySerializer(
            LeavePolicy.objects.all().order_by("category"), many=True,
        ).data)


class PolicyDetailView(PolicyListView):
    http_method_names = ["put", "options"]

    @extend_schema(
        operation_id="leave_admin_policy_update",
        request=s.LeavePolicySerializer,
        responses=s.LeavePolicySerializer,
    )
    def put(self, request, category):
        policy = get_object_or_404(LeavePolicy, category=category)
        payload = s.LeavePolicySerializer(policy, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        payload.save()
        return Response(payload.data)


class HierarchyView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.policy")]

    @extend_schema(responses=s.LeaveHierarchySerializer(many=True))
    def get(self, request):
        return Response(s.LeaveHierarchySerializer(
            LeaveHierarchy.objects.all().order_by("department", "category"),
            many=True,
        ).data)

    @extend_schema(
        request=s.LeaveHierarchySerializer,
        responses={201: s.LeaveHierarchySerializer},
    )
    def post(self, request):
        payload = s.LeaveHierarchySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        hierarchy, _ = LeaveHierarchy.objects.update_or_create(
            department=data["department"],
            category=data["category"],
            defaults={
                **data,
                "updated_by_user_id": request.principal.user_id,
            },
        )
        return Response(s.LeaveHierarchySerializer(hierarchy).data,
                        status=status.HTTP_201_CREATED)


class HolidayCalendarView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.calendar")]

    @extend_schema(responses=s.HolidayCalendarSerializer(many=True))
    def get(self, request):
        return Response(s.HolidayCalendarSerializer(
            HolidayCalendar.objects.prefetch_related("dates"), many=True,
        ).data)

    @extend_schema(
        request=s.HolidayCalendarSerializer,
        responses={201: s.HolidayCalendarSerializer},
    )
    def post(self, request):
        payload = s.HolidayCalendarSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        dates = values.pop("dates")
        with transaction.atomic():
            calendar = HolidayCalendar.objects.create(
                **values,
                created_by_user_id=request.principal.user_id,
            )
            HolidayDate.objects.bulk_create([
                HolidayDate(calendar=calendar, **row) for row in dates
            ])
        return Response(s.HolidayCalendarSerializer(calendar).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.HolidayCalendarSerializer)
class PublishCalendarView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.calendar")]

    def post(self, request, calendar_id):
        calendar = get_object_or_404(HolidayCalendar, pk=calendar_id)
        calendar.publish()
        return Response(s.HolidayCalendarSerializer(calendar).data)


class VacationPeriodView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.calendar")]

    @extend_schema(responses=s.VacationPeriodSerializer(many=True))
    def get(self, request):
        return Response(s.VacationPeriodSerializer(
            VacationPeriod.objects.order_by("year", "start_date"), many=True,
        ).data)

    @extend_schema(
        request=s.VacationPeriodSerializer,
        responses={201: s.VacationPeriodSerializer},
    )
    def post(self, request):
        payload = s.VacationPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        period = payload.save()
        return Response(s.VacationPeriodSerializer(period).data,
                        status=status.HTTP_201_CREATED)


class SLAConfigListView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.sla")]
    http_method_names = ["get", "put", "head", "options"]

    @extend_schema(
        operation_id="leave_admin_sla_list",
        responses=s.LeaveSLAConfigSerializer(many=True),
    )
    def get(self, request):
        return Response(s.LeaveSLAConfigSerializer(
            LeaveSLAConfig.objects.order_by("request_type"), many=True,
        ).data)

    @extend_schema(
        operation_id="leave_admin_sla_create",
        request=s.LeaveSLAConfigSerializer,
        responses={200: s.LeaveSLAConfigSerializer,
                   201: s.LeaveSLAConfigSerializer},
    )
    def put(self, request):
        payload = s.LeaveSLAConfigSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        result = payload.save()
        return Response(s.LeaveSLAConfigSerializer(result).data,
                        status=status.HTTP_201_CREATED)


class SLAConfigDetailView(SLAConfigListView):
    http_method_names = ["put", "options"]

    @extend_schema(
        operation_id="leave_admin_sla_update",
        request=s.LeaveSLAConfigSerializer,
        responses=s.LeaveSLAConfigSerializer,
    )
    def put(self, request, config_id):
        config = get_object_or_404(LeaveSLAConfig, pk=config_id)
        payload = s.LeaveSLAConfigSerializer(config, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        result = payload.save()
        return Response(s.LeaveSLAConfigSerializer(result).data)


@extend_schema(
    request=s.OfflineLeaveSerializer,
    responses={201: s.LeaveApplicationSerializer},
)
class OfflineLeaveView(_LeaveView):
    permission_classes = [MODULE, HasPermission(services.P_MANAGE_RECORDS)]

    def post(self, request):
        payload = s.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = services.record_offline_leave(
            request.principal, payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(application).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.YearEndInputSerializer, responses=OpenApiTypes.OBJECT)
class YearEndView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.records")]

    def post(self, request):
        payload = s.YearEndInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        completed = services.process_year_end(payload.validated_data["year"])
        return Response({"processed_employees": completed})


class YearEndConfigView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.records")]

    @extend_schema(responses=s.LeaveYearEndConfigSerializer)
    def get(self, request):
        config = LeaveYearEndConfig.objects.first()
        return Response(
            None if config is None else s.LeaveYearEndConfigSerializer(config).data,
        )

    @extend_schema(
        request=s.LeaveYearEndConfigSerializer,
        responses=s.LeaveYearEndConfigSerializer,
    )
    def put(self, request):
        payload = s.LeaveYearEndConfigSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        config, _ = LeaveYearEndConfig.objects.update_or_create(
            pk=1,
            defaults={
                **payload.validated_data,
                "updated_by_user_id": request.principal.user_id,
            },
        )
        return Response(s.LeaveYearEndConfigSerializer(config).data)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
class ProcessConfiguredYearEndView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.records")]

    def post(self, request):
        return Response(services.process_configured_year_end())


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
class ProcessSLAView(_LeaveView):
    permission_classes = [MODULE, HasPermission("leave_elm.manage.sla")]

    def post(self, request):
        return Response(services.process_sla_thresholds())
