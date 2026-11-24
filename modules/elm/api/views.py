"""API views for Employee Leave Management."""

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    ApplicationInputSerializer,
    BalanceAllotSerializer,
    BalanceSerializer,
    DecisionInputSerializer,
    ElmLeaveApplicationSerializer,
    EventSerializer,
    ExtensionInputSerializer,
    HolidaySerializer,
    LeaveAccountTransactionSerializer,
    LeaveTypeInfoSerializer,
    NotificationSerializer,
    OfflineLeaveInputSerializer,
    PrintableApplicationSerializer,
    ProfileSerializer,
    ReplacementSubstituteInputSerializer,
    ResumptionInputSerializer,
    SlaConfigSerializer,
    SlaProcessOutputSerializer,
    YearEndInputSerializer,
    YearEndOutputSerializer,
)
from modules.elm.domain.policy import DEFAULT_ENTITLEMENTS
from modules.elm.models import EmployeeLeaveProfile, Holiday, SlaConfig
from modules.elm.selectors.queries import (
    get_accessible_application,
    list_account_transactions,
    list_approval_queue,
    list_employee_applications,
    list_employee_balances,
    list_holidays,
    list_notifications,
    list_profiles,
    list_sla_configs,
)
from modules.elm.services.leave import (
    allot_balance,
    decide,
    execute_year_end_processing,
    nominate_replacement_substitute,
    process_sla_thresholds,
    record_offline_leave,
    request_cancellation,
    review_resumption,
    submit,
    submit_extension,
    submit_resumption,
    upsert_holiday,
    upsert_profile,
    withdraw,
)

MODULE = HasModuleGrant("leave_elm")
VIEW = HasPermission("leave_elm.application.view")
APPLY = HasPermission("leave_elm.application.apply")
REVIEW = HasPermission("leave_elm.application.approve")
BALANCE = HasPermission("leave_elm.balance.view")
ADMIN = HasPermission("leave_elm.policy.manage")


class LeaveTypesView(GenericAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = LeaveTypeInfoSerializer

    def get(self, request):
        return Response(
            [
                {"code": key, "label": label, "default_entitlement": DEFAULT_ENTITLEMENTS[key]}
                for key, label in (
                    ("CL", "Casual Leave"),
                    ("RH", "Restricted Holiday"),
                    ("SCL", "Special Casual Leave"),
                    ("EL", "Earned Leave"),
                    ("COL", "Commuted Leave"),
                    ("VL", "Vacation Leave"),
                )
            ]
        )


class ApplicationsView(GenericAPIView):
    permission_classes = [MODULE]
    serializer_class = ElmLeaveApplicationSerializer

    def get_permissions(self):
        permission = APPLY if self.request.method == "POST" else VIEW
        return [MODULE(), permission()]

    def get(self, request):
        rows = list_employee_applications(request.principal.user_id)
        return Response({"results": self.get_serializer(rows, many=True).data})

    def post(self, request):
        form = ApplicationInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = submit(request.principal, form.validated_data)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)


class ApplicationEventsView(GenericAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = EventSerializer

    def get(self, request, pk: int):
        obj = get_accessible_application(request.principal.user_id, pk)
        return Response({"results": self.get_serializer(obj.events.all()[:100], many=True).data})


class WithdrawView(GenericAPIView):
    permission_classes = [MODULE, APPLY]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        return Response(self.get_serializer(withdraw(request.principal, pk)).data)


class CancelView(GenericAPIView):
    permission_classes = [MODULE, APPLY]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        remarks = str(request.data.get("remarks", "")).strip()
        return Response(
            self.get_serializer(request_cancellation(request.principal, pk, remarks=remarks)).data
        )


class ReplaceSubstituteView(GenericAPIView):
    permission_classes = [MODULE, APPLY]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        form = ReplacementSubstituteInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = nominate_replacement_substitute(
            request.principal, pk, form.validated_data["replacement_substitute_user_id"]
        )
        return Response(self.get_serializer(obj).data)


class ExtendView(GenericAPIView):
    permission_classes = [MODULE, APPLY]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        form = ExtensionInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = submit_extension(request.principal, pk, form.validated_data)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)


class ResumeView(GenericAPIView):
    permission_classes = [MODULE, APPLY]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        form = ResumptionInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = submit_resumption(
            request.principal,
            pk,
            form.validated_data["actual_resumption_date"],
            form.validated_data.get("remarks", ""),
        )
        return Response(self.get_serializer(obj).data)


class ReviewResumptionView(GenericAPIView):
    permission_classes = [MODULE, REVIEW]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        remarks = str(request.data.get("remarks", "")).strip()
        obj = review_resumption(request.principal, pk, remarks=remarks)
        return Response(self.get_serializer(obj).data)


class PrintableView(GenericAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = PrintableApplicationSerializer

    def get(self, request, pk: int):
        app = get_accessible_application(request.principal.user_id, pk)
        profile = EmployeeLeaveProfile.objects.filter(user_id=app.employee_id).first()
        events = list(app.events.all()[:50])

        st_desc = f"Yes ({app.station_location})" if app.station_leave else "No"
        printable_text = (
            f"--- EMPLOYEE LEAVE APPLICATION ---\n"
            f"Application ID: {app.id}\n"
            f"Employee ID: {app.employee_id}\n"
            f"Designation: {profile.designation if profile else 'N/A'}\n"
            f"Department / Unit: {profile.unit if profile else 'N/A'}\n"
            f"Leave Category: {app.category}\n"
            f"Period: {app.start_date} to {app.end_date} ({app.duration} days)\n"
            f"Half Day: {app.half_day}\n"
            f"Reason: {app.reason}\n"
            f"Station Leave: {st_desc}\n"
            f"Status: {app.status}\n"
            f"Substitute ID: {app.substitute_user_id or 'None'} (Status: {app.substitute_status})\n"
            f"Unit Head ID: {app.unit_head_id or 'N/A'}\n"
            f"Sanction Authority ID: {app.sanction_authority_id or 'N/A'}\n"
            f"Final Decision By: {app.approver_id or 'Pending'} at {app.decided_at or 'Pending'}\n"
            f"Remarks: {app.decision_remarks or 'None'}\n"
            f"----------------------------------"
        )

        return Response(
            {
                "application": ElmLeaveApplicationSerializer(app).data,
                "profile": ProfileSerializer(profile).data if profile else None,
                "events": EventSerializer(events, many=True).data,
                "printable_text": printable_text,
            }
        )


class ApprovalQueueView(GenericAPIView):
    permission_classes = [MODULE, REVIEW]
    serializer_class = ElmLeaveApplicationSerializer

    def get(self, request):
        rows = list_approval_queue(request.principal.user_id)
        return Response({"results": self.get_serializer(rows, many=True).data})


class DecisionView(GenericAPIView):
    permission_classes = [MODULE, REVIEW]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk: int):
        form = DecisionInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = decide(request.principal, pk, **form.validated_data)
        return Response(self.get_serializer(obj).data)


class MyBalancesView(GenericAPIView):
    permission_classes = [MODULE, BALANCE]
    serializer_class = BalanceSerializer

    def get(self, request):
        try:
            year = int(request.query_params.get("year", "0"))
        except ValueError as exc:
            raise ValidationError({"year": "Year must be an integer."}) from exc
        if not year:
            year = timezone.localdate().year
        rows = list_employee_balances(request.principal.user_id, year)
        return Response({"results": self.get_serializer(rows, many=True).data})


class MyTransactionsView(GenericAPIView):
    permission_classes = [MODULE, BALANCE]
    serializer_class = LeaveAccountTransactionSerializer

    def get(self, request):
        year_str = request.query_params.get("year")
        year = int(year_str) if year_str and year_str.isdigit() else None
        rows = list_account_transactions(request.principal.user_id, year=year)
        return Response({"results": self.get_serializer(rows, many=True).data})


class NotificationsView(GenericAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = NotificationSerializer

    def get(self, request):
        rows = list_notifications(request.principal.user_id)
        return Response({"results": self.get_serializer(rows, many=True).data})


class ProfilesAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = ProfileSerializer

    def get(self, request):
        return Response({"results": self.get_serializer(list_profiles(), many=True).data})

    def post(self, request):
        existing = EmployeeLeaveProfile.objects.filter(user_id=request.data.get("user_id")).first()
        form = self.get_serializer(existing, data=request.data)
        form.is_valid(raise_exception=True)
        obj, created = upsert_profile(form.validated_data)
        return Response(
            self.get_serializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BalancesAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = BalanceSerializer

    def post(self, request):
        form = BalanceAllotSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = allot_balance(form.validated_data)
        return Response(self.get_serializer(obj).data)


class HolidaysAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = HolidaySerializer

    def get(self, request):
        return Response({"results": self.get_serializer(list_holidays(), many=True).data})

    def post(self, request):
        existing = Holiday.objects.filter(date=request.data.get("date")).first()
        form = self.get_serializer(existing, data=request.data)
        form.is_valid(raise_exception=True)
        obj = upsert_holiday(form.validated_data)
        return Response(self.get_serializer(obj).data)


class OfflineLeaveAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request):
        form = OfflineLeaveInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = record_offline_leave(request.principal, form.validated_data)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)


class YearEndAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = YearEndInputSerializer

    @extend_schema(request=YearEndInputSerializer, responses={200: YearEndOutputSerializer})
    def post(self, request):
        form = self.get_serializer(data=request.data)
        form.is_valid(raise_exception=True)
        year = form.validated_data.get("year") or timezone.localdate().year
        summary = execute_year_end_processing(year)
        return Response(summary)


class SlaAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = SlaConfigSerializer

    def get(self, request):
        return Response({"results": self.get_serializer(list_sla_configs(), many=True).data})

    def post(self, request):
        existing = SlaConfig.objects.filter(task_type=request.data.get("task_type")).first()
        form = self.get_serializer(existing, data=request.data)
        form.is_valid(raise_exception=True)
        form.save()
        return Response(form.data)


class SlaProcessAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = SlaProcessOutputSerializer

    @extend_schema(request=None, responses={200: SlaProcessOutputSerializer})
    def post(self, request):
        report = process_sla_thresholds()
        return Response(report)
