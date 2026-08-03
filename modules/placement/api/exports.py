"""CSV exports for the placement office.

The largest deliberate egress in the module: one request leaves with the whole
cohort's applications, names and CPIs attached. So the gate matches the CPI
directory's — staff only, never a recruiter — the `export` throttle applies,
and every download is logged with who took it and how many rows.

Cell escaping lives in core.api.csv, so an export added later cannot forget it.
"""
from __future__ import annotations

import logging

from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csv as safe_csv
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.placement.selectors import scoping

log = logging.getLogger("fusion.placement.export")

MODULE = HasModuleGrant("placement_cell")
P_VIEW_REPORTS = "placement_cell.report.view"

#: Beyond this an export is almost certainly a scrape rather than a report.
MAX_ROWS = 20_000


def _actor(request):
    return getattr(request, "principal", None)


class _StaffExport(APIView):
    """Shared gate. Subclasses provide `filename`, `header` and `build`."""

    permission_classes = [MODULE, HasPermission(P_VIEW_REPORTS)]
    throttle_scope = "export"

    filename = "export"
    header: list[str] = []

    def build(self, actor) -> list[list[object]]:
        raise NotImplementedError

    @extend_schema(responses={
        (200, "text/csv"): OpenApiTypes.STR,
        403: OpenApiResponse(description="Staff only; never a recruiter."),
    })
    def get(self, request):
        actor = _actor(request)
        # Explicit because this is bulk personal data, not because the gate is unsure.
        if getattr(actor, "kind", None) == "recruiter" or not scoping.is_staff(actor):
            return Response({"detail": "Not available."},
                            status=status.HTTP_403_FORBIDDEN)

        rows = self.build(actor)
        stamp = timezone.now().strftime("%Y%m%d-%H%M")
        log.info("placement.export user=%s file=%s rows=%d",
                 getattr(actor, "user_id", None), self.filename, len(rows))
        return safe_csv.stream(
            filename=f"{self.filename}-{stamp}.csv",
            header=self.header, rows=rows)


class ApplicationExportView(_StaffExport):
    """Every application in the caller's scope, one row each."""

    filename = "applications"
    header = ["Roll no", "Name", "Discipline", "Programme", "Company", "Role",
              "Season", "Status", "CPI at apply", "Semester at apply",
              "Applied at"]

    def build(self, actor):
        applications = list(
            scoping.applications_for(actor)
            .select_related("posting", "posting__company")
            .order_by("posting__company__name", "posting__title")[:MAX_ROWS])
        # One batched directory call for the whole file, not one per row.
        people = directory.get_users([a.user_id for a in applications])

        rows = []
        for a in applications:
            person = people.get(a.user_id)
            rows.append([
                getattr(person, "username", ""),
                getattr(person, "display_name", ""),
                getattr(person, "discipline", ""),
                getattr(person, "programme", ""),
                a.posting.company.name,
                a.posting.title,
                a.posting.placement_year,
                a.get_status_display(),
                a.cpi_at_apply,
                a.semester_at_apply,
                a.applied_at.isoformat() if a.applied_at else "",
            ])
        return rows


class PlacementRecordExportView(_StaffExport):
    """Who was placed where — the season's outcome, for the annual report."""

    filename = "placements"
    header = ["Roll no", "Name", "Discipline", "Programme", "Company", "Role",
              "Kind", "CTC (LPA)", "Season", "Recorded at"]

    def build(self, actor):
        records = list(
            scoping.placement_records_for(actor)
            .filter(is_active=True)
            .select_related("company", "posting", "policy")
            .order_by("-ctc_lpa")[:MAX_ROWS])
        people = directory.get_users([r.user_id for r in records])

        rows = []
        for r in records:
            person = people.get(r.user_id)
            rows.append([
                getattr(person, "username", ""),
                getattr(person, "display_name", ""),
                getattr(person, "discipline", ""),
                getattr(person, "programme", ""),
                r.company.name,
                r.posting.title if r.posting else "",
                r.kind,
                r.ctc_lpa,
                r.policy.season if r.policy else "",
                r.created_at.isoformat(),
            ])
        return rows
