from django.db.models import QuerySet
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana.api.serializers import (
    ApplySerializer, BulkReviewSerializer, ClubSerializer,
    MembershipApplicationSerializer, ReviewSerializer,
)
from modules.gymkhana.models import Club, ClubCoordinatorAssignment, MembershipApplication
from modules.gymkhana.services import membership

MODULE = HasModuleGrant("gymkhana")


def actor(request):
    return getattr(request, "principal", None)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        principal = actor(request)
        return (
            principal is not None
            and getattr(principal, "kind", None) == "student"
            and bool(getattr(principal, "user_id", None))
        )


class IsAssignedCoordinator(BasePermission):
    """For object actions, the service also checks assignment under a DB lock."""
    def has_permission(self, request, view):
        principal = actor(request)
        return (
            principal is not None
            and getattr(principal, "kind", None) != "recruiter"
            and bool(getattr(principal, "user_id", None))
        )


class ClubListView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.club.view")]

    def get(self, request):
        clubs = Club.objects.filter(is_active=True).order_by("name")
        return Response({"results": ClubSerializer(clubs, many=True).data})


class AssignedClubsView(APIView):
    permission_classes = [
        MODULE,
        HasPermission("gymkhana.application.review"),
        IsAssignedCoordinator,
    ]

    def get(self, request):
        principal = actor(request)
        club_ids = ClubCoordinatorAssignment.objects.filter(
            user_id=principal.user_id,
            is_active=True,
        ).values_list("club_id", flat=True)

        clubs = Club.objects.filter(
            id__in=club_ids,
            is_active=True,
        ).order_by("name")

        return Response({"results": ClubSerializer(clubs, many=True).data})


class MyApplicationsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            permission = HasPermission("gymkhana.application.create")
        else:
            permission = HasPermission("gymkhana.application.self")
        return [MODULE(), permission(), IsStudent()]

    def get(self, request):
        rows = membership.my_applications(actor=actor(request))
        return Response({
            "results": MembershipApplicationSerializer(rows, many=True).data
        })

    def post(self, request):
        payload = ApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = membership.apply(actor=actor(request), **payload.validated_data)
        return Response(
            MembershipApplicationSerializer(row).data,
            status=status.HTTP_201_CREATED,
        )


class ClubApplicationsView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.application.review"), IsAssignedCoordinator]

    def get(self, request, club_id):
        principal = actor(request)
        assigned = ClubCoordinatorAssignment.objects.filter(
            club_id=club_id, user_id=principal.user_id, is_active=True
        ).exists()
        if not assigned:
            raise PermissionDenied("You are not an active coordinator for this club.")

        rows = MembershipApplication.objects.filter(
            club_id=club_id
        ).select_related("club").order_by("-created_at")
        return Response({
            "results": MembershipApplicationSerializer(rows, many=True).data
        })


class ReviewApplicationView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.application.review"), IsAssignedCoordinator]

    def post(self, request, application_id):
        payload = ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = membership.review(
            actor=actor(request),
            application_id=application_id,
            **payload.validated_data,
        )
        return Response(MembershipApplicationSerializer(row).data)


class BulkReviewView(APIView):
    permission_classes = [MODULE, HasPermission("gymkhana.application.review"), IsAssignedCoordinator]

    def post(self, request):
        payload = BulkReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        results = membership.bulk_review(
            actor=actor(request),
            items=payload.validated_data["items"],
        )
        return Response({"results": results})
