"""HTTP layer: check permission, call services, return JSON."""
from rest_framework import generics, status
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.gymkhana import services
from modules.gymkhana.models import Club, Membership
from modules.gymkhana.serializers import ClubSerializer, MembershipSerializer

MODULE = HasModuleGrant("gymkhana")


class ClubListCreateView(generics.ListCreateAPIView):
    serializer_class = ClubSerializer

    def get_permissions(self):
        code = "gymkhana.club.create" if self.request.method == "POST" else "gymkhana.club.view"
        return [MODULE(), HasPermission(code)()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Club.objects.none()
        return services.visible_clubs(self.request.principal)

    def post(self, request):
        body = ClubSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        club = services.create_club(request.principal, body.validated_data)
        return Response(ClubSerializer(club).data, status=status.HTTP_201_CREATED)


class ClubApproveView(generics.GenericAPIView):
    permission_classes = [MODULE, HasPermission("gymkhana.club.approve")]
    serializer_class = ClubSerializer

    def post(self, request, pk):
        return Response(ClubSerializer(services.approve_club(pk)).data)


class MembershipListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("gymkhana.membership.create")()]
        return [MODULE(), HasPermission("gymkhana.membership.create",
                                        "gymkhana.membership.approve")()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Membership.objects.none()
        return services.visible_memberships(self.request.principal)

    def post(self, request):
        club_id = request.data.get("club")
        m = services.apply(request.principal, club_id, request.data.get("description", ""))
        return Response(MembershipSerializer(m).data, status=status.HTTP_201_CREATED)


class MembershipApproveView(generics.GenericAPIView):
    permission_classes = [MODULE, HasPermission("gymkhana.membership.approve")]
    serializer_class = MembershipSerializer

    def post(self, request, pk):
        m = services.approve_membership(request.principal, pk, request.data.get("remarks", ""))
        return Response(MembershipSerializer(m).data)
