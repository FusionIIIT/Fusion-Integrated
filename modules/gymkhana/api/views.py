"""API views for Gymkhana module."""

from __future__ import annotations

from django.http import FileResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from core.api.pagination import CursorPagination
from core.files.validators import sanitise_filename
from modules.gymkhana.api import serializers as s
from modules.gymkhana.api.params import date_param, int_param, text_param
from modules.gymkhana.api.permissions import MODULE, Acting
from modules.gymkhana.selectors.access import acting_permissions, acting_roles
from modules.gymkhana.selectors.bookings import get_booking_by_id, list_bookings
from modules.gymkhana.selectors.people import (
    display_names,
    poll_group_options,
    search_people,
    student_group,
)
from modules.gymkhana.selectors.polls import polls_for
from modules.gymkhana.selectors.scoping import (
    clubs_led_by,
    scope_budget_requests,
    scope_clubs,
    scope_event_reports,
    scope_memberships,
)
from modules.gymkhana.selectors.venues import configured_venues
from modules.gymkhana.services.bookings import book_event, book_session
from modules.gymkhana.services.budgets import submit_budget_request
from modules.gymkhana.services.clubs import approve_club, change_leadership, create_club
from modules.gymkhana.services.memberships import apply_membership, approve_membership
from modules.gymkhana.services.polls import cast_vote, create_poll
from modules.gymkhana.services.reports import submit_event_report

MIN_SEARCH = 3

FILE_RESPONSES = {
    (200, "application/octet-stream"): OpenApiTypes.BINARY,
    404: OpenApiResponse(description="Absent, or outside the caller's scope."),
}


def int_query(name: str) -> OpenApiParameter:
    return OpenApiParameter(name, OpenApiTypes.INT, OpenApiParameter.QUERY)


def text_query(name: str) -> OpenApiParameter:
    return OpenApiParameter(name, OpenApiTypes.STR, OpenApiParameter.QUERY)


class GymkhanaView(APIView):
    """Both gates on every method; a write is checked against its own permission and throttled."""

    read_codes: tuple[str, ...] = ()
    write_codes: tuple[str, ...] = ()

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            codes = self.read_codes or self.write_codes
        else:
            # A method the view lacks must reach DRF's own 405.
            codes = self.write_codes or self.read_codes
        return [MODULE(), Acting(*codes)()]

    @property
    def throttle_scope(self):
        request = getattr(self, "request", None)
        if request is None or request.method in SAFE_METHODS:
            return None
        return "gymkhana_write"

    @property
    def actor_id(self) -> int:
        return self.request.principal.user_id

    @property
    def roles(self) -> frozenset[str]:
        return acting_roles(self.request.principal)

    def page(self, queryset, serializer_class, people=()):
        paginator = CursorPagination()
        rows = paginator.paginate_queryset(queryset, self.request)
        data = serializer_class(rows, many=True, context=self.names(rows, people)).data
        return paginator.get_paginated_response(data)

    def names(self, rows, people) -> dict:
        ids = [getattr(row, field) for row in rows for field in people]
        return {"names": display_names(ids)}

    def one(self, row, serializer_class, people=(), http_status=status.HTTP_200_OK):
        data = serializer_class(row, context=self.names([row], people)).data
        return Response(data, status=http_status)

    def found(self, queryset, pk: int):
        row = queryset.filter(pk=pk).first()
        if row is None:
            raise NotFoundError("Not found.")
        return row

    def valid(self, serializer_class) -> dict:
        serializer = serializer_class(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


def file_response(stored, name: str) -> FileResponse:
    """Always a download, never rendered on this origin."""
    if not stored or not stored.storage.exists(stored.name):
        raise NotFoundError("This file is not available.")
    extension = stored.name.rsplit(".", 1)[-1]
    response = FileResponse(
        stored.open("rb"),
        as_attachment=True,
        filename=f"{sanitise_filename(name)}.{extension}",
        content_type="application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


# ==============================================================================
# The caller, and what a form needs to offer
# ==============================================================================
class AccessView(GymkhanaView):
    """What the acting role may do here, so no screen offers what the server would refuse."""

    read_codes = ("gymkhana.club.view",)

    @extend_schema(operation_id="gymkhana_access", responses={200: s.AccessSerializer})
    def get(self, request):
        return Response(
            {
                "permissions": acting_permissions(request.principal),
                "clubs_led": s.LedClubSerializer(
                    clubs_led_by(self.actor_id).order_by("name"), many=True
                ).data,
            }
        )


class VenueListView(GymkhanaView):
    read_codes = ("gymkhana.booking.view",)

    @extend_schema(operation_id="gymkhana_list_venues", responses={200: s.VenueListSerializer})
    def get(self, request):
        return Response({"venues": configured_venues()})


class PollOptionsView(GymkhanaView):
    read_codes = ("gymkhana.poll.create",)

    @extend_schema(operation_id="gymkhana_poll_options", responses={200: s.PollOptionsSerializer})
    def get(self, request):
        if not clubs_led_by(self.actor_id).exists():
            raise NotFoundError("Not found.")
        return Response(poll_group_options())


class PeopleSearchView(GymkhanaView):
    """A picker for people who assign someone: Student Admin, or the head of a club."""

    read_codes = ("gymkhana.club.create", "gymkhana.club.manage")
    throttle_scope = "directory_search"

    @extend_schema(
        operation_id="gymkhana_search_people",
        parameters=[
            OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("kind", str, OpenApiParameter.QUERY, enum=["student", "faculty"]),
        ],
        responses={200: s.PeopleSerializer},
    )
    def get(self, request):
        may_assign = "gymkhana.club.create" in acting_permissions(request.principal)
        if not may_assign and not clubs_led_by(self.actor_id).exists():
            raise NotFoundError("Not found.")
        q = text_param(request, "q")
        kind = "faculty" if text_param(request, "kind") == "faculty" else "student"
        # Shorter than this is an enumeration of the institute, not a search.
        results = search_people(q, kind) if len(q) >= MIN_SEARCH else []
        return Response({"results": results})


# ==============================================================================
# Clubs
# ==============================================================================
CLUB_PEOPLE = ("coordinator_id", "co_coordinator_id", "faculty_councillor_id")


class ClubListView(GymkhanaView):
    read_codes = ("gymkhana.club.view",)
    write_codes = ("gymkhana.club.create",)

    @extend_schema(operation_id="gymkhana_list_clubs", responses={200: s.ClubSerializer(many=True)})
    def get(self, request):
        return self.page(scope_clubs(self.actor_id, self.roles), s.ClubSerializer, CLUB_PEOPLE)

    @extend_schema(
        operation_id="gymkhana_create_club",
        request=s.ClubCreateSerializer,
        responses={201: s.ClubSerializer},
    )
    def post(self, request):
        club = create_club(creator_id=self.actor_id, **self.valid(s.ClubCreateSerializer))
        return self.one(club, s.ClubSerializer, CLUB_PEOPLE, status.HTTP_201_CREATED)


class ClubDetailView(GymkhanaView):
    read_codes = ("gymkhana.club.view",)

    @extend_schema(operation_id="gymkhana_get_club", responses={200: s.ClubSerializer})
    def get(self, request, pk: int):
        club = self.found(scope_clubs(self.actor_id, self.roles), pk)
        return self.one(club, s.ClubSerializer, CLUB_PEOPLE)


class ClubConfirmView(GymkhanaView):
    write_codes = ("gymkhana.club.approve",)

    @extend_schema(
        operation_id="gymkhana_confirm_club", request=None, responses={200: s.ClubSerializer}
    )
    def post(self, request, pk: int):
        club = approve_club(club_id=pk, approver_id=self.actor_id, roles=sorted(self.roles))
        return self.one(club, s.ClubSerializer, CLUB_PEOPLE)


class ClubLeadershipView(GymkhanaView):
    write_codes = ("gymkhana.club.manage",)

    @extend_schema(
        operation_id="gymkhana_change_leadership",
        request=s.LeadershipChangeSerializer,
        responses={200: s.ClubSerializer},
    )
    def post(self, request, pk: int):
        data = self.valid(s.LeadershipChangeSerializer)
        club = change_leadership(
            club_id=pk,
            actor_id=self.actor_id,
            new_coordinator_id=data["coordinator_id"],
            new_co_coordinator_id=data["co_coordinator_id"],
        )
        return self.one(club, s.ClubSerializer, CLUB_PEOPLE)


# ==============================================================================
# Venue Bookings
# ==============================================================================
class BookingListView(GymkhanaView):
    read_codes = ("gymkhana.booking.view",)

    @extend_schema(
        operation_id="gymkhana_list_bookings",
        parameters=[text_query("venue"), text_query("booking_date"), int_query("club_id")],
        responses={200: s.VenueBookingSerializer(many=True)},
    )
    def get(self, request):
        queryset = list_bookings(
            venue=text_param(request, "venue") or None,
            booking_date=date_param(request, "booking_date"),
            club_id=int_param(request, "club_id"),
        )
        return self.page(queryset, s.VenueBookingSerializer)


class SessionBookingView(GymkhanaView):
    write_codes = ("gymkhana.booking.create",)

    @extend_schema(
        operation_id="gymkhana_book_session",
        request=s.SessionBookingCreateSerializer,
        responses={201: s.VenueBookingSerializer},
    )
    def post(self, request):
        data = self.valid(s.SessionBookingCreateSerializer)
        booking = book_session(actor_id=self.actor_id, **data)
        return self.one(
            booking, s.VenueBookingSerializer, http_status=status.HTTP_201_CREATED
        )


class EventBookingView(GymkhanaView):
    write_codes = ("gymkhana.booking.create",)

    @extend_schema(
        operation_id="gymkhana_book_event",
        request=s.EventBookingCreateSerializer,
        responses={201: s.VenueBookingSerializer},
    )
    def post(self, request):
        data = self.valid(s.EventBookingCreateSerializer)
        booking = book_event(actor_id=self.actor_id, **data)
        return self.one(
            booking, s.VenueBookingSerializer, http_status=status.HTTP_201_CREATED
        )


class BookingDetailView(GymkhanaView):
    read_codes = ("gymkhana.booking.view",)

    @extend_schema(operation_id="gymkhana_get_booking", responses={200: s.VenueBookingSerializer})
    def get(self, request, pk: int):
        return self.one(get_booking_by_id(pk), s.VenueBookingSerializer)


class BookingPosterView(GymkhanaView):
    read_codes = ("gymkhana.booking.view",)

    @extend_schema(operation_id="gymkhana_booking_poster", responses=FILE_RESPONSES)
    def get(self, request, pk: int):
        return file_response(get_booking_by_id(pk).poster_file, f"poster-{pk}")


# ==============================================================================
# Memberships
# ==============================================================================
class MembershipListView(GymkhanaView):
    read_codes = ("gymkhana.membership.view",)

    @extend_schema(
        operation_id="gymkhana_list_memberships",
        parameters=[int_query("club_id")],
        responses={200: s.MembershipSerializer(many=True)},
    )
    def get(self, request):
        queryset = scope_memberships(
            user_id=self.actor_id, roles=self.roles, club_id=int_param(request, "club_id")
        )
        return self.page(queryset, s.MembershipSerializer, ("student_id",))


class MembershipApplyView(GymkhanaView):
    write_codes = ("gymkhana.membership.create",)

    @extend_schema(
        operation_id="gymkhana_apply_membership",
        request=s.MembershipApplySerializer,
        responses={201: s.MembershipSerializer},
    )
    def post(self, request):
        data = self.valid(s.MembershipApplySerializer)
        membership = apply_membership(student_id=self.actor_id, **data)
        return self.one(
            membership, s.MembershipSerializer, ("student_id",), status.HTTP_201_CREATED
        )


class MembershipApproveView(GymkhanaView):
    write_codes = ("gymkhana.membership.approve",)

    @extend_schema(
        operation_id="gymkhana_approve_membership",
        request=s.MembershipApproveSerializer,
        responses={200: s.MembershipSerializer},
    )
    def post(self, request, pk: int):
        data = self.valid(s.MembershipApproveSerializer)
        membership = approve_membership(membership_id=pk, actor_id=self.actor_id, **data)
        return self.one(membership, s.MembershipSerializer, ("student_id",))


# ==============================================================================
# Voting Polls
# ==============================================================================
class PollView(GymkhanaView):
    def visible(self):
        batch, branch = student_group(self.actor_id)
        return polls_for(self.actor_id, batch, branch)


class PollListView(PollView):
    read_codes = ("gymkhana.poll.view",)
    write_codes = ("gymkhana.poll.create",)

    @extend_schema(
        operation_id="gymkhana_list_polls",
        parameters=[int_query("club_id")],
        responses={200: s.PollSerializer(many=True)},
    )
    def get(self, request):
        queryset, club_id = self.visible(), int_param(request, "club_id")
        if club_id is not None:
            queryset = queryset.filter(club_id=club_id)
        return self.page(queryset, s.PollSerializer)

    @extend_schema(
        operation_id="gymkhana_create_poll",
        request=s.PollCreateSerializer,
        responses={201: s.PollSerializer},
    )
    def post(self, request):
        data = self.valid(s.PollCreateSerializer)
        groups = [(g["batch"], g["branch"]) for g in data.pop("target_groups")]
        poll = create_poll(actor_id=self.actor_id, target_groups=groups, **data)
        return self.one(
            self.found(self.visible(), poll.pk),
            s.PollSerializer,
            http_status=status.HTTP_201_CREATED,
        )


class PollDetailView(PollView):
    read_codes = ("gymkhana.poll.view",)

    @extend_schema(operation_id="gymkhana_get_poll", responses={200: s.PollSerializer})
    def get(self, request, pk: int):
        return self.one(self.found(self.visible(), pk), s.PollSerializer)


class PollVoteView(PollView):
    write_codes = ("gymkhana.poll.vote",)

    @extend_schema(
        operation_id="gymkhana_cast_vote",
        request=s.VoteSerializer,
        responses={200: s.PollSerializer},
    )
    def post(self, request, pk: int):
        data = self.valid(s.VoteSerializer)
        batch, branch = student_group(self.actor_id)
        cast_vote(
            poll_id=pk,
            student_id=self.actor_id,
            choice_id=data["choice_id"],
            student_batch=batch,
            student_branch=branch,
        )
        return self.one(self.found(self.visible(), pk), s.PollSerializer)


# ==============================================================================
# Budget Requests
# ==============================================================================
class BudgetListView(GymkhanaView):
    read_codes = ("gymkhana.budget.view",)
    write_codes = ("gymkhana.budget.create",)

    @extend_schema(
        operation_id="gymkhana_list_budgets",
        parameters=[int_query("club_id")],
        responses={200: s.BudgetRequestSerializer(many=True)},
    )
    def get(self, request):
        queryset = scope_budget_requests(
            user_id=self.actor_id, roles=self.roles, club_id=int_param(request, "club_id")
        )
        return self.page(queryset, s.BudgetRequestSerializer)

    @extend_schema(
        operation_id="gymkhana_submit_budget",
        request={"multipart/form-data": s.BudgetRequestCreateSerializer},
        responses={201: s.BudgetRequestSerializer},
    )
    def post(self, request):
        data = self.valid(s.BudgetRequestCreateSerializer)
        budget = submit_budget_request(actor_id=self.actor_id, **data)
        return self.one(budget, s.BudgetRequestSerializer, http_status=status.HTTP_201_CREATED)


class BudgetDetailView(GymkhanaView):
    read_codes = ("gymkhana.budget.view",)

    @extend_schema(operation_id="gymkhana_get_budget", responses={200: s.BudgetRequestSerializer})
    def get(self, request, pk: int):
        budget = self.found(scope_budget_requests(self.actor_id, self.roles), pk)
        return self.one(budget, s.BudgetRequestSerializer)


class BudgetFileView(GymkhanaView):
    read_codes = ("gymkhana.budget.view",)

    @extend_schema(operation_id="gymkhana_budget_file", responses=FILE_RESPONSES)
    def get(self, request, pk: int):
        budget = self.found(scope_budget_requests(self.actor_id, self.roles), pk)
        return file_response(budget.supporting_file, f"budget-{pk}")


# ==============================================================================
# Event Reports
# ==============================================================================
class ReportListView(GymkhanaView):
    read_codes = ("gymkhana.report.view",)
    write_codes = ("gymkhana.report.create",)

    @extend_schema(
        operation_id="gymkhana_list_reports",
        parameters=[int_query("club_id")],
        responses={200: s.EventReportSerializer(many=True)},
    )
    def get(self, request):
        queryset = scope_event_reports(self.actor_id, int_param(request, "club_id"))
        return self.page(queryset, s.EventReportSerializer, ("student_incharge_id",))

    @extend_schema(
        operation_id="gymkhana_submit_report",
        request={"multipart/form-data": s.EventReportCreateSerializer},
        responses={201: s.EventReportSerializer},
    )
    def post(self, request):
        data = self.valid(s.EventReportCreateSerializer)
        report = submit_event_report(actor_id=self.actor_id, **data)
        return self.one(
            report, s.EventReportSerializer, ("student_incharge_id",), status.HTTP_201_CREATED
        )


class ReportDetailView(GymkhanaView):
    read_codes = ("gymkhana.report.view",)

    @extend_schema(operation_id="gymkhana_get_report", responses={200: s.EventReportSerializer})
    def get(self, request, pk: int):
        report = self.found(scope_event_reports(self.actor_id), pk)
        return self.one(report, s.EventReportSerializer, ("student_incharge_id",))


class ReportFileView(GymkhanaView):
    read_codes = ("gymkhana.report.view",)

    @extend_schema(operation_id="gymkhana_report_file", responses=FILE_RESPONSES)
    def get(self, request, pk: int):
        report = self.found(scope_event_reports(self.actor_id), pk)
        return file_response(report.report_file, f"report-{pk}")
