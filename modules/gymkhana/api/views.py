from datetime import datetime

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.api import serializers as s
from modules.gymkhana.selectors import (
    bookings as booking_selectors,
)
from modules.gymkhana.selectors import (
    budgets as budget_selectors,
)
from modules.gymkhana.selectors import (
    clubs as club_selectors,
)
from modules.gymkhana.selectors import (
    memberships as membership_selectors,
)
from modules.gymkhana.selectors import (
    polls as poll_selectors,
)
from modules.gymkhana.selectors import (
    reports as report_selectors,
)
from modules.gymkhana.services import (
    bookings as booking_services,
)
from modules.gymkhana.services import (
    budgets as budget_services,
)
from modules.gymkhana.services import (
    clubs as club_services,
)
from modules.gymkhana.services import (
    leadership as leadership_services,
)
from modules.gymkhana.services import (
    memberships as membership_services,
)
from modules.gymkhana.services import (
    polls as poll_services,
)
from modules.gymkhana.services import (
    reports as report_services,
)


def _get_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None):
        return int(principal.user_id)
    if request.user and request.user.is_authenticated:
        return int(getattr(request.user, "user_id", getattr(request.user, "id", 0)))
    return 0


class ClubListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("gymkhana")(), HasPermission("gymkhana.club.create")()]
        return [HasModuleGrant("gymkhana")(), HasPermission("gymkhana.club.view")()]

    @extend_schema(responses={200: s.ClubSerializer(many=True)})
    def get(self, request):
        status_filter = request.query_params.get("status")
        category_filter = request.query_params.get("category")
        clubs = club_selectors.list_clubs(
            request.user, status=status_filter, category=category_filter
        )
        return Response(s.ClubSerializer(clubs, many=True).data)

    @extend_schema(request=s.ClubCreateSerializer, responses={201: s.ClubSerializer})
    def post(self, request):
        ser = s.ClubCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        club = club_services.create_club(**ser.validated_data)
        return Response(s.ClubSerializer(club).data, status=status.HTTP_201_CREATED)


class ClubDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]

    @extend_schema(responses={200: s.ClubSerializer})
    def get(self, request, pk: int):
        club = club_selectors.get_club(pk)
        if not club:
            raise NotFoundError("Club not found.", code="club_not_found")
        return Response(s.ClubSerializer(club).data)


class ClubConfirmView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.approve")]

    @extend_schema(request=None, responses={200: s.ClubSerializer})
    def post(self, request, pk: int):
        club = club_services.confirm_club(pk)
        return Response(s.ClubSerializer(club).data)


class ClubLeadershipChangeView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.leadership.update")]

    @extend_schema(request=s.ClubLeadershipChangeSerializer, responses={200: s.ClubSerializer})
    def post(self, request, pk: int):
        ser = s.ClubLeadershipChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        club = leadership_services.change_leadership(
            club_id=pk,
            acting_user_id=user_id,
            **ser.validated_data,
        )
        return Response(s.ClubSerializer(club).data)


class ClubSessionBookingView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.session.book")]

    @extend_schema(request=s.ClubBookingCreateSerializer, responses={201: s.ClubBookingSerializer})
    def post(self, request, pk: int):
        ser = s.ClubBookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        booking = booking_services.book_session(
            club_id=pk,
            acting_user_id=user_id,
            booking_date=ser.validated_data["date"],
            start_time=ser.validated_data["start_time"],
            end_time=ser.validated_data["end_time"],
            title=ser.validated_data["title"],
            venue=ser.validated_data["venue"],
            description=ser.validated_data.get("description", ""),
        )
        return Response(s.ClubBookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class ClubEventBookingView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.event.book")]

    @extend_schema(request=s.ClubBookingCreateSerializer, responses={201: s.ClubBookingSerializer})
    def post(self, request, pk: int):
        ser = s.ClubBookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        booking = booking_services.book_event(
            club_id=pk,
            acting_user_id=user_id,
            booking_date=ser.validated_data["date"],
            start_time=ser.validated_data["start_time"],
            end_time=ser.validated_data["end_time"],
            title=ser.validated_data["title"],
            venue=ser.validated_data["venue"],
            description=ser.validated_data.get("description", ""),
        )
        return Response(s.ClubBookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class ClubBookingListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]

    @extend_schema(responses={200: s.ClubBookingSerializer(many=True)})
    def get(self, request, pk: int):
        club = club_selectors.get_club(pk)
        if not club:
            raise NotFoundError("Club not found.", code="club_not_found")
        date_str = request.query_params.get("date")
        booking_date = None
        if date_str:
            try:
                booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as exc:
                msg = "Date must be in YYYY-MM-DD format."
                raise BadRequestError(msg, code="invalid_date_format") from exc
        bookings = booking_selectors.list_bookings(request.user, club, booking_date=booking_date)
        return Response(s.ClubBookingSerializer(bookings, many=True).data)


class ClubMembershipApplyView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.membership.apply")]

    @extend_schema(
        request=s.ClubMembershipApplySerializer, responses={201: s.ClubMembershipSerializer}
    )
    def post(self, request, pk: int):
        ser = s.ClubMembershipApplySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        membership = membership_services.apply_membership(
            club_id=pk,
            student_id=user_id,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(s.ClubMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class ClubMembershipListView(APIView):
    permission_classes = [
        HasModuleGrant("gymkhana"),
        HasPermission("gymkhana.membership.approve"),
    ]

    @extend_schema(responses={200: s.ClubMembershipSerializer(many=True)})
    def get(self, request, pk: int):
        club = club_selectors.get_club(pk)
        if not club:
            raise NotFoundError("Club not found.", code="club_not_found")
        status_filter = request.query_params.get("status")
        memberships = membership_selectors.list_memberships(
            request.user, club, status=status_filter
        )
        return Response(s.ClubMembershipSerializer(memberships, many=True).data)


class MembershipApproveView(APIView):
    permission_classes = [
        HasModuleGrant("gymkhana"),
        HasPermission("gymkhana.membership.approve"),
    ]

    @extend_schema(
        request=s.ClubMembershipApplySerializer, responses={200: s.ClubMembershipSerializer}
    )
    def post(self, request, pk: int):
        user_id = _get_user_id(request)
        remarks = request.data.get("remarks", "")
        membership = membership_services.approve_membership(
            membership_id=pk,
            acting_user_id=user_id,
            remarks=remarks,
        )
        return Response(s.ClubMembershipSerializer(membership).data)


class ClubPollCreateView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.create")]

    @extend_schema(request=s.VotingPollCreateSerializer, responses={201: s.VotingPollSerializer})
    def post(self, request, pk: int):
        ser = s.VotingPollCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        poll = poll_services.create_poll(
            club_id=pk,
            acting_user_id=user_id,
            title=ser.validated_data["title"],
            description=ser.validated_data.get("description", ""),
            target_batches=ser.validated_data.get("target_batches", []),
            target_branches=ser.validated_data.get("target_branches", []),
            expires_at=ser.validated_data["expires_at"],
            choices=ser.validated_data["choices"],
        )
        return Response(s.VotingPollSerializer(poll).data, status=status.HTTP_201_CREATED)


class ActivePollListView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.vote")]

    @extend_schema(responses={200: s.VotingPollSerializer(many=True)})
    def get(self, request):
        polls = poll_selectors.list_active_polls(request.user)
        return Response(s.VotingPollSerializer(polls, many=True).data)


class PollVoteView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.vote")]

    @extend_schema(request=s.PollVoteSerializer, responses={200: s.PollVoteResponseSerializer})
    def post(self, request, pk: int):
        ser = s.PollVoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        vote = poll_services.cast_vote(
            poll_id=pk,
            student_id=user_id,
            choice_id=ser.validated_data["choice_id"],
        )
        return Response({"status": "vote_recorded", "vote_id": vote.id})


class ClubBudgetRequestView(APIView):
    def get_permissions(self):
        return [
            HasModuleGrant("gymkhana")(),
            HasPermission("gymkhana.budget.request")(),
        ]

    @extend_schema(responses={200: s.ClubBudgetRequestSerializer(many=True)})
    def get(self, request, pk: int):
        club = club_selectors.get_club(pk)
        if not club:
            raise NotFoundError("Club not found.", code="club_not_found")
        requests = budget_selectors.list_budget_requests(request.user, club)
        return Response(s.ClubBudgetRequestSerializer(requests, many=True).data)

    @extend_schema(
        request=s.ClubBudgetRequestCreateSerializer,
        responses={201: s.ClubBudgetRequestSerializer},
    )
    def post(self, request, pk: int):
        ser = s.ClubBudgetRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        budget = budget_services.submit_budget_request(
            club_id=pk,
            acting_user_id=user_id,
            amount=ser.validated_data["amount"],
            purpose=ser.validated_data["purpose"],
            description=ser.validated_data["description"],
            supporting_file=ser.validated_data["supporting_file"],
        )
        return Response(s.ClubBudgetRequestSerializer(budget).data, status=status.HTTP_201_CREATED)


class ClubEventReportSubmitView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.submit")]

    @extend_schema(
        request=s.ClubEventReportCreateSerializer,
        responses={201: s.ClubEventReportSerializer},
    )
    def post(self, request, pk: int):
        ser = s.ClubEventReportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = _get_user_id(request)
        report = report_services.submit_event_report(
            club_id=pk,
            acting_user_id=user_id,
            title=ser.validated_data["title"],
            description=ser.validated_data["description"],
            report_file=ser.validated_data["report_file"],
        )
        return Response(s.ClubEventReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ClubEventReportReviewView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.review")]

    @extend_schema(responses={200: s.ClubEventReportSerializer(many=True)})
    def get(self, request, pk: int):
        club = club_selectors.get_club(pk)
        if not club:
            raise NotFoundError("Club not found.", code="club_not_found")
        reports = report_selectors.list_event_reports(request.user, club)
        return Response(s.ClubEventReportSerializer(reports, many=True).data)
