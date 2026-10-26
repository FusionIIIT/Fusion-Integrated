from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission, IsAuthenticatedPrincipal
from modules.directory.models import UserRef
from modules.leave.api.serializers import (
    BalanceAdjustmentSerializer,
    LeaveBalanceChangeSerializer,
    LeaveCalendarCreateSerializer,
    LeaveRequestSerializer,
)
from modules.leave.domain import eligible_for, starting_balance
from modules.leave.models import (
    LeaveBalance,
    LeaveBalanceChange,
    LeaveCalendar,
    LeaveCalendarDay,
    LeaveRequest,
)


class MyLeaveRequestsView(APIView):
    permission_classes = []

    def get_permissions(self):
        codes = {
            "GET": ("leave.request.view_self",),
            "POST": ("leave.request.create",),
            "DELETE": ("leave.request.delete",),
        }
        code = codes.get(self.request.method, ("leave.request.view_self",))
        return [HasPermission(*code)()]

    def get(self, request):
        rows = LeaveRequest.objects.filter(employee_user_id=request.principal.user_id)
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data, context={"request": request})
        with transaction.atomic():
            # Serializes submissions by the projected employee row so overlap
            # and pending-balance checks cannot race each other.
            UserRef.objects.select_for_update().filter(
                user_id=request.principal.user_id, kind__in=("faculty", "staff"),
                is_active=True,
            ).first()
            serializer.is_valid(raise_exception=True)
            leave = serializer.save(employee_user_id=request.principal.user_id)
        return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)

    def delete(self, request, request_id):
        deleted, _ = LeaveRequest.objects.filter(
            pk=request_id, employee_user_id=request.principal.user_id,
            status="pending",
        ).update(status="withdrawn")
        if not deleted:
            return Response({"detail": "Pending request not found."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveApprovalView(APIView):
    permission_classes = [HasPermission("leave.request.approve")]

    def get(self, request):
        # CL/RH are the only categories with a single Unit-Head final decision.
        # Higher-sanction routing needs the configured hierarchy and is not
        # represented by this first workflow slice.
        unit_head = UserRef.objects.filter(
            user_id=request.principal.user_id, kind__in=("faculty", "staff"),
            is_active=True,
        ).first()
        if unit_head is None or not unit_head.department:
            return Response({"detail": "A department-scoped Unit Head profile is required."},
                            status=status.HTTP_403_FORBIDDEN)
        unit_employee_ids = UserRef.objects.filter(
            department=unit_head.department, kind__in=("faculty", "staff"), is_active=True
        ).values("user_id")
        rows = LeaveRequest.objects.filter(
            status="pending", leave_type__in=("CL", "RH"),
            employee_user_id__in=unit_employee_ids,
        )
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def patch(self, request, request_id):
        decision = request.data.get("status")
        if decision not in ("approved", "rejected"):
            return Response({"status": "Choose approved or rejected."},
                            status=status.HTTP_400_BAD_REQUEST)
        comment = request.data.get("reviewer_comment", "")
        if not isinstance(comment, str) or len(comment) > 500:
            return Response({"reviewer_comment": "Must be text of at most 500 characters."},
                            status=status.HTTP_400_BAD_REQUEST)
        insufficient = False
        with transaction.atomic():
            unit_head = UserRef.objects.filter(
                user_id=request.principal.user_id, kind__in=("faculty", "staff"),
                is_active=True,
            ).first()
            leave = LeaveRequest.objects.select_for_update().filter(
                pk=request_id, status="pending"
            ).first()
            if leave is None:
                return Response({"detail": "Pending request not found."},
                                status=status.HTTP_404_NOT_FOUND)
            if leave.leave_type not in ("CL", "RH"):
                return Response({"detail": "This category requires the higher-sanction workflow."},
                                status=status.HTTP_409_CONFLICT)
            applicant = UserRef.objects.filter(
                user_id=leave.employee_user_id, kind__in=("faculty", "staff"),
                is_active=True,
            ).first()
            if (unit_head is None or applicant is None or not unit_head.department
                    or unit_head.department != applicant.department):
                return Response({"detail": "Request is outside your Unit Head scope."},
                                status=status.HTTP_404_NOT_FOUND)
            if decision == "approved":
                employee = applicant
                accounts = []
                for year, amount in leave.charge_by_year.items():
                    balance, _ = LeaveBalance.objects.get_or_create(
                        employee_user_id=leave.employee_user_id,
                        leave_type=leave.leave_type,
                        year=int(year),
                        defaults={"available": starting_balance(employee.kind,
                                                                 leave.leave_type)},
                    )
                    balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
                    if balance.available < Decimal(amount):
                        insufficient = True
                        break
                    accounts.append((balance, Decimal(amount)))
                if insufficient:
                    transaction.set_rollback(True)
                else:
                    for balance, amount in accounts:
                        balance.available -= amount
                        balance.save(update_fields=("available", "updated_at"))
                        LeaveBalanceChange.objects.create(
                            balance=balance, leave_request=leave, action="approved",
                            amount=-amount, actor_user_id=request.principal.user_id,
                            note="Approved leave request",
                        )
                    leave.status = decision
                    leave.reviewed_by_user_id = request.principal.user_id
                    leave.reviewer_comment = comment
                    leave.save(update_fields=("status", "reviewed_by_user_id",
                                              "reviewer_comment", "updated_at"))
            else:
                leave.status = decision
                leave.reviewed_by_user_id = request.principal.user_id
                leave.reviewer_comment = comment
                leave.save(update_fields=("status", "reviewed_by_user_id",
                                          "reviewer_comment", "updated_at"))
        if insufficient:
            return Response({"detail": "The available balance is no longer sufficient."},
                            status=status.HTTP_409_CONFLICT)
        return Response(LeaveRequestSerializer(leave).data)


class MyLeaveBalancesView(APIView):
    permission_classes = [HasPermission("leave.request.view_self")]

    def get(self, request):
        employee = UserRef.objects.get(user_id=request.principal.user_id)
        year = timezone.localdate().year
        balances = []
        for leave_type, label in LeaveRequest.TYPE:
            if not eligible_for(employee.kind, leave_type):
                continue
            account = LeaveBalance.objects.filter(
                employee_user_id=employee.user_id, leave_type=leave_type, year=year
            ).first()
            balances.append({
                "leave_type": leave_type, "label": label, "year": year,
                "available": (account.available if account else
                              starting_balance(employee.kind, leave_type)),
            })
        return Response({"results": balances})


class MyLeaveBalanceHistoryView(APIView):
    permission_classes = [HasPermission("leave.request.view_self")]

    def get(self, request):
        changes = LeaveBalanceChange.objects.filter(
            balance__employee_user_id=request.principal.user_id
        ).select_related("balance")
        return Response({"results": LeaveBalanceChangeSerializer(changes, many=True).data})


class LeaveBalanceAdjustmentView(APIView):
    permission_classes = [HasPermission("leave.balance.update")]

    def post(self, request):
        serializer = BalanceAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        employee = UserRef.objects.get(user_id=values["employee_user_id"])
        with transaction.atomic():
            balance, _ = LeaveBalance.objects.get_or_create(
                employee_user_id=employee.user_id,
                leave_type=values["leave_type"], year=values["year"],
                defaults={"available": starting_balance(employee.kind,
                                                         values["leave_type"])},
            )
            balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
            new_amount = balance.available + values["amount"]
            if new_amount < 0:
                transaction.set_rollback(True)
                return Response({"amount": "Adjustment cannot make the balance negative."},
                                status=status.HTTP_400_BAD_REQUEST)
            balance.available = new_amount
            balance.save(update_fields=("available", "updated_at"))
            LeaveBalanceChange.objects.create(
                balance=balance, action="adjustment", amount=values["amount"],
                note=values["note"], actor_user_id=request.principal.user_id,
            )
        return Response({"leave_type": balance.leave_type, "year": balance.year,
                         "available": balance.available})


class LeaveCalendarView(APIView):
    permission_classes = [IsAuthenticatedPrincipal]

    def get(self, request):
        calendar = LeaveCalendar.objects.filter(status="published").first()
        if calendar is None:
            return Response({"calendar": None, "days": []})
        days = calendar.days.order_by("date").values(
            "date", "is_closed", "is_restricted_holiday")
        return Response({"calendar": calendar.title, "days": list(days)})


class LeaveCalendarAdminView(APIView):
    permission_classes = [HasPermission("leave.calendar.manage")]

    def post(self, request):
        serializer = LeaveCalendarCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        with transaction.atomic():
            calendar = LeaveCalendar.objects.create(
                title=values["title"], created_by_user_id=request.principal.user_id)
            LeaveCalendarDay.objects.bulk_create([
                LeaveCalendarDay(calendar=calendar, **day) for day in values["days"]
            ])
        return Response({"id": calendar.pk, "status": calendar.status},
                        status=status.HTTP_201_CREATED)


class LeaveCalendarPublishView(APIView):
    permission_classes = [HasPermission("leave.calendar.publish")]

    def post(self, request, calendar_id):
        with transaction.atomic():
            calendar = LeaveCalendar.objects.select_for_update().filter(
                pk=calendar_id, status="draft").first()
            if calendar is None:
                return Response({"detail": "Draft calendar not found."},
                                status=status.HTTP_404_NOT_FOUND)
            LeaveCalendar.objects.filter(status="published").update(
                status="replaced", updated_at=timezone.now())
            calendar.publish()
        return Response({"id": calendar.pk, "status": calendar.status,
                         "published_at": calendar.published_at})

