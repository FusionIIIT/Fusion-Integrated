from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import Holiday, LeaveApplication, LeaveBalance, LeaveCategory

MODULE = HasModuleGrant("employee_leave")
P_VIEW = "employee_leave.application.view_self"
P_CREATE = "employee_leave.application.create"
P_WITHDRAW = "employee_leave.application.withdraw"
P_BALANCE = "employee_leave.balance.view"
P_CALENDAR = "employee_leave.calendar.view"


def user_id(request):
    principal = getattr(request, "principal", None)
    return getattr(principal, "user_id", getattr(principal, "id", None))


class CategoryListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]
    serializer_class = s.CategorySerializer
    queryset = LeaveCategory.objects.filter(active=True)


class BalanceListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE)]
    serializer_class = s.BalanceSerializer

    def get_queryset(self):
        return LeaveBalance.objects.filter(user_id=user_id(self.request)).select_related(
            "category")


class ApplicationListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get_queryset(self):
        return LeaveApplication.objects.filter(user_id=user_id(self.request)).select_related(
            "category")

    def get_serializer_class(self):
        return (s.ApplicationCreateSerializer
                if self.request.method == "POST" else s.ApplicationSerializer)

    def create(self, request, *args, **kwargs):
        payload = s.ApplicationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        category = get_object_or_404(LeaveCategory, code=data.pop("category_code"), active=True)
        application = LeaveApplication.objects.create(user_id=user_id(request),
                                                       category=category, **data)
        return Response(s.ApplicationSerializer(application).data,
                        status=status.HTTP_201_CREATED)


class ApplicationWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk):
        application = get_object_or_404(LeaveApplication, pk=pk, user_id=user_id(request))
        if application.status == "pending":
            application.status = "withdrawn"
            application.current_stage = "employee"
            application.save(update_fields=["status", "current_stage", "updated_at"])
        return Response(s.ApplicationSerializer(application).data)


class HolidayListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    serializer_class = s.HolidaySerializer

    def get_queryset(self):
        qs = Holiday.objects.filter(published=True)
        year = self.request.query_params.get("year")
        return qs.filter(date__year=year) if year else qs
