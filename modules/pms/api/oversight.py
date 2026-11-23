"""Queues, deadlines, escalations, oversight, reports, audit, licensing and settings."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter
from rest_framework.response import Response

from core.api import csv as csv_export
from core.api.exceptions import BadRequestError, DomainError
from modules.pms.api import serializers as s
from modules.pms.api.common import (
    Pagination,
    PmsView,
    WriteView,
    found,
    gate,
    int_param,
    names,
    schema,
)
from modules.pms.domain import documents as d
from modules.pms.domain import policy as pol
from modules.pms.domain import reports as rp
from modules.pms.domain.roles import acting_role
from modules.pms.models import ReportDefinition
from modules.pms.selectors import deadlines as deadline_selector
from modules.pms.selectors import oversight, people, scoping
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import audit, escalations, licensing, reports
from modules.pms.services import policy as policy_service

LICENSING = {"id": 3, "application_id": 7, "application_reference": "PMS-2026-00007",
             "kind": "licensing", "summary": "Licence the coating to a battery maker.",
             "status": "routed", "route_kind": "committee", "routed_director_user_id": None,
             "committee_name": "Technology Transfer Committee",
             "routed_at": "2026-12-01T10:00:00+05:30", "notes": [], "agreement": None,
             "created_at": "2026-12-01T10:00:00+05:30"}
ESCALATION = {"id": 2, "kind": "missed_review", "application_id": 7,
              "application_reference": "PMS-2026-00007", "subject_id": 11,
              "deadline": "2026-11-23", "status": "open", "note": "", "handled_at": None,
              "created_at": "2026-11-24T00:05:00+05:30"}


class MyWorkView(PmsView):
    permission_classes = gate("pms.application.view")

    @schema("What is waiting on you", response=s.PmsWorkItemSerializer(many=True),
            example_out=[{"kind": "review", "id": 11, "application_id": 7,
                          "reference": "PMS-2026-00007", "title": "Graphene anode",
                          "status": "open"}])
    def get(self, request):
        return Response(s.PmsWorkItemSerializer(oversight.my_work(self.actor), many=True).data)


class DeadlinesView(PmsView):
    permission_classes = gate("pms.escalation.review")

    @schema("Every tracked deadline, soonest first (UC-PMS-016)",
            response=s.PmsDeadlineSerializer(many=True),
            example_out=[{"kind": "review", "subject_id": 11, "application_id": 7,
                          "reference": "PMS-2026-00007", "due_on": "2026-11-23",
                          "responsible": "Director 2001", "missed": False}])
    def get(self, request):
        rows = deadline_selector.tracked(scoping.applications_for(self.actor))
        ctx = {"names": names(r.responsible_user_id for r in rows),
               "today": timezone.localdate()}
        return Response(s.PmsDeadlineSerializer(rows, many=True, context=ctx).data)


class EscalationsView(PmsView):
    permission_classes = gate("pms.escalation.review")

    @schema("Escalations and exceptional cases (UC-PMS-027)",
            response=s.PmsEscalationSerializer(many=True), example_out=[ESCALATION],
            parameters=[OpenApiParameter("status", str)])
    def get(self, request):
        qs = scoping.escalations_for(self.actor).order_by("-id")
        wanted = request.query_params.get("status")
        if wanted:
            if wanted not in ("open", "routed", "resolved"):
                raise BadRequestError("status is open, routed or resolved.",
                                      code="invalid_filter")
            qs = qs.filter(status=wanted)
        return Response(s.PmsEscalationSerializer(qs[:500], many=True).data)


class EscalationHandleView(WriteView):
    permission_classes = gate("pms.escalation.review")

    @schema("Route or resolve an escalation", request=s.PmsHandleIn,
            response=s.PmsEscalationSerializer,
            example_in={"action": "resolve", "note": "Reassigned to Director 2002."},
            example_out={**ESCALATION, "status": "resolved"})
    def post(self, request, pk: int):
        body = s.PmsHandleIn(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(s.PmsEscalationSerializer(escalations.handle(
            actor=self.actor, escalation_id=pk, **body.validated_data)).data)


class OversightView(PmsView):
    permission_classes = gate("pms.workflow.view")

    @schema("Workflow oversight within your scope (UC-PMS-032)", response=dict,
            example_out={"by_status": {"submitted": 2, "under_review": 3}, "total": 5,
                         "overdue_reviews": 1, "open_escalations": 1})
    def get(self, request):
        return Response(oversight.workflow_summary(self.actor))


def _report_args(request) -> tuple[dict, list | None]:
    params = request.query_params
    filters = {k: params[k] for k in ("status", "domain_code", "date_from", "date_to")
               if params.get(k)}
    unknown = set(params) - {"status", "domain_code", "date_from", "date_to", "columns"}
    if unknown:
        raise BadRequestError("Unknown report parameter: " + ", ".join(sorted(unknown)) + ".",
                              code="invalid_filter")
    columns = [c for c in params.get("columns", "").split(",") if c] or None
    return filters, columns


class ReportView(PmsView):
    permission_classes = gate("pms.report.view")

    @schema("A report within your scope; viewing it is logged (PMS-AFR-191)", response=dict,
            example_out={"columns": ["reference", "status"],
                         "rows": [{"reference": "PMS-2026-00007", "status": "filed"}]})
    def get(self, request, report_type: str):
        filters, columns = _report_args(request)
        cols, rows = reports.generate(actor=self.actor, report_type=report_type,
                                      filters=filters, columns=columns)
        return Response({"columns": list(cols), "rows": rows})


def _csv(cols, rows, filename):
    return csv_export.stream(filename=filename, header=list(cols),
                             rows=([row[c] for c in cols] for row in rows))


class ReportExportView(PmsView):
    permission_classes = gate("pms.report.export")
    throttle_scope = "pms_export"

    @schema("The same report as CSV (PMS-AFR-189)", response=bytes)
    def get(self, request, report_type: str):
        filters, columns = _report_args(request)
        cols, rows = reports.generate(actor=self.actor, report_type=report_type,
                                      filters=filters, columns=columns, export=True)
        return _csv(cols, rows, f"pms-{report_type}.csv")


class ReportDefinitionsView(WriteView):
    permission_classes = gate("pms.report_definition.create")

    @schema("Your saved and scheduled reports (PMS-AFR-188, 190)",
            response=s.PmsReportDefinitionSerializer(many=True),
            example_out=[{"id": 1, "name": "Weekly status", "report_type": "status",
                          "filters": {}, "columns": ["reference", "status"],
                          "schedule": "weekly", "active": True,
                          "created_at": "2026-11-01T10:00:00+05:30", "runs": []}])
    def get(self, request):
        rows = (ReportDefinition.objects.filter(owner_user_id=self.actor.user_id)
                .prefetch_related("runs").order_by("-id"))
        return Response(s.PmsReportDefinitionSerializer(rows, many=True).data)

    @schema("Save a report definition", request=s.PmsReportDefinitionIn,
            response=s.PmsReportDefinitionSerializer, status=201,
            example_in={"name": "Weekly status", "report_type": "status",
                        "columns": ["reference", "status"], "schedule": "weekly"},
            example_out={"id": 1, "name": "Weekly status", "report_type": "status",
                         "filters": {}, "columns": ["reference", "status"],
                         "schedule": "weekly", "active": True,
                         "created_at": "2026-11-01T10:00:00+05:30", "runs": []})
    def post(self, request):
        body = s.PmsReportDefinitionIn(data=request.data)
        body.is_valid(raise_exception=True)
        row = reports.save_definition(actor=self.actor, **body.validated_data)
        return Response(s.PmsReportDefinitionSerializer(row).data, status=201)


class ReportDeactivateView(WriteView):
    permission_classes = gate("pms.report_definition.create")

    @schema("Switch a saved report off", request=None, response=s.PmsReportDefinitionSerializer,
            example_out={"id": 1, "name": "Weekly status", "report_type": "status",
                         "filters": {}, "columns": [], "schedule": "weekly", "active": False,
                         "created_at": "2026-11-01T10:00:00+05:30", "runs": []})
    def post(self, request, pk: int):
        return Response(s.PmsReportDefinitionSerializer(
            reports.deactivate(actor=self.actor, definition_id=pk)).data)


class ReportRunDownloadView(PmsView):
    permission_classes = gate("pms.report.view")
    throttle_scope = "pms_export"

    @schema("A scheduled run, rebuilt from your live scope (blueprint S-1)", response=bytes)
    def get(self, request, pk: int):
        run, (cols, rows) = reports.run_download(actor=self.actor, run_id=pk)
        return _csv(cols, rows, f"pms-{run.definition.report_type}-{run.period}.csv")


class AuditView(PmsView):
    permission_classes = gate("pms.audit_log.view")

    @schema("Audit entries within your scope (UC-PMS-028)",
            response=s.PmsAuditSerializer(many=True),
            parameters=[OpenApiParameter("application", int), OpenApiParameter("actor", int),
                        OpenApiParameter("action", str), OpenApiParameter("cursor", str)],
            example_out={"next": None, "previous": None, "results": []})
    def get(self, request):
        qs = _audit_rows(self.actor, request)
        pager = Pagination()
        page = pager.paginate_queryset(qs, request, view=self)
        audit.record(self.actor, "audit.viewed", details={"rows": len(page)})
        return pager.get_paginated_response(s.PmsAuditSerializer(page, many=True).data)


def _audit_rows(actor, request):
    qs = scoping.audit_for(actor)
    params = request.query_params
    unknown = set(params) - {"application", "actor", "action", "cursor", "limit"}
    if unknown:
        raise BadRequestError("Unknown audit filter: " + ", ".join(sorted(unknown)) + ".",
                              code="invalid_filter")
    if (app := int_param(params, "application")) is not None:
        qs = qs.filter(application_id=app)
    if (who := int_param(params, "actor")) is not None:
        qs = qs.filter(actor_user_id=who)
    if params.get("action"):
        qs = qs.filter(action__startswith=params["action"][:64])
    return qs.order_by("-id")


class AuditExportView(PmsView):
    permission_classes = gate("pms.audit_log.export")
    throttle_scope = "pms_export"

    @schema("Audit entries as CSV for compliance review (PMS-AFR-213)", response=bytes)
    def get(self, request):
        rows = list(_audit_rows(self.actor, request)[:10_000])
        audit.record(self.actor, "audit.exported", details={"rows": len(rows)})
        cols = ("id", "at", "actor_user_id", "actor_role", "action", "application_id",
                "from_state", "to_state")
        return csv_export.stream(filename="pms-audit.csv", header=list(cols),
                                 rows=([getattr(r, c) for c in cols] for r in rows))


class LicensingListView(WriteView):
    def get_permissions(self):
        code = ("pms.licensing_request.view" if self.request.method == "GET"
                else "pms.licensing_request.create")
        return [p() for p in gate(code)]

    @schema("Licensing requests within your scope (BR-PMS-091)",
            response=s.PmsLicensingSerializer(many=True), example_out=[LICENSING])
    def get(self, request):
        rows = (scoping.licensing_for(self.actor).prefetch_related("notes")
                .select_related("agreement").order_by("-id"))
        return Response(s.PmsLicensingSerializer(rows, many=True).data)

    @schema("Submit a licensing or technology-transfer request (UC-PMS-020)",
            request=s.PmsLicensingIn, response=s.PmsLicensingSerializer, status=201,
            example_in={"application_id": 7, "kind": "licensing",
                        "summary": "Licence the coating to a battery maker."},
            example_out=LICENSING)
    def post(self, request):
        body = s.PmsLicensingIn(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        row = licensing.submit(actor=self.actor, pk=data["application_id"], kind=data["kind"],
                               summary=data["summary"])
        return Response(s.PmsLicensingSerializer(row).data, status=201)


def _licensing(actor, pk):
    row = found(scoping.licensing_for(actor).prefetch_related("notes").filter(pk=pk).first(),
                "licensing request")
    return Response(s.PmsLicensingSerializer(row).data)


class LicensingRouteView(WriteView):
    permission_classes = gate("pms.licensing_request.review")

    @schema("Route a request once a route is configured (BR-PMS-088)", request=None,
            response=s.PmsLicensingSerializer, example_out=LICENSING)
    def post(self, request, pk: int):
        licensing.route(actor=self.actor, request_id=pk)
        return _licensing(self.actor, pk)


class LicensingNoteView(WriteView):
    permission_classes = gate("pms.licensing_request.review")

    @schema("Record negotiation progress (PMS-AFR-161)", request=s.PmsNoteIn,
            response=s.PmsLicensingSerializer, example_in={"note": "Term sheet received."},
            example_out={**LICENSING, "status": "negotiating"})
    def post(self, request, pk: int):
        body = s.PmsNoteIn(data=request.data)
        body.is_valid(raise_exception=True)
        licensing.add_note(actor=self.actor, request_id=pk, **body.validated_data)
        return _licensing(self.actor, pk)


class LicensingAgreementView(WriteView):
    permission_classes = gate("pms.licensing_request.review")

    @schema("Record the final agreement (PMS-AFR-162)", request=s.PmsLicenseAgreementIn,
            response=s.PmsLicensingSerializer,
            example_in={"counterparty": "Acme Cells", "signed_on": "2027-01-10",
                        "terms_summary": "Non-exclusive, India, 5 years."},
            example_out={**LICENSING, "status": "agreement_recorded"})
    def post(self, request, pk: int):
        body = s.PmsLicenseAgreementIn(data=request.data)
        body.is_valid(raise_exception=True)
        licensing.record_agreement(actor=self.actor, request_id=pk, **body.validated_data)
        return _licensing(self.actor, pk)


class ReferenceDataView(PmsView):
    permission_classes = gate("pms.application.view")

    @schema("Areas, sensitivity levels and report types for forms", response=dict,
            example_out={"domains": [{"code": "materials", "label": "Materials",
                                      "ipc_classes": ["H01M"]}],
                         "sensitivities": ["public_internal", "confidential", "restricted"],
                         "document_kinds": ["specification"], "alert_offsets_days": [30, 15, 5],
                         "withdrawal_statuses": [], "report_types": ["status"],
                         "appeal_period_days": 30})
    def get(self, request):
        spec = policy_selector.current()
        return Response({
            "domains": pol.to_payload(spec)["domains"],
            "sensitivities": list(d.SENSITIVITIES), "document_kinds": list(d.KINDS),
            "alert_offsets_days": list(spec.alert_offsets_days),
            "withdrawal_statuses": sorted(spec.withdrawal_statuses),
            "withdrawal_consent_required": spec.withdrawal_consent_required,
            "report_types": list(rp.TYPES), "appeal_period_days": spec.appeal_period_days})


class PolicyView(WriteView):
    permission_classes = gate("pms.policy.publish")

    @schema("The settings in effect and every earlier version (UC-PMS-025)", response=dict,
            example_out={"version": 0, "payload": {"appeal_period_days": 30},
                         "history": []})
    def get(self, request):
        spec = policy_selector.current()
        return Response({"version": spec.version, "payload": pol.to_payload(spec),
                         "history": s.PmsPolicySerializer(policy_selector.history()[:50],
                                                       many=True).data})

    @schema("Publish a new settings version (409 if someone published first)",
            request=s.PmsPolicyIn, response=dict, status=201,
            example_in={"based_on_version": 0,
                        "payload": {"cost_threshold": "100000.00",
                                    "domains": [{"code": "materials", "label": "Materials"}]}},
            example_out={"version": 1, "payload": {"cost_threshold": "100000.00"},
                         "history": []})
    def post(self, request):
        body = s.PmsPolicyIn(data=request.data)
        body.is_valid(raise_exception=True)
        row = policy_service.publish(actor=self.actor, **body.validated_data)
        return Response({"version": row.version, "payload": row.payload,
                         "history": s.PmsPolicySerializer(policy_selector.history()[:50],
                                                       many=True).data}, status=201)


class SetupView(PmsView):
    permission_classes = gate("pms.policy.publish")

    @schema("What PCC_ADMIN still has to configure (Step 2.8)", response=dict,
            example_out={"gaps": ["No technical areas are configured..."]})
    def get(self, request):
        return Response({"gaps": policy_service.setup_gaps()})


class PeopleView(PmsView):
    permission_classes = gate("pms.inventor.update", "pms.director_profile.update",
                              "pms.attorney_panel.update", "pms.policy.publish")
    throttle_scope = "pms_search"

    @schema("Find a person by name for a picker (ids, names and kinds only)", response=dict,
            parameters=[OpenApiParameter("q", str), OpenApiParameter("kind", str)],
            example_out={"results": [{"user_id": 1001, "display_name": "Person 1001",
                                      "kind": "student"}]})
    def get(self, request):
        kind = request.query_params.get("kind") or None
        if kind not in (None, "student", "faculty", "staff"):
            raise BadRequestError("kind is student, faculty or staff.", code="invalid_filter")
        found_people = people.search(request.query_params.get("q", ""), kind=kind)
        if found_people is None:
            raise DomainError("The directory is not reachable right now; try again shortly.",
                              code="directory_unavailable")
        return Response({"results": [p.__dict__ for p in found_people]})


class ActingView(PmsView):
    permission_classes = gate("pms.application.view")

    @schema("The PMS permissions of the role you are acting as", response=dict,
            example_out={"role": "pms_director", "permissions": ["pms.review.approve"]})
    def get(self, request):
        actor = self.actor
        return Response({"role": acting_role(actor.active_role, actor.kind),
                         "permissions": sorted(p for p in actor.permissions
                                               if p.startswith("pms."))})
