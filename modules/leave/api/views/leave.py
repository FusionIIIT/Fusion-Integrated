"""API views for Leave Management."""
from datetime import date

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasPermission

from ...domain.entities import LeaveCategory, LeaveStatus
from ...models import (
    HolidayCalendar,
    LeaveBalance,
    LeavePolicy,
    LeaveRequest,
    OfflineLeaveEntry,
    SubstituteRequest,
)
from ...selectors.leave_requests import (
    get_leave_request,
    get_leave_request_history,
    get_pending_approvals,
    get_pending_substitute_requests,
    visible_leave_requests,
)
from ...services.balances import (
    process_year_end,
)
from ...services.leave_requests import (
    create_leave_request,
    establishment_review,
    final_sanction,
    respond_to_substitute_request,
    submit_leave_request,
    unit_head_review,
)
from ..filters import (
    HolidayCalendarFilter,
    LeaveBalanceFilter,
    LeavePolicyFilter,
    LeaveRequestFilter,
    OfflineLeaveEntryFilter,
    SubstituteRequestFilter,
)
from ..permissions import (
    CanModifyPendingLeave,
    HasModuleGrantLeave,
    IsLeaveRequestOwner,
    IsLeaveRequestOwnerOrApprover,
    LeaveActionPermissionMixin,
)
from ..serializers.read import (
    HolidayCalendarReadSerializer,
    LeaveBalanceReadSerializer,
    LeavePolicyReadSerializer,
    LeaveRequestListSerializer,
    LeaveRequestReadSerializer,
    OfflineLeaveEntryReadSerializer,
    SubstituteRequestReadSerializer,
)
from ..serializers.write import (
    EstablishmentReviewSerializer,
    FinalSanctionSerializer,
    HolidayCalendarWriteSerializer,
    LeaveBalanceAdjustSerializer,
    LeavePolicyWriteSerializer,
    LeaveRequestCancelSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestExtendSerializer,
    LeaveRequestModifySerializer,
    LeaveRequestResumeSerializer,
    LeaveRequestWithdrawSerializer,
    OfflineLeaveEntryWriteSerializer,
    SubstituteRequestRespondSerializer,
    UnitHeadReviewSerializer,
)


class StandardResultsSetPagination(CursorPagination):
    page_size = 25


# -- Leave Request Views ------------------------------------------------------

class LeaveRequestViewSet(LeaveActionPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [HasModuleGrantLeave, IsLeaveRequestOwnerOrApprover]
    action_permissions = {
        "metadata": (),
        "list": (HasPermission(
            "leave_management.leave_request.view_self",
            "leave_management.leave_request.view",
        ),),
        "retrieve": (
            HasPermission(
                "leave_management.leave_request.view_self",
                "leave_management.leave_request.view",
            ),
            IsLeaveRequestOwnerOrApprover,
        ),
        "create": (HasPermission("leave_management.leave_request.create"),),
        "update": (
            HasPermission("leave_management.leave_request.modify_pending"),
            CanModifyPendingLeave,
        ),
        "partial_update": (
            HasPermission("leave_management.leave_request.modify_pending"),
            CanModifyPendingLeave,
        ),
        "submit": (
            HasPermission("leave_management.leave_request.create"),
            CanModifyPendingLeave,
        ),
        "modify": (
            HasPermission("leave_management.leave_request.modify_pending"),
            CanModifyPendingLeave,
        ),
        "withdraw": (
            HasPermission("leave_management.leave_request.withdraw_pending"),
            CanModifyPendingLeave,
        ),
        "cancel": (
            HasPermission("leave_management.leave_request.cancel_approved"),
            IsLeaveRequestOwner,
        ),
        "extend": (
            HasPermission("leave_management.leave_request.extend"),
            IsLeaveRequestOwner,
        ),
        "resume": (
            HasPermission("leave_management.leave_request.resume"),
            IsLeaveRequestOwner,
        ),
        "history": (HasPermission(
            "leave_management.leave_request.view_self",
            "leave_management.leave_request.view_audit",
        ),),
    }
    pagination_class = StandardResultsSetPagination
    filterset_class = LeaveRequestFilter
    lookup_field = "pk"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return visible_leave_requests(self.request.principal)

    def get_action_leave_request(self, request, pk):
        leave_request = get_leave_request(pk, request.principal)
        if leave_request is not None:
            self.check_object_permissions(request, leave_request)
        return leave_request

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return (
                LeaveRequestReadSerializer
                if self.action == "retrieve"
                else LeaveRequestListSerializer
            )
        if self.action == "create":
            return LeaveRequestCreateSerializer
        if self.action == "partial_update":
            return LeaveRequestModifySerializer
        return LeaveRequestReadSerializer

    def create(self, request, *args, **kwargs):
        """Return the read shape, including `id`.

        The SPA creates a draft and immediately calls `/submit/` with the id
        from this response; the write serializer does not carry `id`, so the
        default 201 body would make the follow-up request hit `undefined`.
        """
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            LeaveRequestReadSerializer(serializer.instance,
                                       context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer):
        lr = create_leave_request(
            user_id=self.request.principal.user_id,
            category=serializer.validated_data["category"],
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
            half_day=serializer.validated_data.get("half_day", False),
            half_day_session=serializer.validated_data.get("half_day_session"),
            purpose=serializer.validated_data["purpose"],
            station_leave=serializer.validated_data.get("station_leave", False),
            station_leave_address=serializer.validated_data.get("station_leave_address"),
            substitute_id=serializer.validated_data.get("substitute_id"),
            employee_type="faculty" if self.request.principal.kind == "faculty" else "non_faculty",
            principal=self.request.principal,
        )
        serializer.instance = lr

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        if self.get_action_leave_request(request, pk) is None:
            return Response({"detail": "Not found"}, status=404)
        lr = submit_leave_request(pk, request.principal)
        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def modify(self, request, pk=None):
        lr = self.get_action_leave_request(request, pk)
        if not lr:
            return Response({"detail": "Not found"}, status=404)

        serializer = LeaveRequestModifySerializer(lr, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        lr = self.get_action_leave_request(request, pk)
        if not lr:
            return Response({"detail": "Not found"}, status=404)

        serializer = LeaveRequestWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update status
        lr.status = LeaveStatus.WITHDRAWN
        lr.save(update_fields=["status", "updated_at"])

        from ...services.leave_requests import _record_transition
        _record_transition(
            lr, lr.status, LeaveStatus.WITHDRAWN,
            request.principal.user_id, "employee",
            serializer.validated_data.get("reason", "")
        )

        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        lr = self.get_action_leave_request(request, pk)
        if not lr:
            return Response({"detail": "Not found"}, status=404)

        if lr.status != LeaveStatus.APPROVED:
            return Response({"detail": "Only approved leave can be cancelled"}, status=400)

        serializer = LeaveRequestCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lr.status = LeaveStatus.CANCELLED
        lr.save(update_fields=["status", "updated_at"])

        from ...services.leave_requests import _record_transition
        _record_transition(
            lr, LeaveStatus.APPROVED, LeaveStatus.CANCELLED,
            request.principal.user_id, "employee",
            serializer.validated_data.get("reason", "")
        )

        # Restore balance
        from ...selectors.balances import get_or_create_balance
        balance = get_or_create_balance(lr.user_id, lr.category, lr.start_date.year)
        balance.availed -= lr.total_days
        balance.closing_balance += lr.total_days
        balance.save(update_fields=["availed", "closing_balance", "updated_at"])

        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        lr = self.get_action_leave_request(request, pk)
        if not lr:
            return Response({"detail": "Not found"}, status=404)

        if lr.status != LeaveStatus.APPROVED:
            return Response({"detail": "Only approved leave can be extended"}, status=400)

        if lr.category not in [LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL]:
            return Response({"detail": "Only EL, VL, COL can be extended"}, status=400)

        serializer = LeaveRequestExtendSerializer(lr, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Create extension request
        extension = create_leave_request(
            user_id=lr.user_id,
            category=lr.category,
            start_date=lr.end_date + date.resolution,
            end_date=serializer.validated_data["end_date"],
            half_day=False,
            half_day_session=None,
            purpose=serializer.validated_data["purpose"],
            station_leave=False,
            station_leave_address=None,
            substitute_id=lr.substitute_id,
            employee_type="faculty" if request.principal.kind == "faculty" else "non_faculty",
            principal=request.principal,
        )
        extension.extension_of = lr
        extension.status = LeaveStatus.EXTENSION_REQUESTED
        extension.save(update_fields=["extension_of", "status"])

        lr.status = LeaveStatus.EXTENSION_REQUESTED
        lr.save(update_fields=["status", "updated_at"])

        return Response(LeaveRequestReadSerializer(extension, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        lr = self.get_action_leave_request(request, pk)
        if not lr:
            return Response({"detail": "Not found"}, status=404)

        if lr.status != LeaveStatus.APPROVED:
            return Response({"detail": "Only approved leave can have resumption"}, status=400)

        if lr.category not in [LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL]:
            return Response({"detail": "Only EL, VL, COL require resumption"}, status=400)

        serializer = LeaveRequestResumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lr.status = LeaveStatus.RESUMPTION_PENDING
        lr.resumption_date = serializer.validated_data["resumption_date"]
        lr.save(update_fields=["status", "resumption_date", "updated_at"])

        from ...services.leave_requests import _record_transition
        _record_transition(
            lr, LeaveStatus.APPROVED, LeaveStatus.RESUMPTION_PENDING,
            request.principal.user_id, "employee",
            "Resumption of duty submitted"
        )

        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        lr = self.get_action_leave_request(request, pk)
        if not lr:
            return Response({"detail": "Not found"}, status=404)

        history = get_leave_request_history(pk)
        from .serializers.read import LeaveRequestTransitionReadSerializer
        return Response(LeaveRequestTransitionReadSerializer(history, many=True).data)


# -- Pending Approvals --------------------------------------------------------

class PendingApprovalsView(generics.ListAPIView):
    permission_classes = [
        HasModuleGrantLeave,
        HasPermission("leave_management.leave_request.approve"),
    ]
    serializer_class = LeaveRequestListSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = LeaveRequestFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return get_pending_approvals(self.request.principal)


# -- Approval Actions ---------------------------------------------------------

class ApprovalActionsViewSet(LeaveActionPermissionMixin, viewsets.ViewSet):
    permission_classes = [HasModuleGrantLeave]
    serializer_class = LeaveRequestReadSerializer
    action_permissions = {
        "metadata": (),
        "unit_head_review": (HasPermission("leave_management.leave_request.approve"),),
        "establishment_review": (HasPermission("leave_management.leave_request.approve"),),
        "final_sanction": (HasPermission("leave_management.leave_request.approve"),),
    }

    @extend_schema(request=UnitHeadReviewSerializer, responses=LeaveRequestReadSerializer)
    @action(detail=False, methods=["post"], url_path=r"(?P<leave_request_id>\d+)/unit-head-review")
    def unit_head_review(self, request, leave_request_id=None):
        serializer = UnitHeadReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lr = unit_head_review(
            int(leave_request_id),
            serializer.validated_data["recommend"],
            serializer.validated_data.get("remark", ""),
            request.principal,
        )
        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @extend_schema(request=EstablishmentReviewSerializer, responses=LeaveRequestReadSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path=r"(?P<leave_request_id>\d+)/establishment-review",
    )
    def establishment_review(self, request, leave_request_id=None):
        serializer = EstablishmentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lr = establishment_review(
            int(leave_request_id),
            serializer.validated_data["action"],
            serializer.validated_data.get("remark", ""),
            request.principal,
        )
        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)

    @extend_schema(request=FinalSanctionSerializer, responses=LeaveRequestReadSerializer)
    @action(detail=False, methods=["post"], url_path=r"(?P<leave_request_id>\d+)/final-sanction")
    def final_sanction(self, request, leave_request_id=None):
        serializer = FinalSanctionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lr = final_sanction(
            int(leave_request_id),
            serializer.validated_data["approve"],
            serializer.validated_data.get("remark", ""),
            request.principal,
        )
        return Response(LeaveRequestReadSerializer(lr, context={"request": request}).data)


# -- Substitute Requests ------------------------------------------------------

class SubstituteRequestViewSet(LeaveActionPermissionMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasModuleGrantLeave]
    action_permissions = {
        "metadata": (),
        "list": (HasPermission(
            "leave_management.substitute_request.view_self",
            "leave_management.substitute_request.respond",
        ),),
        "retrieve": (HasPermission(
            "leave_management.substitute_request.view_self",
            "leave_management.substitute_request.respond",
        ),),
        "respond": (HasPermission("leave_management.substitute_request.respond"),),
    }
    serializer_class = SubstituteRequestReadSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = SubstituteRequestFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SubstituteRequest.objects.none()
        return get_pending_substitute_requests(self.request.principal.user_id)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        sr = SubstituteRequest.objects.get(pk=pk)
        serializer = SubstituteRequestRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sr = respond_to_substitute_request(
            pk,
            serializer.validated_data["accept"],
            serializer.validated_data.get("reason", ""),
            request.principal,
        )
        return Response(SubstituteRequestReadSerializer(sr, context={"request": request}).data)


# -- Leave Balance ------------------------------------------------------------

class LeaveBalanceViewSet(LeaveActionPermissionMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasModuleGrantLeave]
    action_permissions = {
        "metadata": (),
        "list": (HasPermission(
            "leave_management.leave_balance.view_self",
            "leave_management.leave_balance.view",
        ),),
        "retrieve": (HasPermission(
            "leave_management.leave_balance.view_self",
            "leave_management.leave_balance.view",
        ),),
    }
    serializer_class = LeaveBalanceReadSerializer
    pagination_class = StandardResultsSetPagination
    filterset_class = LeaveBalanceFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveBalance.objects.none()
        from ...selectors.balances import get_all_user_balances

        return get_all_user_balances(self.request.principal.user_id)


class LeaveBalanceAdminViewSet(LeaveActionPermissionMixin, viewsets.ViewSet):
    permission_classes = [HasModuleGrantLeave]
    serializer_class = LeaveBalanceReadSerializer
    action_permissions = {
        "metadata": (),
        "adjust": (HasPermission("leave_management.leave_balance.adjust"),),
    }

    @extend_schema(
        request=LeaveBalanceAdjustSerializer,
        responses=LeaveBalanceReadSerializer,
    )
    @action(detail=False, methods=["post"], url_path="adjust")
    def adjust(self, request):
        serializer = LeaveBalanceAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from ...services.balances import adjust_balance
        balance = adjust_balance(
            serializer.validated_data["user_id"],
            serializer.validated_data["category"],
            serializer.validated_data["year"],
            serializer.validated_data["adjustment"],
            serializer.validated_data.get("reason", ""),
        )
        return Response(LeaveBalanceReadSerializer(balance).data)


# -- Leave Policy -------------------------------------------------------------

class LeavePolicyViewSet(LeaveActionPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [HasModuleGrantLeave]
    action_permissions = {
        "metadata": (),
        "list": (HasPermission(
            "leave_management.leave_policy.view",
            "leave_management.leave_policy.manage",
        ),),
        "retrieve": (HasPermission(
            "leave_management.leave_policy.view",
            "leave_management.leave_policy.manage",
        ),),
        "create": (HasPermission("leave_management.leave_policy.manage"),),
        "update": (HasPermission("leave_management.leave_policy.manage"),),
        "partial_update": (HasPermission("leave_management.leave_policy.manage"),),
        "destroy": (HasPermission("leave_management.leave_policy.manage"),),
    }
    pagination_class = StandardResultsSetPagination
    filterset_class = LeavePolicyFilter

    def get_queryset(self):
        return LeavePolicy.objects.all().order_by("-effective_from")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return LeavePolicyWriteSerializer
        return LeavePolicyReadSerializer


# -- Holiday Calendar ---------------------------------------------------------

class HolidayCalendarViewSet(LeaveActionPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [HasModuleGrantLeave]
    action_permissions = {
        "metadata": (),
        "list": (HasPermission(
            "leave_management.holiday_calendar.view",
            "leave_management.holiday_calendar.manage",
        ),),
        "retrieve": (HasPermission(
            "leave_management.holiday_calendar.view",
            "leave_management.holiday_calendar.manage",
        ),),
        "create": (HasPermission("leave_management.holiday_calendar.manage"),),
        "update": (HasPermission("leave_management.holiday_calendar.manage"),),
        "partial_update": (HasPermission("leave_management.holiday_calendar.manage"),),
        "destroy": (HasPermission("leave_management.holiday_calendar.manage"),),
    }
    pagination_class = StandardResultsSetPagination
    filterset_class = HolidayCalendarFilter

    def get_queryset(self):
        return HolidayCalendar.objects.all().order_by("date")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return HolidayCalendarWriteSerializer
        return HolidayCalendarReadSerializer


# -- Offline Leave Entry ------------------------------------------------------

class OfflineLeaveEntryViewSet(LeaveActionPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [HasModuleGrantLeave]
    action_permissions = {
        "metadata": (),
        "list": (HasPermission("leave_management.offline_leave.view"),),
        "retrieve": (HasPermission("leave_management.offline_leave.view"),),
        "create": (HasPermission("leave_management.offline_leave.record"),),
        "update": (HasPermission("leave_management.offline_leave.record"),),
        "partial_update": (HasPermission("leave_management.offline_leave.record"),),
        "destroy": (HasPermission("leave_management.offline_leave.record"),),
    }
    pagination_class = StandardResultsSetPagination
    filterset_class = OfflineLeaveEntryFilter

    def get_queryset(self):
        return OfflineLeaveEntry.objects.all().order_by("-start_date")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return OfflineLeaveEntryWriteSerializer
        return OfflineLeaveEntryReadSerializer


# -- Year End Processing ------------------------------------------------------

class YearEndProcessingViewSet(LeaveActionPermissionMixin, viewsets.ViewSet):
    permission_classes = [HasModuleGrantLeave]
    serializer_class = LeaveRequestReadSerializer
    action_permissions = {
        "metadata": (),
        "run": (HasPermission("leave_management.year_end.process"),),
    }

    @extend_schema(
        request=inline_serializer(
            name="YearEndProcessingRequest",
            fields={"year": serializers.IntegerField(required=False)},
        ),
        responses=inline_serializer(
            name="YearEndProcessingResponse",
            fields={
                "status": serializers.CharField(),
                "processed_users": serializers.IntegerField(),
                "errors": serializers.ListField(child=serializers.JSONField()),
            },
        ),
    )
    @action(detail=False, methods=["post"], url_path="run")
    def run(self, request):
        year = request.data.get("year", date.today().year)
        yep = process_year_end(year, request.principal)
        return Response(
            {
                "status": yep.status,
                "processed_users": yep.processed_users,
                "errors": yep.errors,
            }
        )
