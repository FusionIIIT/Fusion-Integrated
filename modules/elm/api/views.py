"""API views for Employee Leave Management."""

from django.utils import timezone
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
    HolidaySerializer,
    LeaveTypeInfoSerializer,
    ProfileSerializer,
)
from modules.elm.domain.policy import DEFAULT_ENTITLEMENTS
from modules.elm.models import EmployeeLeaveProfile, Holiday
from modules.elm.selectors.queries import (
    get_employee_application,
    list_approval_queue,
    list_employee_applications,
    list_employee_balances,
    list_holidays,
    list_profiles,
)
from modules.elm.services.leave import (
    allot_balance,
    cancel_approved,
    decide,
    submit,
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
        obj = get_employee_application(request.principal.user_id, pk)
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
            self.get_serializer(cancel_approved(request.principal, pk, remarks=remarks)).data
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
