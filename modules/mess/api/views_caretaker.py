#  --- views.py ---

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csrf
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.placement.api import serializers as s
from modules.placement.api.permissions import ScopedCollection
from modules.placement.authentication import (
    COOKIE_NAME as RECRUITER_COOKIE,
)
from modules.placement.authentication import (
    COOKIE_PATH as RECRUITER_COOKIE_PATH,
)
from modules.placement.authentication import (
    RecruiterAuthentication,
)
from modules.placement.models import (
    PlacementPolicy,
    RecruiterAccount,
)
from modules.placement.selectors import scoping
from modules.placement.services import announcements as announcement_service
from modules.placement.services import applications as application_service
from modules.placement.services import candidates
from modules.placement.services import companies as company_service
from modules.placement.services import interviews as interview_service
from modules.placement.services import offers as offer_service
from modules.placement.services import postings as posting_service
from modules.placement.services import recruiters as recruiter_service
from modules.placement.services import stats as stats_service

MODULE = HasModuleGrant("placement_cell")

P_VIEW_POSTINGS = "placement_cell.job_posting.view"
P_MANAGE_POSTINGS = "placement_cell.job_posting.manage"
P_VIEW_APPS = "placement_cell.application.view"
P_VIEW_SELF = "placement_cell.application.view_self"
P_MANAGE_COMPANIES = "placement_cell.company.manage"
P_VIEW_REPORTS = "placement_cell.report.view"


class OpenRegistrationWindow(APIView):
    @extend_schema(
        summary="Open the registration window",
        responses={
            200: s.RegistrationOpenResponse(),
        },
    )
    def get(self, request):
        try:
            # Call the service function here
            result = registration_service.open_registration_window()
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Similarly, create other endpoints for review registration, review deregistration, etc.
