"""Thin HTTP layer. Both authorization gates are declared on every view; the
default is deny. All logic lives in selectors/ and services/."""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave import selectors
from modules.leave import services as svc
from modules.leave.api.serializers import (
    ApplyLeaveSerializer,
    DecisionSerializer,
    ExtensionSerializer,
    HolidaySerializer,
    LeaveAccountSerializer,
    LeaveApplicationSerializer,
    OfflineLeaveSerializer,
    ResumptionSerializer,
    VacationPeriodSerializer,
)

MODULE = "leave_management"


class MyLeaveListView(generics.ListAPIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.view_self")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        return selectors.visible_applications(self.request.principal)


class ApplyLeaveView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.apply")]

    def post(self, request):
        s = ApplyLeaveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = svc.apply_leave(principal=request.principal, **s.validated_data)
        return Response(LeaveApplicationSerializer(app).data,
                        status=status.HTTP_201_CREATED)


class WithdrawView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.withdraw")]

    def post(self, request, pk: int):
        app = svc.withdraw(application_id=pk, principal=request.principal)
        return Response(LeaveApplicationSerializer(app).data)


class CancelRequestView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.cancel")]

    def post(self, request, pk: int):
        app = svc.request_cancellation(
            application_id=pk, principal=request.principal,
            reason=request.data.get("reason", ""))
        return Response(LeaveApplicationSerializer(app).data)


class ExtensionView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.extension")]

    def post(self, request, pk: int):
        s = ExtensionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = svc.request_extension(application_id=pk,
                                    principal=request.principal, **s.validated_data)
        return Response(LeaveApplicationSerializer(app).data)


class ResumptionView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.resumption")]

    def post(self, request, pk: int):
        s = ResumptionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = svc.report_resumption(application_id=pk,
                                    principal=request.principal, **s.validated_data)
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteRespondView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.substitute.respond")]

    def post(self, request, pk: int):
        accept = bool(request.data.get("accept"))
        sub = svc.respond_to_cover(application_id=pk, principal=request.principal,
                                   accept=accept)
        return Response({"id": sub.id, "status": sub.status})


class ApprovalQueueView(generics.ListAPIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.view")]
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        return selectors.visible_applications(self.request.principal)


class RecommendView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.review")]

    def post(self, request, pk: int):
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = svc.decide(application_id=pk, principal=request.principal, **s.validated_data)
        return Response(LeaveApplicationSerializer(app).data)


class SanctionView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.sanction")]

    def post(self, request, pk: int):
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = svc.decide(application_id=pk, principal=request.principal, **s.validated_data)
        return Response(LeaveApplicationSerializer(app).data)


class OfflineLeaveView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.record_offline")]

    def post(self, request):
        s = OfflineLeaveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = svc.record_offline_leave(principal=request.principal, **s.validated_data)
        return Response(LeaveApplicationSerializer(app).data,
                        status=status.HTTP_201_CREATED)


class MyBalancesView(generics.ListAPIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.leave.view_self")]
    serializer_class = LeaveAccountSerializer

    def get_queryset(self):
        return selectors.my_accounts_all(self.request.principal.user_id)


class CalendarView(generics.ListAPIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.calendar.manage")]
    serializer_class = HolidaySerializer

    def get_queryset(self):
        return selectors.published_holidays()


class VacationView(generics.ListAPIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.calendar.manage")]
    serializer_class = VacationPeriodSerializer

    def get_queryset(self):
        return selectors.active_vacations()


class PolicyView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.policy.manage")]

    def get(self, request):
        return Response([
            {"category": p.category, "annual_entitlement": str(p.annual_entitlement),
             "carries_forward": p.carries_forward,
             "continuous_counting": p.continuous_counting,
             "half_day_allowed": p.half_day_allowed,
             "final_authority": p.final_authority}
            for p in selectors.policies()
        ])


class LeaveReportView(APIView):
    permission_classes = [HasModuleGrant(MODULE),
                          HasPermission("leave_management.report.view")]

    def get(self, request):
        return Response(svc.leave_statistics())
