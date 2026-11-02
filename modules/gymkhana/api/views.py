from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.http import FileResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.gymkhana import services
from modules.gymkhana.api import serializers as s
from modules.gymkhana.models import (
    BudgetRequest,
    Club,
    ClubEvent,
    ClubEventReport,
    ClubSession,
    MembershipApplication,
    VotingPoll,
)

MODULE = HasModuleGrant("gymkhana")


def _actor(request):
    return request.principal


def _require(request, code: str) -> None:
    if not _actor(request).has_permission(code):
        raise PermissionDeniedError(
            "You do not have permission to perform this Gymkhana action.",
            code="permission_denied",
        )


def _require_kind(request, kind: str) -> None:
    if _actor(request).kind != kind:
        raise PermissionDeniedError(
            f"This action is available to {kind} accounts only.",
            code="wrong_actor_kind",
        )


def _club_head(request, club_id: int) -> Club:
    _require_kind(request, "student")
    club = services.confirmed_club(club_id)
    services.require_club_head(club, _actor(request).user_id)
    return club


def _read_file(field, filename: str):
    if not field or not field.storage.exists(field.name):
        raise NotFoundError("The requested file is unavailable.")
    response = FileResponse(field.open("rb"), as_attachment=True,
                            filename=filename or "download")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{quote(filename or 'download')}"
    )
    return response


class VenueListView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.module.view")]

    @extend_schema(responses=s.VenueListSerializer)
    def get(self, request):
        return Response({"results": list(settings.GYMKHANA_VENUES)})


class PeopleSearchView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.people.search")]
    throttle_scope = "directory_search"

    @extend_schema(responses=s.PeopleSearchSerializer)
    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        kind = request.query_params.get("kind", "")
        if kind not in ("student", "faculty"):
            return Response({"results": []})
        if len(query) < 2:
            return Response({"results": []})
        people = directory.search(q=query, kind=kind, limit=25)
        return Response({
            "results": [
                {
                    "user_id": person.user_id,
                    "display_name": person.display_name,
                    "username": person.username,
                    "kind": person.kind,
                    "batch_year": person.batch_year,
                    "discipline": person.discipline,
                }
                for person in people
            ],
        })


class ClubListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.module.view")]

    @extend_schema(responses=s.ClubListSerializer)
    def get(self, request):
        rows = Club.objects.all()
        if not _actor(request).has_permission("gymkhana.club.manage"):
            rows = rows.filter(status=Club.Status.CONFIRMED)
        return Response({"results": s.ClubSerializer(rows.order_by("name"), many=True).data})

    @extend_schema(request=s.ClubSerializer, responses={201: s.ClubSerializer})
    def post(self, request):
        _require(request, "gymkhana.club.manage")
        payload = s.ClubSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        club = services.create_club(data=payload.validated_data)
        return Response(s.ClubSerializer(club).data, status=status.HTTP_201_CREATED)


class ClubApprovalView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.club.manage")]

    @transaction.atomic
    @extend_schema(request=None, responses=s.ClubSerializer)
    def post(self, request, club_id):
        club = services.approve_club(club_id=club_id)
        return Response(s.ClubSerializer(club).data)


class LeadershipView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.club.leadership")]

    @extend_schema(request=s.LeadershipSerializer, responses=s.ClubSerializer)
    def post(self, request, club_id):
        club = _club_head(request, club_id)
        payload = s.LeadershipSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        updated = services.change_leadership(club=club, **payload.validated_data)
        return Response(s.ClubSerializer(updated).data)


class SessionListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.activity.manage")]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses=s.ActivityListSerializer)
    def get(self, request, club_id):
        club = services.confirmed_club(club_id)
        rows = ClubSession.objects.filter(club=club).order_by("date", "start_time")
        return Response({"results": s.ActivitySerializer(rows, many=True).data})

    @extend_schema(request=s.ActivitySerializer, responses={201: s.ActivitySerializer})
    def post(self, request, club_id):
        club = _club_head(request, club_id)
        payload = s.ActivitySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.book_session(
            club=club, user_id=_actor(request).user_id, data=payload.validated_data,
        )
        return Response(s.ActivitySerializer(row).data, status=status.HTTP_201_CREATED)


class EventListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.activity.manage")]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses=s.EventListSerializer)
    def get(self, request, club_id):
        club = services.confirmed_club(club_id)
        rows = ClubEvent.objects.filter(club=club).order_by("date", "start_time")
        return Response({"results": s.EventSerializer(rows, many=True).data})

    @extend_schema(request=s.EventSerializer, responses={201: s.EventSerializer})
    def post(self, request, club_id):
        club = _club_head(request, club_id)
        payload = s.EventSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.book_event(
            club=club, user_id=_actor(request).user_id, data=payload.validated_data,
        )
        return Response(s.EventSerializer(row).data, status=status.HTTP_201_CREATED)


class MembershipMineView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.membership.apply")]

    @extend_schema(responses=s.MembershipMineListSerializer)
    def get(self, request):
        _require_kind(request, "student")
        rows = MembershipApplication.objects.filter(
            student_user_id=_actor(request).user_id,
        ).select_related("club").order_by("-created_at")
        return Response({
            "results": [
                s.MembershipMineSerializer(row).data
                for row in rows
            ],
        })


class MembershipApplicationListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.membership.apply")]

    @extend_schema(responses=s.MembershipListSerializer)
    def get(self, request, club_id):
        club = _club_head(request, club_id)
        rows = MembershipApplication.objects.filter(
            club=club, status=MembershipApplication.Status.OPEN,
        ).order_by("created_at")
        return Response({"results": s.MembershipApplicationSerializer(rows, many=True).data})

    @extend_schema(
        request=s.MembershipApplicationSerializer,
        responses={201: s.MembershipApplicationSerializer},
    )
    def post(self, request, club_id):
        _require_kind(request, "student")
        club = Club.objects.filter(pk=club_id).first()
        if club is None:
            raise NotFoundError("No such club.")
        payload = s.MembershipApplicationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = services.apply_for_membership(
            club=club,
            student_user_id=_actor(request).user_id,
            description=payload.validated_data["description"],
        )
        return Response(
            s.MembershipApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class MembershipApprovalView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.membership.review")]

    @extend_schema(
        request=s.MembershipApprovalSerializer,
        responses=s.MembershipApplicationSerializer,
    )
    def post(self, request, club_id, application_id):
        club = _club_head(request, club_id)
        payload = s.MembershipApprovalSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = services.approve_membership(
            application_id=application_id,
            club=club,
            actor_user_id=_actor(request).user_id,
            **payload.validated_data,
        )
        return Response(s.MembershipApplicationSerializer(application).data)


class PollListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.poll.view")]

    @extend_schema(responses=s.PollListSerializer)
    def get(self, request):
        _require_kind(request, "student")
        polls = services.eligible_polls(_actor(request).user_id)
        return Response({
            "results": s.PollSerializer(
                polls, many=True, context={"user_id": _actor(request).user_id},
            ).data,
        })

    @extend_schema(
        request=s.PollCreateSerializer,
        responses={201: s.PollSerializer},
    )
    def post(self, request):
        _require(request, "gymkhana.poll.manage")
        payload = s.PollCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        club = _club_head(request, data.pop("club_id"))
        poll = services.create_poll(
            club=club, user_id=_actor(request).user_id, data=data,
        )
        return Response(
            s.PollSerializer(poll, context={"user_id": _actor(request).user_id}).data,
            status=status.HTTP_201_CREATED,
        )


class PollVoteView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.poll.vote")]

    @extend_schema(request=s.VoteSerializer, responses=s.VoteResultSerializer)
    def post(self, request, poll_id):
        _require_kind(request, "student")
        payload = s.VoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        vote = services.cast_vote(
            poll_id=poll_id,
            choice_id=payload.validated_data["choice_id"],
            student_user_id=_actor(request).user_id,
        )
        return Response({"poll_id": vote.poll_id, "choice_id": vote.choice_id})


class BudgetRequestListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.budget.manage")]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses=s.BudgetListSerializer)
    def get(self, request, club_id):
        club = _club_head(request, club_id)
        rows = BudgetRequest.objects.filter(club=club).order_by("-created_at")
        return Response({
            "results": s.BudgetRequestSerializer(rows, many=True).data,
        })

    @extend_schema(
        request=s.BudgetRequestSerializer,
        responses={201: s.BudgetRequestSerializer},
    )
    def post(self, request, club_id):
        club = _club_head(request, club_id)
        payload = s.BudgetRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = BudgetRequest.objects.create(
            club=club, created_by_user_id=_actor(request).user_id,
            **payload.validated_data,
        )
        return Response(
            s.BudgetRequestSerializer(row).data, status=status.HTTP_201_CREATED,
        )


class EventReportListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.report.submit")]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses=s.EventReportListSerializer)
    def get(self, request, club_id):
        club = _club_head(request, club_id)
        rows = ClubEventReport.objects.filter(club=club).order_by("-created_at")
        return Response({"results": s.EventReportSerializer(rows, many=True).data})

    @extend_schema(
        request=s.EventReportSerializer,
        responses={201: s.EventReportSerializer},
    )
    def post(self, request, club_id):
        club = _club_head(request, club_id)
        payload = s.EventReportSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.validate_people(
            (payload.validated_data["student_incharge_user_id"],), "student",
        )
        row = ClubEventReport.objects.create(
            club=club,
            created_by_user_id=_actor(request).user_id,
            **payload.validated_data,
        )
        return Response(
            s.EventReportSerializer(row).data, status=status.HTTP_201_CREATED,
        )


class AssignedReportsView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.report.view")]

    @extend_schema(responses=s.AssignedEventReportListSerializer)
    def get(self, request):
        _require_kind(request, "faculty")
        club_ids = services.faculty_report_club_ids(_actor(request).user_id)
        rows = ClubEventReport.objects.filter(club_id__in=club_ids).select_related(
            "club",
        ).order_by("-created_at")
        return Response({
            "results": [
                s.AssignedEventReportSerializer(row).data
                for row in rows
            ],
        })


class AttachmentView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.file.view")]

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, kind, object_id):
        if kind == "budget":
            row = BudgetRequest.objects.filter(pk=object_id).select_related("club").first()
            if row is None:
                raise NotFoundError("No such file.")
            services.require_club_head(row.club, _actor(request).user_id)
            return _read_file(row.supporting_file, row.supporting_file.name.rsplit("/", 1)[-1])
        if kind == "report":
            row = ClubEventReport.objects.filter(pk=object_id).select_related("club").first()
            if row is None:
                raise NotFoundError("No such file.")
            actor_id = _actor(request).user_id
            if (
                actor_id != row.club.faculty_councillor_user_id
                and actor_id not in (
                    row.club.coordinator_user_id, row.club.co_coordinator_user_id,
                )
            ):
                raise PermissionDeniedError("This report is not assigned to you.")
            return _read_file(row.report_file, row.report_file.name.rsplit("/", 1)[-1])
        if kind == "session":
            row = ClubSession.objects.filter(pk=object_id).select_related("club").first()
            if row is None:
                raise NotFoundError("No such file.")
            return _read_file(row.poster, row.poster.name.rsplit("/", 1)[-1])
        if kind == "event":
            row = ClubEvent.objects.filter(pk=object_id).select_related("club").first()
            if row is None:
                raise NotFoundError("No such file.")
            return _read_file(row.poster, row.poster.name.rsplit("/", 1)[-1])
        raise NotFoundError("No such file.")
