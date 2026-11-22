from django.http import HttpResponse
from django.utils.html import format_html, format_html_join
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.employee_leave.api import serializers as s
from modules.employee_leave.models import (
    LeaveHoliday,
    LeaveLedgerEntry,
    LeavePolicy,
)
from modules.employee_leave.services import (
    P_ADMIN,
    P_BALANCE,
    P_ESTABLISHMENT,
    P_FINAL,
    P_OFFLINE,
    P_UNIT_HEAD,
    acknowledge_task_notice,
    act,
    assigned_tasks,
    employee_balances,
    maintain_balance,
    process_year_end,
    record_offline,
    request_extension,
    submit,
    task_notices_for,
    visible_requests,
)

MODULE = HasModuleGrant("employee_leave")


def _actor(request):
    return request.principal


def _serialize_requests(rows, *, many=True):
    rows = list(rows) if many else rows
    ids = [row.employee_id for row in rows] if many else [rows.employee_id]
    people = directory.get_users(ids)
    names = {user_id: person.display_name for user_id, person in people.items()}
    return s.LeaveRequestSerializer(rows, many=many, context={"employee_names": names}).data


class LeaveRequestListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = visible_requests(_actor(request)).order_by("-created_at")
        if request.query_params.get("status"):
            rows = rows.filter(status=request.query_params["status"])
        return Response(_serialize_requests(rows))

    @extend_schema(
        request=s.LeaveRequestCreateSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request):
        payload = s.LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = submit(actor=_actor(request), **payload.validated_data)
        return Response(
            _serialize_requests(leave_request, many=False), status=status.HTTP_201_CREATED
        )


class LeaveRequestActionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(request=s.LeaveActionSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.LeaveActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = act(request_id=pk, actor=_actor(request), **payload.validated_data)
        return Response(_serialize_requests(leave_request, many=False))


class LeaveExtensionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.LeaveExtensionCreateSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request, pk):
        payload = s.LeaveExtensionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        extension = request_extension(
            request_id=pk, actor=_actor(request), **payload.validated_data
        )
        return Response(_serialize_requests(extension, many=False), status=status.HTTP_201_CREATED)


class LeaveRequestPrintView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.STR, description="Printable HTML leave request"
            )
        }
    )
    def get(self, request, pk):
        leave_request = visible_requests(_actor(request)).filter(pk=pk).first()
        if leave_request is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("No such leave request.")
        person = directory.get_users([leave_request.employee_id]).get(leave_request.employee_id)
        employee_name = person.display_name if person else str(leave_request.employee_id)
        details = format_html_join(
            "",
            "<tr><th>{}</th><td>{}</td></tr>",
            (
                ("Employee", employee_name),
                ("Category", leave_request.leave_type),
                ("Period", f"{leave_request.start_date} to {leave_request.end_date}"),
                ("Charged days", leave_request.charged_days),
                ("Status", leave_request.get_status_display()),
                ("Reason", leave_request.reason),
                ("Station leave details", leave_request.station_leave_details or "None"),
                ("Final decision", leave_request.final_decision or "Pending"),
            ),
        )
        history = format_html_join(
            "",
            "<li><strong>{}</strong>: {} <time>{}</time><p>{}</p></li>",
            (
                (d.action, d.to_status, d.created_at, d.comment or "")
                for d in leave_request.decisions.all()
            ),
        )
        document = format_html(
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<title>Leave request {}</title><style>body{{font:16px sans-serif;"
            "max-width:800px;margin:40px auto}}table{{border-collapse:collapse;width:100%}}"
            "th,td{{border-bottom:1px solid #bbb;padding:10px;text-align:left}}"
            "@media print{{button{{display:none}}}}</style><h1>Leave request {}</h1>"
            "<table>{}</table><h2>Decision history</h2><ol>{}</ol>"
            "<button onclick='window.print()'>Print</button></html>",
            leave_request.pk,
            leave_request.pk,
            details,
            history,
        )
        response = HttpResponse(document, content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'inline; filename="leave-{leave_request.pk}.html"'
        return response


class LeaveBalanceView(APIView):
    permission_classes = [MODULE, HasPermission("employee_leave.balance.view_self")]

    @extend_schema(responses=s.LeaveBalanceSummarySerializer)
    def get(self, request):
        balances = employee_balances(_actor(request).user_id).select_related("policy")
        return Response(
            {
                "balances": s.LeaveBalanceSerializer(balances, many=True).data,
                "history": s.LeaveLedgerSerializer(
                    LeaveLedgerEntry.objects.filter(balance__user_id=_actor(request).user_id)
                    .select_related("balance")
                    .order_by("-created_at")[:100],
                    many=True,
                ).data,
            }
        )


class LeaveTaskQueueView(APIView):
    permission_classes = [
        MODULE,
        HasPermission(
            "employee_leave.request.work_queue",
            "employee_leave.request.respond_substitute",
            P_UNIT_HEAD,
            P_ESTABLISHMENT,
            P_FINAL,
        ),
    ]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = assigned_tasks(_actor(request)).order_by("created_at")
        return Response(_serialize_requests(rows))


class LeaveTaskNoticeListView(APIView):
    permission_classes = [
        MODULE,
        HasPermission(
            "employee_leave.request.work_queue",
            "employee_leave.request.respond_substitute",
            P_UNIT_HEAD,
            P_ESTABLISHMENT,
            P_FINAL,
        ),
    ]

    @extend_schema(responses=s.LeaveTaskNoticeSerializer(many=True))
    def get(self, request):
        rows = task_notices_for(_actor(request))[:100]
        return Response(s.LeaveTaskNoticeSerializer(rows, many=True).data)


class LeaveTaskNoticeReadView(APIView):
    permission_classes = [MODULE]

    @extend_schema(request=None, responses=s.LeaveTaskNoticeSerializer)
    def post(self, request, pk):
        notice = acknowledge_task_notice(actor=_actor(request), notice_id=pk)
        return Response(s.LeaveTaskNoticeSerializer(notice).data)


class LeavePolicyView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    queryset = LeavePolicy.objects.all()
    serializer_class = s.LeavePolicySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [MODULE()]
        return [MODULE(), HasPermission(P_ADMIN)()]

    def perform_create(self, serializer):
        serializer.save()


class LeavePolicyDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [MODULE]
    queryset = LeavePolicy.objects.all()
    serializer_class = s.LeavePolicySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [MODULE()]
        return [MODULE(), HasPermission(P_ADMIN)()]


class LeaveHolidayView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    queryset = LeaveHoliday.objects.none()
    serializer_class = s.LeaveHolidaySerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveHoliday.objects.none()
        rows = LeaveHoliday.objects.all()
        if not _actor(self.request).has_permission(P_ADMIN):
            rows = rows.filter(published=True)
        return rows

    def get_permissions(self):
        if self.request.method == "GET":
            return [MODULE()]
        return [MODULE(), HasPermission(P_ADMIN)()]


class LeaveHolidayPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_ADMIN)]

    @extend_schema(request=None, responses=s.LeaveHolidaySerializer)
    def post(self, request, pk):
        holiday = LeaveHoliday.objects.filter(pk=pk).first()
        if holiday is None:
            from core.api.exceptions import NotFoundError

            raise NotFoundError("No such calendar entry.")
        holiday.published = True
        holiday.save(update_fields=("published", "updated_at"))
        return Response(s.LeaveHolidaySerializer(holiday).data)


class LeaveBalanceAdjustmentView(APIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE)]

    @extend_schema(
        request=s.BalanceAdjustmentSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveLedgerSerializer},
    )
    def post(self, request):
        payload = s.BalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        entry = maintain_balance(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveLedgerSerializer(entry).data, status=status.HTTP_201_CREATED)


class OfflineLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_OFFLINE)]

    @extend_schema(
        request=s.OfflineLeaveSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveRequestSerializer},
    )
    def post(self, request):
        payload = s.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_request = record_offline(actor=_actor(request), **payload.validated_data)
        return Response(
            _serialize_requests(leave_request, many=False),
            status=status.HTTP_201_CREATED,
        )


class LeaveYearEndView(APIView):
    permission_classes = [MODULE, HasPermission(P_ADMIN)]

    @extend_schema(
        request=s.YearEndProcessSerializer,
        responses={status.HTTP_201_CREATED: s.LeaveYearEndRunSerializer},
    )
    def post(self, request):
        payload = s.YearEndProcessSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        run = process_year_end(actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveYearEndRunSerializer(run).data, status=status.HTTP_201_CREATED)
