"""HTTP layer: parse, scope, delegate, serialise. Two gates on every view."""
from __future__ import annotations

from datetime import date

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.api import serializers as s
from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.domain.rules import Target
from modules.gymkhana.models import Club, Poll
from modules.gymkhana.selectors import scoping
from modules.gymkhana.selectors.clubs import leaders_by_club, own_membership_status
from modules.gymkhana.selectors.people import names_for
from modules.gymkhana.selectors.polls import own_votes, tallies
from modules.gymkhana.selectors.venues import current_venue_names
from modules.gymkhana.services import (
    bookings,
    budget,
    clubs,
    leadership,
    memberships,
    people,
    polls,
    reports,
)

MODULE = HasModuleGrant("gymkhana")


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.", code="invalid_filter") from exc


def _date_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise BadRequestError(f"{name} must be a date like 2026-12-01.",
                              code="invalid_filter") from exc


def _choice_param(params, name, allowed):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    if raw not in allowed:
        raise BadRequestError(f"{name} must be one of {', '.join(allowed)}.",
                              code="invalid_filter")
    return raw


def _ex(name, value, *, request=False):
    return OpenApiExample(name, value=value, request_only=request, response_only=not request)


CLUB_EX = _ex("club", {"id": 7, "name": "Robotics Club", "category": "technical",
                       "description": "Builds robots.", "status": "open",
                       "faculty_councillor_user_id": 2001, "approved_at": None,
                       "created_at": "2026-11-22T10:00:00+05:30",
                       "leaders": {"coordinator": 1001, "co_coordinator": 1002},
                       "my_membership": None})
ERROR_EX = _ex("refused", {"error": {"code": "venue_slot_taken", "message":
                                     "LHTC 101 is already booked from 10:00 to 11:00.",
                                     "details": [], "request_id": "…"}})


class _Paged(generics.ListAPIView):
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["actor"] = _actor(self.request)
        return ctx


# -- Clubs ---------------------------------------------------------------------
@extend_schema(parameters=[OpenApiParameter("status", str), OpenApiParameter("category", str)],
               examples=[CLUB_EX])
class ClubListView(_Paged):
    """Clubs in scope; Student Admin sees open ones too."""

    serializer_class = s.GymkhanaClubSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.club.view")]

    def get_queryset(self):
        params = self.request.query_params
        qs = scoping.clubs_for(_actor(self.request))
        status_ = _choice_param(params, "status", sm.STATES)
        category = _choice_param(params, "category", ("technical", "sports", "cultural"))
        if status_:
            qs = qs.filter(status=status_)
        if category:
            qs = qs.filter(category=category)
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        ctx = {**self.get_serializer_context(), **_club_context(page, request)}
        return self.get_paginated_response(s.GymkhanaClubSerializer(page, many=True,
                                                                    context=ctx).data)


@extend_schema(request=s.GymkhanaClubCreateSerializer,
               responses={201: s.GymkhanaClubSerializer},
               examples=[_ex("create", {"name": "Robotics Club", "category": "technical",
                                        "description": "Builds robots.",
                                        "coordinator_user_id": 1001,
                                        "co_coordinator_user_id": 1002,
                                        "faculty_councillor_user_id": 2001},
                             request=True), CLUB_EX])
class ClubCreateView(APIView):
    """UC-GYM-001."""

    permission_classes = [MODULE, HasPermission("gymkhana.club.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaClubCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        club = clubs.create_club(actor=_actor(request), **payload.validated_data)
        return Response(_club_out(club, request), status=status.HTTP_201_CREATED)


def _club_context(clubs, request) -> dict:
    ids = [c.pk for c in clubs]
    leaders = leaders_by_club(ids)
    people = [uid for roles in leaders.values() for uid in roles.values()]
    people += [c.faculty_councillor_user_id for c in clubs]
    return {"leaders": leaders, "names": names_for(people),
            "own_status": own_membership_status(_actor(request).user_id, ids)}


def _club_out(club: Club, request) -> dict:
    return s.GymkhanaClubSerializer(club, context=_club_context([club], request)).data


@extend_schema(request=None, responses=s.GymkhanaClubSerializer, examples=[CLUB_EX, ERROR_EX])
class ClubApproveView(APIView):
    """UC-GYM-011."""

    permission_classes = [MODULE, HasPermission("gymkhana.club.approve")]
    throttle_scope = "gymkhana_write"

    def post(self, request, pk: int):
        club = clubs.approve_club(actor=_actor(request), club_id=pk)
        return Response(_club_out(club, request))


@extend_schema(responses=s.GymkhanaMyClubsSerializer,
               examples=[_ex("mine", {"leading": [], "member_of": []})])
class MyClubsView(APIView):
    """Clubs the caller leads and confirmed clubs they belong to."""

    permission_classes = [MODULE, HasPermission("gymkhana.club.view")]

    def get(self, request):
        actor = _actor(request)
        leading = list(scoping.led_clubs(actor).order_by("name"))
        member_of = list(scoping.member_clubs(actor).order_by("name"))
        ctx = _club_context(leading + member_of, request)
        return Response({"leading": s.GymkhanaClubSerializer(leading, many=True, context=ctx).data,
                         "member_of": s.GymkhanaClubSerializer(member_of, many=True,
                                                       context=ctx).data})


@extend_schema(request=s.GymkhanaLeadershipSerializer,
               responses=s.GymkhanaLeadersOutSerializer,
               examples=[_ex("change", {"coordinator_user_id": 1003,
                                        "co_coordinator_user_id": 1004}, request=True),
                         _ex("leaders", {"coordinator": 1003, "co_coordinator": 1004})])
class LeadershipView(APIView):
    """UC-GYM-008."""

    permission_classes = [MODULE, HasPermission("gymkhana.leadership.assign")]
    throttle_scope = "gymkhana_write"

    def post(self, request, pk: int):
        payload = s.GymkhanaLeadershipSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return Response(leadership.change_leadership(actor=_actor(request), club_id=pk,
                                                     **payload.validated_data))


# -- Memberships ---------------------------------------------------------------
MEMBERSHIP_EX = _ex("membership", {"id": 3, "club": 7, "club_name": "Robotics Club",
                                   "user_id": 1005, "description": "I build drones.",
                                   "status": "open", "remarks": "", "approved_at": None,
                                   "created_at": "2026-11-22T10:00:00+05:30"})


@extend_schema(parameters=[OpenApiParameter("club", int), OpenApiParameter("status", str)],
               examples=[MEMBERSHIP_EX])
class MembershipListView(_Paged):
    """Own applications and applications to clubs the caller leads (AFR-GYM-020)."""

    serializer_class = s.GymkhanaMembershipSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.membership.view")]

    def get_queryset(self):
        params = self.request.query_params
        qs = scoping.memberships_for(_actor(self.request))
        club = _int_param(params, "club")
        status_ = _choice_param(params, "status", sm.STATES)
        if club is not None:
            qs = qs.filter(club_id=club)
        if status_:
            qs = qs.filter(status=status_)
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        ctx = {"names": names_for(m.user_id for m in page)}
        return self.get_paginated_response(s.GymkhanaMembershipSerializer(
            page, many=True, context=ctx).data)


@extend_schema(request=s.GymkhanaApplySerializer,
               responses={201: s.GymkhanaMembershipSerializer},
               examples=[_ex("apply", {"club_id": 7, "description": "I build drones."},
                             request=True), MEMBERSHIP_EX])
class ApplyView(APIView):
    """UC-GYM-004."""

    permission_classes = [MODULE, HasPermission("gymkhana.membership.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = memberships.apply(actor=_actor(request), **payload.validated_data)
        return Response(s.GymkhanaMembershipSerializer(row).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.GymkhanaApproveSerializer,
               responses=s.GymkhanaApprovalOutcomeSerializer(many=True),
               examples=[_ex("approve", {"ids": [3, 4], "remarks": "Welcome"}, request=True),
                         _ex("outcomes", [{"id": 3, "outcome": "approved",
                                           "code": "approved", "message": "Approved."}])])
class ApproveMembershipsView(APIView):
    """UC-GYM-005: each id is decided independently."""

    permission_classes = [MODULE, HasPermission("gymkhana.membership.approve")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaApproveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        outcomes = memberships.approve_many(actor=_actor(request), **payload.validated_data)
        return Response([o.__dict__ for o in outcomes])


# -- Venues and bookings -------------------------------------------------------
@extend_schema(responses=s.GymkhanaVenueListSerializer,
               examples=[_ex("venues", {"venues": ["LHTC 101", "Open Air Theatre"]})])
class VenueListView(APIView):
    """BR-GYM-020: the venues that can be booked now."""

    permission_classes = [MODULE, HasPermission("gymkhana.booking.create")]

    def get(self, request):
        return Response({"venues": current_venue_names()})


BOOKING_EX = _ex("booking", {"id": 9, "club": 7, "club_name": "Robotics Club",
                             "kind": "session", "venue_name": "LHTC 101",
                             "date": "2026-12-01", "start_time": "10:00:00",
                             "end_time": "11:00:00", "description": "Weekly build",
                             "poster_link": "", "event_name": "", "faculty_user_id": None,
                             "created_at": "2026-11-22T10:00:00+05:30"})


@extend_schema(parameters=[OpenApiParameter("club", int), OpenApiParameter("from", str),
                           OpenApiParameter("to", str)], examples=[BOOKING_EX])
class BookingListView(_Paged):
    """Bookings of clubs the caller leads or belongs to."""

    serializer_class = s.GymkhanaBookingSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.booking.view")]

    def get_queryset(self):
        params = self.request.query_params
        qs = scoping.bookings_for(_actor(self.request))
        club = _int_param(params, "club")
        start = _date_param(params, "from")
        end = _date_param(params, "to")
        if club is not None:
            qs = qs.filter(club_id=club)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs


@extend_schema(request=s.GymkhanaSessionCreateSerializer,
               responses={201: s.GymkhanaBookingSerializer},
               examples=[_ex("session", {"club_id": 7, "venue": "LHTC 101",
                                         "date": "2026-12-01", "start_time": "10:00",
                                         "end_time": "11:00", "description": "Weekly build",
                                         "poster_url": ""}, request=True),
                         BOOKING_EX, ERROR_EX])
class SessionCreateView(APIView):
    """UC-GYM-002."""

    permission_classes = [MODULE, HasPermission("gymkhana.booking.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaSessionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = bookings.book_session(actor=_actor(request), **payload.validated_data)
        return Response(s.GymkhanaBookingSerializer(row).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.GymkhanaEventCreateSerializer,
               responses={201: s.GymkhanaBookingSerializer},
               examples=[_ex("event", {"club_id": 7, "event_name": "RoboWars",
                                       "venue": "Open Air Theatre", "date": "2026-12-05",
                                       "start_time": "16:00", "end_time": "19:00",
                                       "description": "Annual contest",
                                       "poster_url": "https://drive.google.com/file/d/"
                                                     "1AbCdEfGhIjK/view"}, request=True),
                         BOOKING_EX, ERROR_EX])
class EventCreateView(APIView):
    """UC-GYM-003."""

    permission_classes = [MODULE, HasPermission("gymkhana.booking.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaEventCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = bookings.book_event(actor=_actor(request), **payload.validated_data)
        return Response(s.GymkhanaBookingSerializer(row).data, status=status.HTTP_201_CREATED)


# -- Polls ---------------------------------------------------------------------
POLL_EX = _ex("poll", {"id": 4, "club": 7, "club_name": "Robotics Club",
                       "title": "Next workshop", "description": "Pick a topic",
                       "expires_on": "2026-12-10", "created_at": "2026-11-22T10:00:00+05:30",
                       "choices": [{"id": 1, "label": "Drones"}, {"id": 2, "label": "ROS"}],
                       "my_choice_id": None})


@extend_schema(examples=[POLL_EX])
class OpenPollListView(_Paged):
    """Unexpired polls whose audience includes the caller (AFR-GYM-026)."""

    serializer_class = s.GymkhanaPollSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.poll.view")]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Poll.objects.none()
        batch_year, discipline = people.cohort_of(_actor(self.request).user_id)
        return (scoping.polls_targeting(batch_year, discipline)
                .filter(expires_on__gte=timezone.localdate())
                .prefetch_related("choices"))

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        ctx = {"own_votes": own_votes(_actor(request).user_id, [p.pk for p in page])}
        return self.get_paginated_response(s.GymkhanaPollSerializer(page, many=True,
                                                            context=ctx).data)


@extend_schema(parameters=[OpenApiParameter("club", int)],
               examples=[_ex("managed", {"id": 4, "title": "Next workshop",
                                         "choices": [{"id": 1, "label": "Drones",
                                                      "votes": 3}],
                                         "total_votes": 3})])
class ManagedPollListView(_Paged):
    """Polls of clubs the caller leads, with counts only (ruling R8)."""

    serializer_class = s.GymkhanaManagedPollSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.poll.create")]

    def get_queryset(self):
        qs = scoping.polls_managed_by(_actor(self.request)).prefetch_related(
            "choices", "targets")
        club = _int_param(self.request.query_params, "club")
        return qs.filter(club_id=club) if club is not None else qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        ctx = {"tallies": tallies([p.pk for p in page])}
        return self.get_paginated_response(s.GymkhanaManagedPollSerializer(page, many=True,
                                                                   context=ctx).data)


@extend_schema(request=s.GymkhanaPollCreateSerializer,
               responses={201: s.GymkhanaPollSerializer},
               examples=[_ex("poll", {"club_id": 7, "title": "Next workshop",
                                      "description": "Pick a topic",
                                      "expires_on": "2026-12-10",
                                      "choices": ["Drones", "ROS"],
                                      "targets": [{"batch_year": 2023,
                                                   "discipline": "CSE"}]}, request=True),
                         POLL_EX])
class PollCreateView(APIView):
    """UC-GYM-006."""

    permission_classes = [MODULE, HasPermission("gymkhana.poll.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaPollCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        data["targets"] = [Target(t["batch_year"], t.get("discipline", ""))
                           for t in data["targets"]]
        poll = polls.create_poll(actor=_actor(request), **data)
        return Response(s.GymkhanaPollSerializer(poll).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.GymkhanaVoteSerializer,
               responses={201: s.GymkhanaVoteSerializer},
               examples=[_ex("vote", {"choice_id": 1}, request=True),
                         _ex("recorded", {"choice_id": 1})])
class VoteView(APIView):
    """UC-GYM-007."""

    permission_classes = [MODULE, HasPermission("gymkhana.vote.create")]
    throttle_scope = "gymkhana_vote"

    def post(self, request, pk: int):
        payload = s.GymkhanaVoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        vote = polls.cast_vote(actor=_actor(request), poll_id=pk,
                               choice_id=payload.validated_data["choice_id"])
        return Response({"choice_id": vote.choice_id}, status=status.HTTP_201_CREATED)


# -- Budget requests -----------------------------------------------------------
BUDGET_EX = _ex("budget", {"id": 2, "club": 7, "club_name": "Robotics Club",
                           "purpose": "Parts", "description": "Motors", "amount": "4500.00",
                           "document_link": "https://drive.google.com/file/d/1AbCdEfGhIjK/view",
                           "status": "open", "submitted_by_user_id": 1001,
                           "created_at": "2026-11-22T10:00:00+05:30"})


@extend_schema(parameters=[OpenApiParameter("club", int)], examples=[BUDGET_EX])
class BudgetListView(_Paged):
    serializer_class = s.GymkhanaBudgetRequestSerializer
    permission_classes = [MODULE, HasPermission("gymkhana.budget_request.view")]

    def get_queryset(self):
        qs = scoping.budget_requests_for(_actor(self.request))
        club = _int_param(self.request.query_params, "club")
        return qs.filter(club_id=club) if club is not None else qs


@extend_schema(request=s.GymkhanaBudgetCreateSerializer,
               responses={201: s.GymkhanaBudgetRequestSerializer},
               examples=[_ex("submit", {"club_id": 7, "purpose": "Parts",
                                        "description": "Motors", "amount": "4500.00",
                                        "document_url": "https://drive.google.com/file/d/"
                                                        "1AbCdEfGhIjK/view"}, request=True),
                         BUDGET_EX])
class BudgetCreateView(APIView):
    """UC-GYM-009."""

    permission_classes = [MODULE, HasPermission("gymkhana.budget_request.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaBudgetCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = budget.submit(actor=_actor(request), **payload.validated_data)
        return Response(s.GymkhanaBudgetRequestSerializer(row).data, status=status.HTTP_201_CREATED)


# -- Event reports -------------------------------------------------------------
REPORT_EX = _ex("report", {"id": 5, "club": 7, "club_name": "Robotics Club",
                           "student_incharge_user_id": 1001, "event_name": "RoboWars",
                           "event_at": "2026-11-20T16:00:00+05:30",
                           "description": "Went well",
                           "report_link": "https://drive.google.com/file/d/1AbCdEfGhIjK/view",
                           "submitted_by_user_id": 1001,
                           "created_at": "2026-11-22T10:00:00+05:30"})
_REPORT_READ = HasPermission("gymkhana.event_report.view", "gymkhana.event_report.review")


@extend_schema(parameters=[OpenApiParameter("club", int)], examples=[REPORT_EX])
class ReportListView(_Paged):
    """UC-GYM-012 and the club's own reports."""

    serializer_class = s.GymkhanaEventReportSerializer
    permission_classes = [MODULE, _REPORT_READ]

    def get_queryset(self):
        qs = scoping.reports_for(_actor(self.request))
        club = _int_param(self.request.query_params, "club")
        return qs.filter(club_id=club) if club is not None else qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        ctx = {"names": names_for(r.student_incharge_user_id for r in page)}
        return self.get_paginated_response(s.GymkhanaEventReportSerializer(
            page, many=True, context=ctx).data)


@extend_schema(examples=[REPORT_EX])
class ReportDetailView(generics.RetrieveAPIView):
    """BR-GYM-021: any other club's report is a 404."""

    serializer_class = s.GymkhanaEventReportSerializer
    permission_classes = [MODULE, _REPORT_READ]

    def get_queryset(self):
        return scoping.reports_for(_actor(self.request))

    def retrieve(self, request, *args, **kwargs):
        report = self.get_object()
        ctx = {**self.get_serializer_context(),
               "names": names_for([report.student_incharge_user_id])}
        return Response(s.GymkhanaEventReportSerializer(report, context=ctx).data)


@extend_schema(request=s.GymkhanaEventReportCreateSerializer,
               responses={201: s.GymkhanaEventReportSerializer},
               examples=[_ex("submit", {"club_id": 7, "student_incharge_user_id": 1001,
                                        "event_name": "RoboWars",
                                        "event_at": "2026-11-20T16:00:00+05:30",
                                        "description": "Went well",
                                        "report_url": "https://drive.google.com/file/d/"
                                                      "1AbCdEfGhIjK/view"}, request=True),
                         REPORT_EX])
class ReportCreateView(APIView):
    """UC-GYM-010."""

    permission_classes = [MODULE, HasPermission("gymkhana.event_report.create")]
    throttle_scope = "gymkhana_write"

    def post(self, request):
        payload = s.GymkhanaEventReportCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = reports.submit(actor=_actor(request), **payload.validated_data)
        return Response(s.GymkhanaEventReportSerializer(row).data, status=status.HTTP_201_CREATED)


# -- People picker -------------------------------------------------------------
@extend_schema(parameters=[OpenApiParameter("q", str), OpenApiParameter("kind", str)],
               responses=s.GymkhanaPersonSerializer(many=True),
               examples=[_ex("people", [{"user_id": 1001, "username": "stu00001",
                                         "display_name": "Student One",
                                         "kind": "student"}])])
class PeopleSearchView(APIView):
    """For Student Admin and current Club Heads choosing a person."""

    permission_classes = [MODULE, HasPermission("gymkhana.club.create",
                                                "gymkhana.leadership.assign",
                                                "gymkhana.event_report.create")]
    throttle_scope = "directory_search"

    def get(self, request):
        params = request.query_params
        return Response(people.search(actor=_actor(request), q=params.get("q", ""),
                                      kind=params.get("kind", "student")))
