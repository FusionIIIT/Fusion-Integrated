"""The CPI directory: every student's latest declared result (PC-BR-023).

The whole cohort, so the largest disclosure in the module — staff only, never
a recruiter. Read-only: policy rule 23 puts results with the Academic office.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.placement.api import serializers as s
from modules.placement.selectors import scoping

MODULE = HasModuleGrant("placement_cell")
P_VIEW_DIRECTORY = "placement_cell.academic_directory.view"

MAX_PAGE = 200


def _unavailable(exc):
    return Response(
        {"error": {"code": "identity_service_unavailable",
                   "message": f"Academic records are unavailable: {exc}",
                   "details": [], "request_id": ""}},
        status=status.HTTP_503_SERVICE_UNAVAILABLE)


@extend_schema(responses=s.AcademicDirectorySerializer)
class AcademicDirectoryView(APIView):
    """GET /api/v1/placement/students/cpi"""

    permission_classes = [MODULE, HasPermission(P_VIEW_DIRECTORY)]

    def get(self, request):
        # Explicit because a slip here exposes the whole cohort, not because the gate is unsure.
        if getattr(request.principal, "kind", None) == "recruiter" \
                or not scoping.is_staff(request.principal):
            return Response({"detail": "Not available."},
                            status=status.HTTP_403_FORBIDDEN)

        p = request.query_params
        try:
            limit = min(int(p.get("limit", 50)), MAX_PAGE)
            offset = max(int(p.get("offset", 0)), 0)
        except ValueError:
            return Response({"detail": "limit and offset must be integers."},
                            status=status.HTTP_400_BAD_REQUEST)

        filters = {"limit": limit, "offset": offset}
        for key in ("q", "discipline", "batch_year", "programme",
                    "only_declared"):
            value = p.get(key)
            if value:
                filters[key] = value

        try:
            return Response(get_client().academic_directory(**filters))
        except IamUnavailable as exc:
            return _unavailable(exc)


@extend_schema(responses=s.AcademicFiltersSerializer)
class AcademicFiltersView(APIView):
    """The values actually present, so the UI hard-codes nothing."""

    permission_classes = [MODULE, HasPermission(P_VIEW_DIRECTORY)]

    def get(self, request):
        if not scoping.is_staff(request.principal):
            return Response({"detail": "Not available."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            return Response(get_client().academic_filters())
        except IamUnavailable as exc:
            return _unavailable(exc)
