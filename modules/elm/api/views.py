"""ELM API views. Every collection is scoped to the authenticated principal."""

import csv
from io import StringIO

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm import selectors
from modules.elm.api import serializers as s
from modules.elm.models import (
    AdminAuditEvent,
    ApprovalRoute,
    ELMNotification,
    LeaveCategory,
    SLAConfiguration,
)
from modules.elm.services import workflow as service

MODULE = HasModuleGrant("elm")
P_VIEW, P_CREATE, P_WITHDRAW = "elm.request.view_self", "elm.request.create", "elm.request.withdraw"
P_SUB, P_REVIEW = "elm.substitute.respond", "elm.workflow.review"
P_POLICY, P_CALENDAR, P_ACCOUNT = "elm.policy.manage", "elm.calendar.manage", "elm.account.manage"
P_SLA = "elm.sla.manage"
P_EXPORT = "elm.report.export"


def _actor(request):
    return request.principal


class MyRequestsView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = selectors.history(user_id=_actor(request).user_id)
        return Response({"results": s.LeaveRequestSerializer(rows, many=True).data})

    @extend_schema(request=s.NewRequestSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        payload = s.NewRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.submit(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class MyBalancesView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=dict)
    def get(self, request):
        raw_year = request.query_params.get("year")
        try:
            year = int(raw_year) if raw_year else timezone.localdate().year
        except ValueError:
            from core.api.exceptions import BadRequestError

            raise BadRequestError("year must be a number.", code="invalid_year") from None
        return Response(
            {
                "year": year,
                "results": selectors.balances(user_id=_actor(request).user_id, year=year),
            }
        )


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=None, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        row = service.withdraw(request_id=pk, actor=_actor(request))
        return Response(s.LeaveRequestSerializer(row).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUB, P_CREATE)]

    @extend_schema(request=s.SubstituteSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.SubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.substitute_response(
            request_id=pk, actor=_actor(request), **payload.validated_data
        )
        return Response(s.LeaveRequestSerializer(row).data)


class CancellationView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.CancellationSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request, pk):
        payload = s.CancellationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.cancel(request_id=pk, actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class ExtensionView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.ExtensionSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.extend(request_id=pk, actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.ResumptionInputSerializer, responses={201: s.ResumptionSerializer})
    def post(self, request, pk):
        payload = s.ResumptionInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.report_resumption(
            request_id=pk, actor=_actor(request), **payload.validated_data
        )
        return Response(s.ResumptionSerializer(row).data, status=status.HTTP_201_CREATED)


class TasksView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUB, P_REVIEW)]

    @extend_schema(responses=s.TaskSerializer(many=True))
    def get(self, request):
        rows = selectors.tasks_for(user_id=_actor(request).user_id)
        return Response({"results": s.TaskSerializer(rows, many=True).data})


class ReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.ReviewSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.review(request_id=pk, actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data)


class ResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.ResumptionReviewSerializer, responses=s.ResumptionSerializer)
    def post(self, request, pk):
        payload = s.ResumptionReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.review_resumption(
            resumption_id=pk, actor=_actor(request), **payload.validated_data
        )
        return Response(s.ResumptionSerializer(row).data)


class NotificationsView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=s.NotificationSerializer(many=True))
    def get(self, request):
        rows = ELMNotification.objects.filter(user_id=_actor(request).user_id).order_by(
            "-created_at"
        )[:100]
        return Response({"results": s.NotificationSerializer(rows, many=True).data})


class ExportView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_EXPORT)]

    @extend_schema(responses={"200": {"type": "string", "format": "binary"}})
    def get(self, request):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            (
                "request_id",
                "category",
                "starts_on",
                "ends_on",
                "chargeable_days",
                "status",
                "reason",
                "submitted_at",
            )
        )
        for row in selectors.export_rows(user_id=_actor(request).user_id):
            writer.writerow(row)
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="my-leave-history.csv"'
        return response


class CategoriesAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(responses=dict)
    def get(self, request):
        rows = LeaveCategory.objects.all().order_by("code").values()
        return Response({"results": list(rows)})

    @extend_schema(request=s.LeaveCategoryInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.LeaveCategoryInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.configure_category(actor=_actor(request), values=payload.validated_data)
        return Response(
            {"id": row.pk, "code": row.code, "name": row.name}, status=status.HTTP_201_CREATED
        )


class EmployeeContextAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(request=s.EmployeeContextInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.EmployeeContextInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.configure_employee(actor=_actor(request), values=payload.validated_data)
        return Response(
            {"user_id": row.user_id, "employee_kind": row.employee_kind},
            status=status.HTTP_201_CREATED,
        )


class ApprovalRoutesAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(responses=dict)
    def get(self, request):
        rows = ApprovalRoute.objects.order_by("employee_kind", "category").values()
        return Response({"results": list(rows)})

    @extend_schema(request=s.ApprovalRouteInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.ApprovalRouteInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.configure_route(actor=_actor(request), values=payload.validated_data)
        return Response(
            {
                "id": row.pk,
                "category": row.category,
                "final_authority_user_id": row.final_authority_user_id,
            },
            status=status.HTTP_201_CREATED,
        )


class CalendarAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=s.CalendarInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.CalendarInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.create_calendar(actor=_actor(request), **payload.validated_data)
        return Response(
            {"id": row.pk, "name": row.name, "is_published": row.is_published},
            status=status.HTTP_201_CREATED,
        )


class CalendarEntryAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=s.CalendarEntryInputSerializer, responses={201: dict})
    def post(self, request, pk):
        payload = s.CalendarEntryInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.calendar_entry(
            actor=_actor(request), calendar_id=pk, **payload.validated_data
        )
        return Response(
            {"id": row.pk, "day": row.day, "kind": row.kind}, status=status.HTTP_201_CREATED
        )


class CalendarPublishAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=None, responses=dict)
    def post(self, request, pk):
        row = service.publish_calendar(actor=_actor(request), calendar_id=pk)
        return Response(
            {"id": row.pk, "is_published": row.is_published, "published_at": row.published_at}
        )


class VacationAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=s.VacationInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.VacationInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.configure_vacation(actor=_actor(request), **payload.validated_data)
        return Response(
            {
                "id": row.pk,
                "name": row.name,
                "starts_on": row.starts_on,
                "ends_on": row.ends_on,
                "source_reference": row.source_reference,
            },
            status=status.HTTP_201_CREATED,
        )


class AccountsAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_ACCOUNT)]

    @extend_schema(request=s.AccountInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.AccountInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.create_account(actor=_actor(request), **payload.validated_data)
        return Response(
            {"id": row.pk, "user_id": row.user_id, "category": row.category.code, "year": row.year},
            status=status.HTTP_201_CREATED,
        )


class AccountAdjustmentAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_ACCOUNT)]

    @extend_schema(request=s.AccountAdjustmentSerializer, responses={201: dict})
    def post(self, request):
        payload = s.AccountAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.adjust_account(actor=_actor(request), **payload.validated_data)
        return Response(
            {"id": row.pk, "kind": row.kind, "amount": row.amount}, status=status.HTTP_201_CREATED
        )


class OfflineRecordAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_ACCOUNT)]

    @extend_schema(request=s.OfflineInputSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        payload = s.OfflineInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.record_offline(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class SLAAdminView(APIView):
    permission_classes = [MODULE, HasPermission(P_SLA)]

    @extend_schema(responses=dict)
    def get(self, request):
        return Response({"results": list(SLAConfiguration.objects.order_by("task_type").values())})

    @extend_schema(request=s.SLAInputSerializer, responses={201: dict})
    def post(self, request):
        payload = s.SLAInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = service.configure_sla(actor=_actor(request), values=payload.validated_data)
        return Response(
            {
                "task_type": row.task_type,
                "reminder_after_hours": row.reminder_after_hours,
                "escalation_after_hours": row.escalation_after_hours,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminAuditView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY, P_ACCOUNT)]

    @extend_schema(responses=dict)
    def get(self, request):
        rows = AdminAuditEvent.objects.order_by("-created_at").values(
            "id", "actor_user_id", "target_type", "target_id", "event_type", "details", "created_at"
        )[:200]
        return Response({"results": list(rows)})
