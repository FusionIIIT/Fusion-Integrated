"""Leave API views and controllers."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.domain.constants import STATUS_AWAITING_UNIT_HEAD
from modules.leave.selectors.leave import (
    get_leave_balances,
    get_leave_request_detail,
    get_my_leave_requests,
    get_pending_approvals,
    get_pending_substitute_requests,
)
from modules.leave.services.leave import (
    apply_leave,
    decide_cancellation,
    modify_pending_request,
    process_year_end,
    record_offline_leave,
    request_cancellation,
    respond_substitute,
    review_unit_head,
    sanction_final,
    submit_extension,
    submit_resumption,
    verify_resumption,
    withdraw_pending_request,
)
from .serializers import (
    LeaveApplySerializer,
    LeaveBalanceSerializer,
    LeaveRequestReadSerializer,
    LeaveReviewSerializer,
    OfflineLeaveSerializer,
    ResumptionSerializer,
    SubstituteResponseSerializer,
)


def _actor(request):
    return getattr(request, "principal", None) or getattr(request, "user", None)


class LeaveBalanceListView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_self")]

    def get(self, request):
        actor = _actor(request)
        user_id = actor.user_id
        year = int(request.query_params.get("year", 2026))
        balances = get_leave_balances(user_id, year=year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class LeaveApplicationListCreateView(APIView):
    permission_classes = [HasModuleGrant("leave")]

    def get_permissions(self):
        perms = [HasModuleGrant("leave")]
        if self.request.method == "POST":
            perms.append(HasPermission("leave.application.create"))
        else:
            perms.append(HasPermission("leave.application.view_self"))
        return [p() for p in perms]

    def get(self, request):
        actor = _actor(request)
        user_id = actor.user_id
        requests = get_my_leave_requests(user_id)
        return Response(LeaveRequestReadSerializer(requests, many=True).data)

    def post(self, request):
        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        actor = _actor(request)
        is_director = "Director" in getattr(actor, "roles", ())
        req = apply_leave(
            user_id=actor.user_id,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            purpose=data["purpose"],
            half_day=data.get("half_day", "full"),
            substitute_user_id=data.get("substitute_user_id"),
            station_leave=data.get("station_leave", False),
            station_start_date=data.get("station_start_date"),
            station_end_date=data.get("station_end_date"),
            station_address=data.get("station_address", ""),
            station_contact=data.get("station_contact", ""),
            is_director=is_director,
        )
        return Response(LeaveRequestReadSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_self")]

    def get(self, request, pk: int):
        req = get_leave_request_detail(pk)
        if not req:
            return Response({"error": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeaveRequestReadSerializer(req).data)

    def put(self, request, pk: int):
        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        actor = _actor(request)
        req = modify_pending_request(
            request_id=pk,
            user_id=actor.user_id,
            start_date=data["start_date"],
            end_date=data["end_date"],
            purpose=data["purpose"],
            half_day=data.get("half_day", "full"),
            substitute_user_id=data.get("substitute_user_id"),
        )
        return Response(LeaveRequestReadSerializer(req).data)

    def delete(self, request, pk: int):
        actor = _actor(request)
        req = withdraw_pending_request(request_id=pk, user_id=actor.user_id)
        return Response(LeaveRequestReadSerializer(req).data)


class SubstituteQueueListView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.substitute.respond")]

    def get(self, request):
        actor = _actor(request)
        pending = get_pending_substitute_requests(actor.user_id)
        return Response(LeaveRequestReadSerializer(pending, many=True).data)


class SubstituteRespondView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.substitute.respond")]

    def post(self, request, pk: int):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        actor = _actor(request)
        req = respond_substitute(
            request_id=pk,
            substitute_user_id=actor.user_id,
            accept=data["accept"],
            remarks=data.get("remarks", ""),
            is_director="Director" in getattr(actor, "roles", ()),
        )
        return Response(LeaveRequestReadSerializer(req).data)


class ApprovalsQueueListView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.review")]

    def get(self, request):
        actor = _actor(request)
        active_role = getattr(actor, "active_role", None)
        pending = get_pending_approvals(actor.user_id, active_role=active_role)
        return Response(LeaveRequestReadSerializer(pending, many=True).data)


class LeaveReviewView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.review")]

    def post(self, request, pk: int):
        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        actor = _actor(request)
        req = get_leave_request_detail(pk)
        if not req:
            return Response({"error": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)

        if req.status == STATUS_AWAITING_UNIT_HEAD:
            res = review_unit_head(
                request_id=pk,
                reviewer_user_id=actor.user_id,
                decision=data["decision"],
                remarks=data.get("remarks", ""),
            )
        else:
            res = sanction_final(
                request_id=pk,
                authority_user_id=actor.user_id,
                decision=data["decision"],
                remarks=data.get("remarks", ""),
            )
        return Response(LeaveRequestReadSerializer(res).data)


class LeaveCancellationView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.create")]

    def post(self, request, pk: int):
        actor = _actor(request)
        req = request_cancellation(request_id=pk, user_id=actor.user_id)
        return Response(LeaveRequestReadSerializer(req).data)


class DecideCancellationView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.review")]

    def post(self, request, pk: int):
        actor = _actor(request)
        approve = bool(request.data.get("approve", True))
        req = decide_cancellation(request_id=pk, reviewer_user_id=actor.user_id, approve=approve)
        return Response(LeaveRequestReadSerializer(req).data)


class LeaveExtensionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.create")]

    def post(self, request, pk: int):
        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        actor = _actor(request)
        ext = submit_extension(
            parent_leave_id=pk,
            user_id=actor.user_id,
            extension_start=data["start_date"],
            extension_end=data["end_date"],
            purpose=data["purpose"],
            substitute_user_id=data.get("substitute_user_id"),
        )
        return Response(LeaveRequestReadSerializer(ext).data, status=status.HTTP_201_CREATED)


class LeaveResumptionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.create")]

    def post(self, request, pk: int):
        serializer = ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = _actor(request)
        req = submit_resumption(
            request_id=pk,
            user_id=actor.user_id,
            actual_date=serializer.validated_data["actual_date"],
        )
        return Response(LeaveRequestReadSerializer(req).data)


class VerifyResumptionView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.review")]

    def post(self, request, pk: int):
        actor = _actor(request)
        req = verify_resumption(request_id=pk, verifier_user_id=actor.user_id)
        return Response(LeaveRequestReadSerializer(req).data)


class OfflineLeaveRecordView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.admin.manage")]

    def post(self, request):
        serializer = OfflineLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = record_offline_leave(
            user_id=data["user_id"],
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            purpose=data["purpose"],
            offline_reference=data["offline_reference"],
            year=data.get("year", 2026),
        )
        return Response(LeaveRequestReadSerializer(req).data, status=status.HTTP_201_CREATED)


class YearEndProcessingView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.admin.manage")]

    def post(self, request):
        year = int(request.data.get("year", 2026))
        process_year_end(year=year)
        return Response({"status": f"Year-end processing for {year} completed."})
