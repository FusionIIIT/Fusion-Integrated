# --- views.py ---
"""HTTP layer: parse, scope, delegate, serialise.

Every view takes its queryset from `selectors.scoping`, so authorisation is
never re-derived per endpoint. Anything out of scope is simply absent, which
is why detail views 404 rather than 403.
"""
from __future__ import annotations

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


class SubmitRegistration(APIView):
    authentication_classes = [RecruiterAuthentication]
    permission_classes = [ScopedCollection(MODULE, P_VIEW_POSTINGS)]

    @extend_schema(
        request=s.SubmitRegistrationSerializer,
        responses={
            200: s.SubmitRegistrationSerializer,
            400: s.ErrorSerializer,
        },
    )
    def post(self, request):
        try:
            user_id = request.user.id
            window_id = request.data.get('window_id')
            if not window_id:
                raise BadRequestError('Missing window_id')
            registration_service.submit_registration(user_id, window_id)
            return Response(status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(data={'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubmitDeregistration(APIView):
    authentication_classes = [RecruiterAuthentication]
    permission_classes = [ScopedCollection(MODULE, P_VIEW_POSTINGS)]

    @extend_schema(
        request=s.SubmitDeregistrationSerializer,
        responses={
            200: s.SubmitDeregistrationSerializer,
            400: s.ErrorSerializer,
        },
    )
    def post(self, request):
        try:
            user_id = request.user.id
            reason = request.data.get('reason')
            if not reason:
                raise BadRequestError('Missing reason')
            deregistration_service.submit_deregistration(user_id, reason)
            return Response(status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(data={'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ... similar views for SubmitRebate, SubmitSpecialFoodRequest, RespondToVacationSurvey, SubmitFeedback, etc. ...
