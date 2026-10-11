"""Printable / exportable representation of a leave
application (EL-UC-018): the application, its
resolved route, its decision trail and its
balance effect, as CSV."""
from __future__ import annotations

import csv
from io import StringIO

from drf_spectacular.utils import (
    OpenApiTypes,
    extend_schema,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.elm.api.views import (
    MODULE,
    P_RECORDS_VIEW,
    P_VIEW_SELF,
    _own_request,
)
from modules.elm.models import LeaveTransaction, RequestEvent


class ExportApplicationView(APIView):
    """The full application as CSV — printable from
    the browser, attachable to a file."""

    permission_classes = [
        MODULE,
        HasPermission(P_VIEW_SELF,
                      P_RECORDS_VIEW)]

    @extend_schema(responses={
        (200, "text/csv"): OpenApiTypes.STR,
    })
    def get(self, request, pk):
        application = _own_request(request, pk)

        out = StringIO()
        writer = csv.writer(out)

        writer.writerow(["Fusion ERP — Leave Application"])
        writer.writerow(["Application", application.id])
        writer.writerow([
            "Applicant (IAM user id)",
            application.user_id])
        writer.writerow([
            "Kind", application.get_kind_display()])
        writer.writerow([
            "Category", application.category])
        writer.writerow(["Status", application.status])
        writer.writerow([
            "Period", application.start_date,
            "→", application.end_date])
        writer.writerow([
            "Half days", application.start_half,
            application.end_half])
        writer.writerow([
            "Days", str(application.days)])
        writer.writerow([
            "Leave year", application.leave_year])
        writer.writerow(["Purpose", application.purpose])
        writer.writerow([
            "Station leave", application.station_leave,
            application.station_details])
        writer.writerow([
            "Resolved route",
            " > ".join(
                f"{step.get('role')}"
                f"({step.get('decision')})"
                for step in (application.route or []))])
        writer.writerow([
            "Substitute required",
            application.substitute_required])
        for nomination in (
                application.substitute_nominations.all()):
            writer.writerow([
                "Substitute", nomination.nominee_user_id,
                nomination.status,
                nomination.response_reason])
        if application.recommendation:
            writer.writerow([
                "Unit Head recommendation",
                application.recommendation,
                application.recommendation_reason])
        if application.decided_by_user_id:
            writer.writerow([
                "Decision",
                application.decided_by_user_id,
                application.decided_at,
                application.decision_reason])

        writer.writerow([])
        writer.writerow(["Audit trail"])
        writer.writerow(
            ["at", "event", "actor", "from", "to",
             "outcome", "reason"])
        for event in (
                RequestEvent.objects.filter(
                    request=application).order_by("id")):
            writer.writerow([
                event.at, event.event,
                event.actor_label or event.actor_user_id,
                event.from_status, event.to_status,
                event.outcome, event.reason])

        if application.leave_record:
            writer.writerow([])
            writer.writerow(
                ["Ledger movements for the posted leave"])
            writer.writerow(
                ["at", "kind", "delta", "balance after",
                 "reason"])
            for entry in (
                    LeaveTransaction.objects.filter(
                        request=application).order_by(
                            "id")):
                writer.writerow([
                    entry.created_at, entry.kind,
                    str(entry.delta),
                    str(entry.balance_after),
                    entry.reason])

        return Response(
            out.getvalue(),
            content_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="elm-'
                    f'{application.id}.csv"')},
        )
