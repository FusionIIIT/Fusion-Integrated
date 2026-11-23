"""API views for Gymkhana module."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.api.serializers import (
    BudgetRequestCreateSerializer,
    BudgetRequestSerializer,
    ClubCreateSerializer,
    ClubSerializer,
    EventBookingCreateSerializer,
    EventReportCreateSerializer,
    EventReportSerializer,
    LeadershipChangeSerializer,
    MembershipApplySerializer,
    MembershipApproveSerializer,
    MembershipSerializer,
    PollCreateSerializer,
    PollSerializer,
    SessionBookingCreateSerializer,
    VenueBookingSerializer,
    VoteSerializer,
)
from modules.gymkhana.selectors.bookings import get_booking_by_id, list_bookings
from modules.gymkhana.selectors.budgets import get_budget_by_id
from modules.gymkhana.selectors.clubs import get_club_by_id
from modules.gymkhana.selectors.polls import get_poll_by_id, list_active_polls_for_student
from modules.gymkhana.selectors.reports import get_event_report_by_id
from modules.gymkhana.selectors.scoping import (
    scope_budget_requests,
    scope_clubs,
    scope_event_reports,
    scope_memberships,
)
from modules.gymkhana.services.bookings import book_event, book_session
from modules.gymkhana.services.budgets import submit_budget_request
from modules.gymkhana.services.clubs import (
    approve_club,
    change_leadership,
    create_club,
)
from modules.gymkhana.services.memberships import apply_membership, approve_membership
from modules.gymkhana.services.polls import cast_vote, create_poll
from modules.gymkhana.services.reports import submit_event_report


# ==============================================================================
# Clubs
# ==============================================================================
class ClubListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]
    serializer_class = ClubSerializer

    @extend_schema(operation_id="gymkhana_list_clubs", responses={200: ClubSerializer(many=True)})
    def get(self, request):
        qs = scope_clubs(request.principal.user_id, request.principal.roles)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ClubSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="gymkhana_create_club",
        request=ClubCreateSerializer,
        responses={201: ClubSerializer},
    )
    def post(self, request):
        self.permission_classes = [
            HasModuleGrant("gymkhana"),
            HasPermission("gymkhana.club.create"),
        ]
        self.check_permissions(request)
        serializer = ClubCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club = create_club(
            name=serializer.validated_data["name"],
            category=serializer.validated_data["category"],
            description=serializer.validated_data["description"],
            coordinator_id=serializer.validated_data["coordinator_id"],
            co_coordinator_id=serializer.validated_data["co_coordinator_id"],
            faculty_councillor_id=serializer.validated_data["faculty_councillor_id"],
            creator_id=request.principal.user_id,
        )
        return Response(ClubSerializer(club).data, status=status.HTTP_201_CREATED)


class ClubDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]
    serializer_class = ClubSerializer

    @extend_schema(operation_id="gymkhana_get_club", responses={200: ClubSerializer})
    def get(self, request, pk: int):
        club = get_club_by_id(pk)
        return Response(ClubSerializer(club).data)


class ClubConfirmView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.approve")]
    serializer_class = ClubSerializer

    @extend_schema(operation_id="gymkhana_confirm_club", responses={200: ClubSerializer})
    def post(self, request, pk: int):
        club = approve_club(
            club_id=pk, approver_id=request.principal.user_id, roles=request.principal.roles
        )
        return Response(ClubSerializer(club).data)


class ClubLeadershipView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.manage")]
    serializer_class = ClubSerializer

    @extend_schema(
        operation_id="gymkhana_change_leadership",
        request=LeadershipChangeSerializer,
        responses={200: ClubSerializer},
    )
    def post(self, request, pk: int):
        serializer = LeadershipChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club = change_leadership(
            club_id=pk,
            actor_id=request.principal.user_id,
            new_coordinator_id=serializer.validated_data["coordinator_id"],
            new_co_coordinator_id=serializer.validated_data["co_coordinator_id"],
        )
        return Response(ClubSerializer(club).data)


# ==============================================================================
# Venue Bookings
# ==============================================================================
class BookingListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.booking.view")]
    serializer_class = VenueBookingSerializer

    @extend_schema(
        operation_id="gymkhana_list_bookings", responses={200: VenueBookingSerializer(many=True)}
    )
    def get(self, request):
        venue = request.query_params.get("venue")
        booking_date = request.query_params.get("booking_date")
        club_id = request.query_params.get("club_id")
        qs = list_bookings(
            venue=venue,
            booking_date=booking_date,
            club_id=int(club_id) if club_id else None,
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = VenueBookingSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class SessionBookingView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.booking.create")]
    serializer_class = VenueBookingSerializer

    @extend_schema(
        operation_id="gymkhana_book_session",
        request=SessionBookingCreateSerializer,
        responses={201: VenueBookingSerializer},
    )
    def post(self, request):
        serializer = SessionBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = book_session(
            club_id=serializer.validated_data["club_id"],
            actor_id=request.principal.user_id,
            venue=serializer.validated_data["venue"],
            booking_date=serializer.validated_data["booking_date"],
            start_time=serializer.validated_data["start_time"],
            end_time=serializer.validated_data["end_time"],
            name=serializer.validated_data.get("name", ""),
            description=serializer.validated_data.get("description", ""),
            poster_file=serializer.validated_data.get("poster_file"),
        )
        return Response(VenueBookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class EventBookingView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.booking.create")]
    serializer_class = VenueBookingSerializer

    @extend_schema(
        operation_id="gymkhana_book_event",
        request=EventBookingCreateSerializer,
        responses={201: VenueBookingSerializer},
    )
    def post(self, request):
        serializer = EventBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = book_event(
            club_id=serializer.validated_data["club_id"],
            actor_id=request.principal.user_id,
            venue=serializer.validated_data["venue"],
            booking_date=serializer.validated_data["booking_date"],
            start_time=serializer.validated_data["start_time"],
            end_time=serializer.validated_data["end_time"],
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            faculty_councillor_id=serializer.validated_data["faculty_councillor_id"],
            poster_file=serializer.validated_data.get("poster_file"),
        )
        return Response(VenueBookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.booking.view")]
    serializer_class = VenueBookingSerializer

    @extend_schema(operation_id="gymkhana_get_booking", responses={200: VenueBookingSerializer})
    def get(self, request, pk: int):
        booking = get_booking_by_id(pk)
        return Response(VenueBookingSerializer(booking).data)


# ==============================================================================
# Memberships
# ==============================================================================
class MembershipListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.membership.view")]
    serializer_class = MembershipSerializer

    @extend_schema(
        operation_id="gymkhana_list_memberships", responses={200: MembershipSerializer(many=True)}
    )
    def get(self, request):
        club_id = request.query_params.get("club_id")
        qs = scope_memberships(
            user_id=request.principal.user_id,
            roles=request.principal.roles,
            club_id=int(club_id) if club_id else None,
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = MembershipSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MembershipApplyView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.membership.create")]
    serializer_class = MembershipSerializer

    @extend_schema(
        operation_id="gymkhana_apply_membership",
        request=MembershipApplySerializer,
        responses={201: MembershipSerializer},
    )
    def post(self, request):
        serializer = MembershipApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mem = apply_membership(
            club_id=serializer.validated_data["club_id"],
            student_id=request.principal.user_id,
            description=serializer.validated_data.get("description", ""),
        )
        return Response(MembershipSerializer(mem).data, status=status.HTTP_201_CREATED)


class MembershipApproveView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.membership.approve")]
    serializer_class = MembershipSerializer

    @extend_schema(
        operation_id="gymkhana_approve_membership",
        request=MembershipApproveSerializer,
        responses={200: MembershipSerializer},
    )
    def post(self, request, pk: int):
        serializer = MembershipApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mem = approve_membership(
            membership_id=pk,
            actor_id=request.principal.user_id,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(MembershipSerializer(mem).data)


# ==============================================================================
# Voting Polls
# ==============================================================================
class PollListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.view")]
    serializer_class = PollSerializer

    @extend_schema(operation_id="gymkhana_list_polls", responses={200: PollSerializer(many=True)})
    def get(self, request):
        batch = getattr(request.principal, "batch", None)
        branch = getattr(request.principal, "discipline", None)
        qs = list_active_polls_for_student(batch=batch, branch=branch)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PollSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="gymkhana_create_poll",
        request=PollCreateSerializer,
        responses={201: PollSerializer},
    )
    def post(self, request):
        self.permission_classes = [
            HasModuleGrant("gymkhana"),
            HasPermission("gymkhana.poll.create"),
        ]
        self.check_permissions(request)
        serializer = PollCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_groups = [
            (tg.get("batch", "all"), tg.get("branch", "all"))
            for tg in serializer.validated_data.get("target_groups", [])
        ]
        poll = create_poll(
            club_id=serializer.validated_data["club_id"],
            actor_id=request.principal.user_id,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            expires_at=serializer.validated_data["expires_at"],
            choices=serializer.validated_data["choices"],
            target_groups=target_groups,
        )
        return Response(
            PollSerializer(poll, context={"request": request}).data, status=status.HTTP_201_CREATED
        )


class PollDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.view")]
    serializer_class = PollSerializer

    @extend_schema(operation_id="gymkhana_get_poll", responses={200: PollSerializer})
    def get(self, request, pk: int):
        poll = get_poll_by_id(pk)
        return Response(PollSerializer(poll, context={"request": request}).data)


class PollVoteView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.vote")]
    serializer_class = PollSerializer

    @extend_schema(
        operation_id="gymkhana_cast_vote",
        request=VoteSerializer,
        responses={200: PollSerializer},
    )
    def post(self, request, pk: int):
        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = getattr(request.principal, "batch", None)
        branch = getattr(request.principal, "discipline", None)
        cast_vote(
            poll_id=pk,
            student_id=request.principal.user_id,
            choice_id=serializer.validated_data["choice_id"],
            student_batch=batch,
            student_branch=branch,
        )
        poll = get_poll_by_id(pk)
        return Response(PollSerializer(poll, context={"request": request}).data)


# ==============================================================================
# Budget Requests
# ==============================================================================
class BudgetListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.budget.view")]
    serializer_class = BudgetRequestSerializer

    @extend_schema(
        operation_id="gymkhana_list_budgets", responses={200: BudgetRequestSerializer(many=True)}
    )
    def get(self, request):
        club_id = request.query_params.get("club_id")
        qs = scope_budget_requests(
            user_id=request.principal.user_id,
            roles=request.principal.roles,
            club_id=int(club_id) if club_id else None,
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BudgetRequestSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="gymkhana_submit_budget",
        request=BudgetRequestCreateSerializer,
        responses={201: BudgetRequestSerializer},
    )
    def post(self, request):
        self.permission_classes = [
            HasModuleGrant("gymkhana"),
            HasPermission("gymkhana.budget.create"),
        ]
        self.check_permissions(request)
        serializer = BudgetRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = submit_budget_request(
            club_id=serializer.validated_data["club_id"],
            actor_id=request.principal.user_id,
            amount=serializer.validated_data["amount"],
            purpose=serializer.validated_data["purpose"],
            description=serializer.validated_data.get("description", ""),
            supporting_file=serializer.validated_data["supporting_file"],
        )
        return Response(BudgetRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class BudgetDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.budget.view")]
    serializer_class = BudgetRequestSerializer

    @extend_schema(operation_id="gymkhana_get_budget", responses={200: BudgetRequestSerializer})
    def get(self, request, pk: int):
        req = get_budget_by_id(pk)
        scope_budget_requests(
            user_id=request.principal.user_id,
            roles=request.principal.roles,
            club_id=req.club_id,
        )
        return Response(BudgetRequestSerializer(req).data)


# ==============================================================================
# Event Reports
# ==============================================================================
class ReportListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.view")]
    serializer_class = EventReportSerializer

    @extend_schema(
        operation_id="gymkhana_list_reports", responses={200: EventReportSerializer(many=True)}
    )
    def get(self, request):
        club_id = request.query_params.get("club_id")
        qs = scope_event_reports(
            user_id=request.principal.user_id,
            roles=request.principal.roles,
            club_id=int(club_id) if club_id else None,
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = EventReportSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="gymkhana_submit_report",
        request=EventReportCreateSerializer,
        responses={201: EventReportSerializer},
    )
    def post(self, request):
        self.permission_classes = [
            HasModuleGrant("gymkhana"),
            HasPermission("gymkhana.report.create"),
        ]
        self.check_permissions(request)
        serializer = EventReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rep = submit_event_report(
            club_id=serializer.validated_data["club_id"],
            actor_id=request.principal.user_id,
            student_incharge_id=serializer.validated_data["student_incharge_id"],
            event_name=serializer.validated_data["event_name"],
            event_date=serializer.validated_data["event_date"],
            description=serializer.validated_data.get("description", ""),
            report_file=serializer.validated_data["report_file"],
        )
        return Response(EventReportSerializer(rep).data, status=status.HTTP_201_CREATED)


class ReportDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.view")]
    serializer_class = EventReportSerializer

    @extend_schema(operation_id="gymkhana_get_report", responses={200: EventReportSerializer})
    def get(self, request, pk: int):
        rep = get_event_report_by_id(pk)
        scope_event_reports(
            user_id=request.principal.user_id,
            roles=request.principal.roles,
            club_id=rep.club_id,
        )
        return Response(EventReportSerializer(rep).data)
