from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.api.serializers import (
    ClubSerializer,
    ClubCreateSerializer,
    ChangeLeadershipSerializer,
    ClubLeadershipSerializer,
    ClubMembershipSerializer,
    VenueBookingSerializer,
    VotingPollSerializer,
    CreatePollSerializer,
    CastVoteSerializer,
    PollVoteSerializer,
    ClubBudgetRequestSerializer,
    ClubEventReportSerializer,
)
from modules.gymkhana.models import (
    Club,
    ClubLeadership,
    ClubMembership,
    VenueBooking,
    VotingPoll,
    ClubBudgetRequest,
    ClubEventReport,
)
from modules.gymkhana.services import applications


def _get_user_id(request) -> int:
    return getattr(request.user, "user_id", getattr(request.user, "id", 1))


class ClubListCreateView(APIView):
    permission_classes = [HasModuleGrant("gymkhana")]

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.admin")]
        return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]

    def get(self, request):
        clubs = Club.objects.all().order_by("id")
        return Response(ClubSerializer(clubs, many=True).data)

    def post(self, request):
        serializer = ClubCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            club = applications.create_club(**serializer.validated_data)
            return Response(ClubSerializer(club).data, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ClubDetailView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]

    def get(self, request, pk: int):
        club = get_object_or_404(Club, pk=pk)
        return Response(ClubSerializer(club).data)


class ClubConfirmView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.admin")]

    def post(self, request, pk: int):
        try:
            club = applications.confirm_club(club_id=pk)
            return Response(ClubSerializer(club).data, status=status.HTTP_200_OK)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ClubLeadershipChangeView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.manage")]

    def post(self, request, pk: int):
        serializer = ChangeLeadershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _get_user_id(request)
        try:
            leadership = applications.change_club_leadership(
                club_id=pk,
                actor_id=actor_id,
                new_coordinator_id=serializer.validated_data["new_coordinator_id"],
                new_co_coordinator_id=serializer.validated_data["new_co_coordinator_id"],
            )
            return Response(ClubLeadershipSerializer(leadership).data, status=status.HTTP_200_OK)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class VenueBookingListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.booking.manage")]
        return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.view")]

    def get(self, request):
        bookings = VenueBooking.objects.all().order_by("-booking_date", "-start_time")
        return Response(VenueBookingSerializer(bookings, many=True).data)

    def post(self, request):
        serializer = VenueBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _get_user_id(request)
        try:
            booking = applications.book_venue(
                club_id=serializer.validated_data["club"].id,
                actor_id=actor_id,
                booking_type=serializer.validated_data["booking_type"],
                venue_name=serializer.validated_data["venue_name"],
                booking_date=serializer.validated_data["booking_date"],
                start_time=serializer.validated_data["start_time"],
                end_time=serializer.validated_data["end_time"],
                description=serializer.validated_data.get("description", ""),
                poster_url=serializer.validated_data.get("poster_url", ""),
            )
            return Response(VenueBookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class MembershipApplyView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.membership.apply")]

    def post(self, request, club_id: int):
        student_id = _get_user_id(request)
        try:
            membership = applications.apply_club_membership(
                club_id=club_id,
                student_id=student_id,
            )
            return Response(ClubMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class MembershipApproveView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.manage")]

    def post(self, request, pk: int):
        actor_id = _get_user_id(request)
        try:
            membership = applications.approve_club_membership(
                membership_id=pk,
                actor_id=actor_id,
            )
            return Response(ClubMembershipSerializer(membership).data, status=status.HTTP_200_OK)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (ClubMembership.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class VotingPollListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.club.manage")]
        return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.vote")]

    def get(self, request):
        polls = VotingPoll.objects.filter(is_active=True).order_by("-created_at")
        return Response(VotingPollSerializer(polls, many=True).data)

    def post(self, request):
        serializer = CreatePollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _get_user_id(request)
        try:
            poll = applications.create_voting_poll(
                club_id=serializer.validated_data["club_id"],
                actor_id=actor_id,
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
                options=serializer.validated_data["options"],
                target_batch=serializer.validated_data.get("target_batch", "ALL"),
                target_branch=serializer.validated_data.get("target_branch", "ALL"),
                expires_at=serializer.validated_data["expires_at"],
            )
            return Response(VotingPollSerializer(poll).data, status=status.HTTP_201_CREATED)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class CastVoteView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.poll.vote")]

    def post(self, request, poll_id: int):
        serializer = CastVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = _get_user_id(request)
        try:
            vote = applications.cast_poll_vote(
                poll_id=poll_id,
                student_id=student_id,
                option_id=serializer.validated_data["option_id"],
                student_batch=serializer.validated_data.get("student_batch", "ALL"),
                student_branch=serializer.validated_data.get("student_branch", "ALL"),
            )
            return Response(PollVoteSerializer(vote).data, status=status.HTTP_201_CREATED)
        except (VotingPoll.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class BudgetRequestListCreateView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.budget.submit")]

    def get(self, request):
        requests = ClubBudgetRequest.objects.all().order_by("-submitted_at")
        return Response(ClubBudgetRequestSerializer(requests, many=True).data)

    def post(self, request):
        serializer = ClubBudgetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _get_user_id(request)
        try:
            req = applications.submit_budget_request(
                club_id=serializer.validated_data["club"].id,
                actor_id=actor_id,
                requested_amount=serializer.validated_data["requested_amount"],
                description=serializer.validated_data["description"],
                supporting_file=serializer.validated_data["supporting_file"],
            )
            return Response(ClubBudgetRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class EventReportListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.submit")]
        return [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.review")]

    def get(self, request):
        reports = ClubEventReport.objects.all().order_by("-submitted_at")
        return Response(ClubEventReportSerializer(reports, many=True).data)

    def post(self, request):
        serializer = ClubEventReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_id = _get_user_id(request)
        try:
            report = applications.submit_event_report(
                club_id=serializer.validated_data["club"].id,
                actor_id=actor_id,
                event_name=serializer.validated_data["event_name"],
                event_date=serializer.validated_data["event_date"],
                report_file=serializer.validated_data["report_file"],
            )
            return Response(ClubEventReportSerializer(report).data, status=status.HTTP_201_CREATED)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (Club.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class FacultyReportReviewView(APIView):
    permission_classes = [HasModuleGrant("gymkhana"), HasPermission("gymkhana.report.review")]

    def get(self, request, pk: int):
        faculty_id = _get_user_id(request)
        try:
            report = applications.review_event_report(
                report_id=pk,
                faculty_id=faculty_id,
            )
            return Response(ClubEventReportSerializer(report).data, status=status.HTTP_200_OK)
        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (ClubEventReport.DoesNotExist, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
