from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    ActionRemarksSerializer,
    EmployeeLeaveBalanceSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    ResumptionSubmitSerializer,
    SanctionDecisionSerializer,
    SubstituteResponseSerializer,
    UnitHeadRecommendationSerializer,
)
from modules.elm.selectors.applications import (
    pending_approvals,
    pending_substitute_requests,
    visible_applications,
)
from modules.elm.selectors.balances import get_user_balances
from modules.elm.selectors.calendars import get_published_holidays
from modules.elm.services.admin import record_offline_leave
from modules.elm.services.applications import (
    approve_cancellation,
    recommend_unit_head,
    request_cancellation,
    request_extension,
    respond_substitute,
    review_resumption,
    sanction_application,
    submit_application,
    submit_resumption,
    withdraw_application,
)


class MyLeavesView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    def get(self, request):
        balances = get_user_balances(request.principal.user_id)
        apps = visible_applications(request.principal).filter(user_id=request.principal.user_id)

        return Response({
            "balances": EmployeeLeaveBalanceSerializer(balances, many=True).data,
            "applications": LeaveApplicationSerializer(apps, many=True).data,
        })


class ApplyLeaveView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.apply"),
    ]

    def post(self, request):
        ser = LeaveApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = submit_application(request.principal, ser.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    def get(self, request, pk: int):
        app = visible_applications(request.principal).get(pk=pk)
        return Response(LeaveApplicationSerializer(app).data)


class ApplicationWithdrawView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.withdraw"),
    ]

    def post(self, request, pk: int):
        app = withdraw_application(request.principal, pk)
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteRequestsView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.substitute.respond"),
    ]

    def get(self, request):
        apps = pending_substitute_requests(request.principal)
        return Response(LeaveApplicationSerializer(apps, many=True).data)


class SubstituteRespondView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.substitute.respond"),
    ]

    def post(self, request, pk: int):
        ser = SubstituteResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = respond_substitute(
            request.principal,
            pk,
            action=ser.validated_data["action"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class PendingApprovalsView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    def get(self, request):
        apps = pending_approvals(request.principal)
        return Response(LeaveApplicationSerializer(apps, many=True).data)


class UnitHeadRecommendView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.review"),
    ]

    def post(self, request, pk: int):
        ser = UnitHeadRecommendationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = recommend_unit_head(
            request.principal,
            pk,
            recommendation=ser.validated_data["recommendation"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class SanctionDecisionView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    def post(self, request, pk: int):
        ser = SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = sanction_application(
            request.principal,
            pk,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class CancellationRequestView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.cancel"),
    ]

    def post(self, request, pk: int):
        ser = ActionRemarksSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = request_cancellation(
            request.principal,
            pk,
            reason=ser.validated_data.get("remarks", "Cancellation requested"),
        )
        return Response(LeaveApplicationSerializer(app).data)


class CancellationDecisionView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    def post(self, request, pk: int):
        ser = SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = approve_cancellation(
            request.principal,
            pk,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class ExtensionRequestView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.extend"),
    ]

    def post(self, request, pk: int):
        ser = LeaveApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = request_extension(request.principal, pk, ser.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ResumptionSubmitView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.resume"),
    ]

    def post(self, request, pk: int):
        ser = ResumptionSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = submit_resumption(
            request.principal,
            pk,
            actual_date=ser.validated_data["actual_date"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class ResumptionReviewView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    def post(self, request, pk: int):
        ser = SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = review_resumption(
            request.principal,
            pk,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class HolidayCalendarView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    def get(self, request):
        holidays = get_published_holidays()
        return Response(HolidayCalendarSerializer(holidays, many=True).data)


class OfflineLeaveRecordView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.admin.manage"),
    ]

    def post(self, request):
        app = record_offline_leave(request.principal, request.data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class PrintableApplicationView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    def get(self, request, pk: int):
        app = visible_applications(request.principal).get(pk=pk)
        return Response({
            "printable_html": f"<h1>Leave Application #{app.pk}</h1><p>Applicant: {app.user_id}</p><p>Category: {app.leave_category}</p><p>Period: {app.start_date} to {app.end_date}</p><p>Status: {app.status}</p><p>Reason: {app.reason}</p>",
            "details": LeaveApplicationSerializer(app).data,
        })
