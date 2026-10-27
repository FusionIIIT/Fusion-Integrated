from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
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
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveApplication,
    LeaveBalance,
)
from modules.elm.services.leave import decide, submit, withdraw

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
        rows = LeaveApplication.objects.filter(employee_id=request.principal.user_id).order_by(
            "-created_at"
        )[:100]
        return Response({"results": self.get_serializer(rows, many=True).data})

    def post(self, request):
        form = ApplicationInputSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = submit(request.principal, form.validated_data)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)


class ApplicationEventsView(GenericAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = EventSerializer

    def get(self, request, pk):
        obj = get_object_or_404(
            LeaveApplication,
            pk=pk,
            employee_id=request.principal.user_id,
        )
        return Response({"results": self.get_serializer(obj.events.all()[:100], many=True).data})


class WithdrawView(GenericAPIView):
    permission_classes = [MODULE, APPLY]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk):
        return Response(self.get_serializer(withdraw(request.principal, pk)).data)


class ApprovalQueueView(GenericAPIView):
    permission_classes = [MODULE, REVIEW]
    serializer_class = ElmLeaveApplicationSerializer

    def get(self, request):
        actor_id = request.principal.user_id
        rows = (
            LeaveApplication.objects.filter(
                Q(status="PENDING", unit_head_id=actor_id)
                | Q(status="RECOMMENDED", sanction_authority_id=actor_id)
            )
            .exclude(employee_id=actor_id)
            .order_by("created_at")[:100]
        )
        return Response({"results": self.get_serializer(rows, many=True).data})


class DecisionView(GenericAPIView):
    permission_classes = [MODULE, REVIEW]
    serializer_class = ElmLeaveApplicationSerializer

    def post(self, request, pk):
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
            from django.utils import timezone

            year = timezone.localdate().year
        rows = LeaveBalance.objects.filter(
            employee_id=request.principal.user_id, year=year
        ).order_by("category")
        return Response({"results": self.get_serializer(rows, many=True).data})


class ProfilesAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = ProfileSerializer

    def get(self, request):
        return Response(
            {
                "results": self.get_serializer(
                    EmployeeLeaveProfile.objects.order_by("user_id")[:100], many=True
                ).data
            }
        )

    @transaction.atomic
    def post(self, request):
        existing = EmployeeLeaveProfile.objects.filter(user_id=request.data.get("user_id")).first()
        form = self.get_serializer(existing, data=request.data)
        form.is_valid(raise_exception=True)
        data = dict(form.validated_data)
        user_id = data.pop("user_id")
        obj, created = EmployeeLeaveProfile.objects.update_or_create(user_id=user_id, defaults=data)
        return Response(
            self.get_serializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BalancesAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = BalanceSerializer

    @transaction.atomic
    def post(self, request):
        form = BalanceAllotSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = dict(form.validated_data)
        allot = data.pop("allotted")
        get_object_or_404(EmployeeLeaveProfile, user_id=data["employee_id"])
        obj, _ = LeaveBalance.objects.select_for_update().get_or_create(
            **data, defaults={"allotted": allot, "used": 0}
        )
        if obj.used > allot:
            raise ValidationError({"allotted": "Allotment cannot be less than already used leave."})
        obj.allotted = allot
        obj.save(update_fields=["allotted"])
        return Response(self.get_serializer(obj).data)


class HolidaysAdminView(GenericAPIView):
    permission_classes = [MODULE, ADMIN]
    serializer_class = HolidaySerializer

    def get(self, request):
        return Response(
            {"results": self.get_serializer(Holiday.objects.order_by("date")[:200], many=True).data}
        )

    @transaction.atomic
    def post(self, request):
        existing = Holiday.objects.filter(date=request.data.get("date")).first()
        form = self.get_serializer(existing, data=request.data)
        form.is_valid(raise_exception=True)
        fields = dict(form.validated_data)
        date = fields.pop("date")
        obj, _ = Holiday.objects.update_or_create(date=date, defaults=fields)
        return Response(self.get_serializer(obj).data)
