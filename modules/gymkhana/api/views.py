"""HTTP layer for Gymkhana: parse, scope, delegate, serialise.

Every view takes its queryset from `selectors.scoping` or uses `get_managed_club`
so authorization is never re-derived per endpoint. Anything out of scope is
absent (returns 404 rather than 403).
"""
from __future__ import annotations

from contextlib import contextmanager

from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.api import serializers as s
from modules.gymkhana.domain.exceptions import (
    ActorNotAllowed,
    GuardFailed,
    InvalidPollChoicesError,
    InvalidTimeRangeError,
    InvalidTransition,
    InvalidVenueError,
    InvalidVoteChoiceError,
)
from modules.gymkhana.models import (
    Booking,
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubMembership,
    Poll,
    PollVote,
)
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import (
    bookings as bookings_service,
    budgets as budgets_service,
    clubs as clubs_service,
    memberships as memberships_service,
    polls as polls_service,
    reports as reports_service,
)

MODULE = HasModuleGrant("gymkhana")


def _actor(request):
    """Retrieve the authenticated principal from the request."""
    return getattr(request, "principal", None)


@contextmanager
def translate_domain_exceptions():
    """Translate pure-Python domain exceptions into standard API exceptions."""
    try:
        yield
    except (InvalidTransition, ActorNotAllowed, GuardFailed) as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    except InvalidVenueError as exc:
        raise BadRequestError(str(exc), code="invalid_venue") from exc
    except InvalidTimeRangeError as exc:
        raise BadRequestError(str(exc), code="invalid_time_range") from exc
    except InvalidPollChoicesError as exc:
        raise BadRequestError(str(exc), code="invalid_poll_choices") from exc
    except InvalidVoteChoiceError as exc:
        raise BadRequestError(str(exc), code="invalid_vote_choice") from exc


# ---------------------------------------------------------------------------
# Clubs & Leadership (UC-GYM-001, UC-GYM-008, UC-GYM-011)
# ---------------------------------------------------------------------------


class ClubListView(generics.GenericAPIView):
    """List clubs (public sees confirmed; admin sees all) or create new club (Student Admin)."""

    queryset = Club.objects.none()
    serializer_class = s.ClubSummarySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("gymkhana.club.create")()]
        return [MODULE(), HasPermission("gymkhana.club.view")()]

    @extend_schema(responses={200: s.ClubSummarySerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        clubs = scoping.visible_clubs(actor).order_by("name")
        serializer = s.ClubSummarySerializer(clubs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=s.ClubCreateWriteSerializer, responses={201: s.ClubDetailSerializer})
    def post(self, request):
        actor = _actor(request)
        payload = s.ClubCreateWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        with translate_domain_exceptions():
            club = clubs_service.create_club(
                name=data["name"],
                category=data["category"],
                description=data["description"],
                coordinator_id=data["coordinator_id"],
                co_coordinator_id=data["co_coordinator_id"],
                faculty_councillor_id=data["faculty_councillor_id"],
                changed_by_user_id=actor.user_id,
            )
        return Response(s.ClubDetailSerializer(club).data, status=status.HTTP_201_CREATED)


class ClubDetailView(generics.GenericAPIView):
    """Retrieve club details if visible to the caller (UC-GYM-001, BR-GYM-004)."""

    queryset = Club.objects.none()
    serializer_class = s.ClubDetailSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.club.view")]

    @extend_schema(responses={200: s.ClubDetailSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        club = scoping.visible_clubs(actor).filter(pk=pk).first()
        if not club:
            raise NotFoundError(f"Club {pk} not found.", code="club_not_found")
        return Response(s.ClubDetailSerializer(club).data, status=status.HTTP_200_OK)


class ClubApproveView(generics.GenericAPIView):
    """Approve an open club to confirmed state (UC-GYM-011, BR-GYM-004)."""

    queryset = Club.objects.none()
    serializer_class = s.ClubDetailSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.club.approve")]

    @extend_schema(request=None, responses={200: s.ClubDetailSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        with translate_domain_exceptions():
            club = clubs_service.approve_club(
                club_id=pk,
                actor=actor,
                actor_user_id=actor.user_id,
            )
        return Response(s.ClubDetailSerializer(club).data, status=status.HTTP_200_OK)


class ClubLeadershipView(generics.GenericAPIView):
    """Replace club coordinators, retiring previous active tenure (UC-GYM-008, BR-GYM-016)."""

    queryset = Club.objects.none()
    serializer_class = s.ClubLeadershipWriteSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.leadership.update")]

    @extend_schema(request=s.ClubLeadershipWriteSerializer, responses={200: s.ClubDetailSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        club = scoping.get_managed_club(pk, actor.user_id)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        with translate_domain_exceptions():
            updated_club = clubs_service.change_leadership(
                club=club,
                new_coordinator_id=data["new_coordinator_id"],
                new_co_coordinator_id=data["new_co_coordinator_id"],
                changed_by_user_id=actor.user_id,
            )
        return Response(s.ClubDetailSerializer(updated_club).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Memberships (UC-GYM-004, UC-GYM-005)
# ---------------------------------------------------------------------------


class MembershipListView(generics.GenericAPIView):
    """List caller's own applications or apply for club membership (UC-GYM-004)."""

    queryset = ClubMembership.objects.none()
    serializer_class = s.MembershipSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("gymkhana.membership.create")()]
        return [MODULE(), HasPermission("gymkhana.membership.view")()]

    @extend_schema(responses={200: s.MembershipSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        memberships = scoping.visible_memberships(actor).order_by("-created_at")
        serializer = s.MembershipSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=s.MembershipApplyWriteSerializer, responses={201: s.MembershipSerializer})
    def post(self, request):
        actor = _actor(request)
        payload = s.MembershipApplyWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        club_id = payload.validated_data["club_id"]

        try:
            club = Club.objects.get(pk=club_id)
        except Club.DoesNotExist as exc:
            raise NotFoundError(f"Club {club_id} not found.", code="club_not_found") from exc

        with translate_domain_exceptions():
            membership = memberships_service.apply_membership(
                club=club,
                student_id=actor.user_id,
            )
        return Response(s.MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class ClubMembershipListView(generics.GenericAPIView):
    """List pending/all applications for a specific club (UC-GYM-005, AFR-GYM-020)."""

    queryset = ClubMembership.objects.none()
    serializer_class = s.MembershipSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.membership.view")]

    @extend_schema(responses={200: s.MembershipSerializer(many=True)})
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.visible_memberships(actor, club_id=pk)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = s.MembershipSerializer(qs.order_by("-created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MembershipApproveView(generics.GenericAPIView):
    """Approve a club membership application with optional remarks (UC-GYM-005)."""

    queryset = ClubMembership.objects.none()
    serializer_class = s.MembershipApproveWriteSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.membership.approve")]

    @extend_schema(request=s.MembershipApproveWriteSerializer, responses={200: s.MembershipSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)

        with translate_domain_exceptions():
            membership = memberships_service.approve_membership(
                membership_id=pk,
                actor_user_id=actor.user_id,
            )
        return Response(s.MembershipSerializer(membership).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Bookings (Calendar, Sessions, Events) (UC-GYM-002, UC-GYM-003)
# ---------------------------------------------------------------------------


class BookingListView(generics.GenericAPIView):
    """Public calendar schedule of club sessions and events (BR-GYM-006)."""

    queryset = Booking.objects.none()
    serializer_class = s.BookingSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.session.view")]

    @extend_schema(responses={200: s.BookingSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.visible_bookings(actor)

        date_val = request.query_params.get("date")
        if date_val:
            qs = qs.filter(date=date_val)
        venue_val = request.query_params.get("venue")
        if venue_val:
            qs = qs.filter(venue=venue_val)
        btype = request.query_params.get("booking_type")
        if btype:
            qs = qs.filter(booking_type=btype)
        cid = request.query_params.get("club_id")
        if cid:
            try:
                qs = qs.filter(club_id=int(cid))
            except (ValueError, TypeError):
                pass

        serializer = s.BookingSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionBookingView(generics.GenericAPIView):
    """Book a club session under VenueDayLock (UC-GYM-002, AFR-GYM-010)."""

    queryset = Booking.objects.none()
    serializer_class = s.SessionBookingWriteSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.session.create")]

    @extend_schema(request=s.SessionBookingWriteSerializer, responses={201: s.BookingSerializer})
    def post(self, request):
        actor = _actor(request)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        club = scoping.get_managed_club(data["club_id"], actor.user_id)
        with translate_domain_exceptions():
            booking = bookings_service.book_session(
                club=club,
                venue=data["venue"],
                date=data["date"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                name=data.get("name", ""),
                description=data["description"],
                poster_url=data.get("poster_url", ""),
                user_id=actor.user_id,
            )
        return Response(s.BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class EventBookingView(generics.GenericAPIView):
    """Book a club event under VenueDayLock with faculty context (UC-GYM-003, AFR-GYM-014)."""

    queryset = Booking.objects.none()
    serializer_class = s.EventBookingWriteSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.event.create")]

    @extend_schema(request=s.EventBookingWriteSerializer, responses={201: s.BookingSerializer})
    def post(self, request):
        actor = _actor(request)
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        club = scoping.get_managed_club(data["club_id"], actor.user_id)
        with translate_domain_exceptions():
            booking = bookings_service.book_event(
                club=club,
                faculty_councillor_id=data.get("faculty_councillor_id"),
                venue=data["venue"],
                date=data["date"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                name=data["name"],
                description=data["description"],
                poster_url=data.get("poster_url", ""),
                user_id=actor.user_id,
            )
        return Response(s.BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Polls & Voting (UC-GYM-006, UC-GYM-007)
# ---------------------------------------------------------------------------


class PollListView(generics.GenericAPIView):
    """List eligible voting polls or create a new targeted poll (UC-GYM-006)."""

    queryset = Poll.objects.none()
    serializer_class = s.PollSummarySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("gymkhana.poll.create")()]
        return [MODULE(), HasPermission("gymkhana.poll.view")()]

    @extend_schema(responses={200: s.PollSummarySerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        polls = scoping.visible_polls(actor).order_by("-created_at")
        serializer = s.PollSummarySerializer(polls, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=s.PollCreateWriteSerializer, responses={201: s.PollDetailSerializer})
    def post(self, request):
        actor = _actor(request)
        payload = s.PollCreateWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        club = scoping.get_managed_club(data["club_id"], actor.user_id)
        with translate_domain_exceptions():
            poll = polls_service.create_poll(
                club=club,
                title=data["title"],
                description=data["description"],
                expires_at=data["expires_at"],
                choices=data["choices"],
                targets=data["targets"],
                user_id=actor.user_id,
            )
        serializer = s.PollDetailSerializer(poll, context={"actor": actor})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PollDetailView(generics.GenericAPIView):
    """View details of a poll including choices, dynamic tallies, and voting status (UC-GYM-007)."""

    queryset = Poll.objects.none()
    serializer_class = s.PollDetailSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.poll.view")]

    @extend_schema(responses={200: s.PollDetailSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        poll = scoping.visible_polls(actor).filter(pk=pk).first()
        if not poll:
            raise NotFoundError(f"Poll {pk} not found.", code="poll_not_found")

        serializer = s.PollDetailSerializer(poll, context={"actor": actor})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PollVoteView(generics.GenericAPIView):
    """Cast a single vote in an active, unexpired targeted poll (UC-GYM-007)."""

    queryset = PollVote.objects.none()
    serializer_class = s.PollVoteWriteSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.poll.update")]

    @extend_schema(request=s.PollVoteWriteSerializer, responses={200: s.PollVoteResultSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        poll = scoping.visible_polls(actor).filter(pk=pk).first()
        if not poll:
            raise NotFoundError("Poll not found or not eligible to vote.", code="poll_not_found")

        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        choice_id = payload.validated_data["choice_id"]

        with translate_domain_exceptions():
            vote = polls_service.cast_vote(
                poll=poll,
                choice_id=choice_id,
                student_id=actor.user_id,
            )
        return Response(s.PollVoteResultSerializer(vote).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Budgets (UC-GYM-009)
# ---------------------------------------------------------------------------


class ClubBudgetListView(generics.GenericAPIView):
    """List or submit club budget requests (UC-GYM-009, AFR-GYM-029)."""

    queryset = ClubBudgetRequest.objects.none()
    serializer_class = s.BudgetRequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("gymkhana.budget.create")()]
        return [MODULE(), HasPermission("gymkhana.budget.view")()]

    @extend_schema(responses={200: s.BudgetRequestSerializer(many=True)})
    def get(self, request, pk: int):
        actor = _actor(request)
        budgets = scoping.visible_budget_requests(actor, club_id=pk).order_by("-created_at")
        serializer = s.BudgetRequestSerializer(budgets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=s.BudgetRequestWriteSerializer, responses={201: s.BudgetRequestSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        club = scoping.get_managed_club(pk, actor.user_id)
        payload = s.BudgetRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        with translate_domain_exceptions():
            budget = budgets_service.submit_budget_request(
                club=club,
                amount=data["amount"],
                purpose=data["purpose"],
                description=data["description"],
                supporting_file_url=data["supporting_file_url"],
                user_id=actor.user_id,
            )
        return Response(s.BudgetRequestSerializer(budget).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Event Reports (UC-GYM-010, UC-GYM-012)
# ---------------------------------------------------------------------------


class ClubReportListView(generics.GenericAPIView):
    """List or submit event reports for a club (UC-GYM-010, AFR-GYM-032)."""

    queryset = ClubEventReport.objects.none()
    serializer_class = s.EventReportSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("gymkhana.report.create")()]
        return [MODULE(), HasPermission("gymkhana.report.view")()]

    @extend_schema(responses={200: s.EventReportSerializer(many=True)})
    def get(self, request, pk: int):
        actor = _actor(request)
        reports = scoping.visible_event_reports(actor, club_id=pk).order_by("-created_at")
        serializer = s.EventReportSerializer(reports, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=s.EventReportWriteSerializer, responses={201: s.EventReportSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        club = scoping.get_managed_club(pk, actor.user_id)
        payload = s.EventReportWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        with translate_domain_exceptions():
            report = reports_service.submit_event_report(
                club=club,
                student_incharge_id=data["student_incharge_id"],
                event_name=data["event_name"],
                event_date=data["event_date"],
                event_time=data["event_time"],
                description=data["description"],
                report_file_url=data["report_file_url"],
                user_id=actor.user_id,
            )
        return Response(s.EventReportSerializer(report).data, status=status.HTTP_201_CREATED)


class EventReportDetailView(generics.GenericAPIView):
    """View details of a submitted event report (UC-GYM-012, AFR-GYM-034)."""

    queryset = ClubEventReport.objects.none()
    serializer_class = s.EventReportDetailSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.report.view")]

    @extend_schema(responses={200: s.EventReportDetailSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        report = scoping.visible_event_reports(actor, report_id=pk).first()
        if not report:
            raise NotFoundError(f"Report {pk} not found.", code="report_not_found")
        return Response(s.EventReportDetailSerializer(report).data, status=status.HTTP_200_OK)


class EventReportDownloadView(generics.GenericAPIView):
    """Download/access supporting documentation for an event report via HTTP 302 (UC-GYM-012)."""

    queryset = ClubEventReport.objects.none()
    serializer_class = s.EventReportDetailSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.report.review")]

    @extend_schema(responses={302: None})
    def get(self, request, pk: int):
        actor = _actor(request)
        report = scoping.visible_event_reports(actor, report_id=pk).first()
        if not report:
            raise NotFoundError(f"Report {pk} not found.", code="report_not_found")

        response = HttpResponseRedirect(report.report_file_url)
        response["Referrer-Policy"] = "no-referrer"
        response["Cache-Control"] = "private, no-store"
        return response
