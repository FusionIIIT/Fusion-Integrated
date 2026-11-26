from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.profiles_serializers import (
    DeptChangeDecisionSerializer,
    DeptDetailsWriteSerializer,
    DeptOfficialChangeSerializer,
    DeptProfileWriteSerializer,
    DeptRosterSerializer,
)
from modules.department.domain.profiles import visible_fields
from modules.department.domain.roles import role_kind
from modules.department.models import (
    CourseRoster,
    OfficialChangeProposal,
)
from modules.department.selectors import profiles as profile_selectors
from modules.department.services import department_details as details_service
from modules.department.services import profiles as profile_service
from modules.directory import contracts as directory


def _shape(actor, profile):
    """Shapes a profile based on actor's role and profile's kind."""
    viewer_kind = role_kind(actor.active_role)
    target_kind = profile.record_kind
    in_course = profile_selectors.is_in_course(actor.user_id, profile.user_id)
    fields_to_keep = visible_fields(viewer_kind, target_kind, in_course)

    if fields_to_keep is None:
        return None

    profile_data = {}
    profile_data['id'] = profile.id

    if target_kind == 'alumni':
        profile_data['display_name'] = profile.display_name
        profile_data['email'] = profile.email
    else:
        # Person facts from directory
        user_id = profile.user_id
        user_data = directory.get_users([user_id])
        if user_data and user_id in user_data:
            user = user_data[user_id]
            profile_data['name'] = user.display_name
            profile_data['programme'] = user.programme
            profile_data['department'] = user.department
            profile_data['email'] = user.email
            profile_data['username'] = user.username
            profile_data['discipline'] = user.discipline
            profile_data['batch_year'] = user.batch_year
        else:
            # Fallback if directory lookup fails, though spec implies it should succeed
            pass

    # Add other profile fields
    profile_data['title'] = getattr(profile, 'title', None)
    profile_data['office'] = getattr(profile, 'office', None)
    profile_data['bio'] = getattr(profile, 'bio', None)
    profile_data['graduation_year'] = getattr(profile, 'graduation_year', None)
    profile_data['is_active'] = getattr(profile, 'is_active', None)
    profile_data['record_kind'] = target_kind

    # Filter keys based on fields_to_keep
    final_profile = {}
    for key in fields_to_keep:
        if key in profile_data:
            final_profile[key] = profile_data[key]
        elif key == 'id':
            final_profile[key] = profile_data['id']

    return {"id": profile.id} | final_profile


class ProfileListView(APIView):
    """Lists visible department profiles."""
    serializer_class = DeptProfileWriteSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.profile.view"),
    ]

    @extend_schema(operation_id="department_profile_list", responses=DeptProfileWriteSerializer)
    def get(self, request):
        """Retrieves a list of visible profiles."""
        if getattr(self, "swagger_fake_view", False):
            return Response({"results": []})

        actor = request.principal
        visible_profiles = profile_selectors.visible_profiles(actor)
        shaped_profiles = [_shape(actor, p) for p in visible_profiles if _shape(actor, p) is not None]
        return Response({"results": shaped_profiles})

    def post(self, request):
        """Creates a new department profile."""
        serializer = DeptProfileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        department_id = data.pop('department')
        profile = profile_service.create_profile(
            actor=request.principal,
            department_id=department_id,
            data=data,
        )
        return Response(_shape(request.principal, profile), status=201)


class ProfileDetailView(APIView):
    """Retrieves details for a specific department profile."""
    serializer_class = DeptProfileWriteSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.profile.view"),
    ]

    @extend_schema(operation_id="department_profile_detail", responses=DeptProfileWriteSerializer)
    def get(self, request, pk):
        """Retrieves a specific profile, returning NotFoundError if not visible."""
        actor = request.principal
        profile = profile_selectors.visible_profiles(actor).filter(pk=pk).first()
        if not profile:
            raise NotFoundError("Profile not found or not visible to you.")

        shaped_profile = _shape(actor, profile)
        if shaped_profile is None:
            raise NotFoundError("Profile found but not visible to you.")

        return Response(shaped_profile)

    def patch(self, request, pk):
        """Updates a specific department profile."""
        actor = request.principal
        profile = profile_selectors.visible_profiles(actor).filter(pk=pk).first()
        if not profile:
            raise NotFoundError("Profile not found.")

        serializer = DeptProfileWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        updated_profile = profile_service.update_profile(
            actor=actor,
            profile=profile,
            data=data,
        )
        return Response(_shape(actor, updated_profile))


class ProfileDeactivateView(APIView):
    """Deactivates a specific department profile."""
    serializer_class = DeptProfileWriteSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.profile.update"),
    ]

    def post(self, request, pk):
        """Deactivates the profile."""
        actor = request.principal
        profile = profile_selectors.visible_profiles(actor).filter(pk=pk).first()
        if not profile:
            raise NotFoundError("Profile not found.")

        profile_service.deactivate_profile(actor=request.principal, profile_id=pk)
        return Response(status=204)


class RosterListView(ListCreateAPIView):
    """Lists and creates department rosters."""
    serializer_class = DeptRosterSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.roster.update"),
    ]

    queryset = CourseRoster.objects.none()

    def get_queryset(self) -> QuerySet[CourseRoster]:
        """Returns the queryset of visible rosters."""
        if getattr(self, "swagger_fake_view", False):
            return CourseRoster.objects.none()
        return profile_selectors.visible_rosters(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new department roster."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        department_id = data.pop('department')
        roster = profile_service.add_roster(
            actor=request.principal,
            department_id=department_id,
            data=data,
        )
        return Response(DeptRosterSerializer(roster).data, status=201)


class DepartmentDetailsView(APIView):
    """Updates department details."""
    serializer_class = DeptDetailsWriteSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.department.update"),
    ]

    def patch(self, request, pk):
        """Updates department details."""
        actor = request.principal
        department_id = pk

        serializer = DeptDetailsWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        department, proposal = details_service.update_details(
            actor=actor,
            department_id=department_id,
            data=data,
        )
        return Response({"pending_proposal": proposal.id if proposal else None})


class OfficialChangeListView(ListAPIView):
    """Lists visible official change proposals."""
    serializer_class = DeptOfficialChangeSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.official_change.view"),
    ]

    queryset = OfficialChangeProposal.objects.none()

    def get_queryset(self) -> QuerySet[OfficialChangeProposal]:
        """Returns the queryset of visible official change proposals."""
        if getattr(self, "swagger_fake_view", False):
            return OfficialChangeProposal.objects.none()
        return profile_selectors.visible_official_changes(self.request.principal)


class OfficialChangeDecideView(APIView):
    """Decides on an official change proposal."""
    serializer_class = DeptChangeDecisionSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.official_change.approve"),
    ]

    def post(self, request, pk):
        """Decides on the change proposal."""
        serializer = DeptChangeDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        outcome = details_service.decide_change(
            actor=request.principal,
            proposal_id=pk,
            outcome=data["outcome"],
        )
        return Response(DeptOfficialChangeSerializer(outcome).data)
