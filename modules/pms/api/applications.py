"""Application endpoints: list, draft, submit, inventors, revise, withdraw, appeal."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter
from rest_framework import status
from rest_framework.response import Response

from modules.pms.api import serializers as s
from modules.pms.api.common import Pagination, PmsView, WriteView, found, gate, names, schema
from modules.pms.selectors import applications as app_selector
from modules.pms.selectors import scoping
from modules.pms.services import appeals, inventors, revision, withdrawal
from modules.pms.services import applications as drafting

P_VIEW = "pms.application.view"

EXAMPLE_LIST_ROW = {"id": 7, "reference": "PMS-2026-00007", "title": "Graphene anode",
                    "status": "under_review", "domain_code": "materials",
                    "applicant_user_id": 1001, "applicant_name": "Applicant 1001",
                    "submitted_at": "2026-11-02T10:00:00+05:30",
                    "updated_at": "2026-11-03T09:00:00+05:30", "revision_due_on": None,
                    "appeal_due_on": None}
EXAMPLE_DETAIL = {**EXAMPLE_LIST_ROW, "abstract": "An anode...", "description": "...",
                  "claims": "1. An anode...", "preferred_attorney_user_id": None, "version": 1,
                  "decided_on": None, "grant_date": None, "grant_jurisdiction": "",
                  "patent_number": "", "inventors": [], "review_cycles": [], "appeals": [],
                  "attorney_assignments": [], "budgets": [], "filings": [],
                  "communications": [], "office_actions": [], "maintenance_cycles": [],
                  "assessments": [], "legal_requests": [], "legal_advice": [],
                  "revision_responses": [], "relations": ["applicant"], "feedback": {}}


def _people(app) -> set:
    ids = {app.applicant_user_id}
    ids |= {c.director_user_id for c in app.review_cycles.all()}
    ids |= {a.director_user_id for a in app.appeals.all()}
    ids |= {a.attorney_user_id for a in app.attorney_assignments.all()}
    ids |= {m.deciding_director_user_id for m in app.maintenance_cycles.all()}
    return ids


def detail_response(actor, pk: int, *, code: int = status.HTTP_200_OK) -> Response:
    app = found(app_selector.detail(actor, pk), "application")
    context = {"names": names(_people(app)), "relations": scoping.relations(actor, app),
               "feedback": app_selector.feedback_texts(app)}
    return Response(s.PmsApplicationDetailSerializer(app, context=context).data, status=code)


class ApplicationsView(WriteView):
    def get_permissions(self):
        code = P_VIEW if self.request.method == "GET" else "pms.application.create"
        return [p() for p in gate(code)]

    @schema("Applications within your scope", response=s.PmsApplicationListSerializer(many=True),
            example_out={"next": None, "previous": None, "results": [EXAMPLE_LIST_ROW]},
            parameters=[OpenApiParameter("status", str), OpenApiParameter("domain_code", str),
                        OpenApiParameter("q", str), OpenApiParameter("cursor", str),
                        OpenApiParameter("limit", int)])
    def get(self, request):
        f = s.PmsApplicationFilterIn(data=request.query_params.dict())
        f.is_valid(raise_exception=True)
        qs = app_selector.list_for(self.actor, status=f.validated_data.get("status"),
                                   domain_code=f.validated_data.get("domain_code"),
                                   q=f.validated_data.get("q"))
        pager = Pagination()
        page = pager.paginate_queryset(qs, request, view=self)
        ctx = {"names": names(a.applicant_user_id for a in page)}
        return pager.get_paginated_response(
            s.PmsApplicationListSerializer(page, many=True, context=ctx).data)


    @schema("Start a draft application (UC-PMS-001)", request=s.PmsApplicationIn,
            response=s.PmsApplicationDetailSerializer, status=201,
            example_in={"title": "Graphene anode", "domain_code": "materials"},
            example_out={**EXAMPLE_DETAIL, "status": "draft", "reference": ""})
    def post(self, request):
        body = s.PmsApplicationIn(data=request.data)
        body.is_valid(raise_exception=True)
        app = drafting.create_draft(actor=self.actor, fields=body.validated_data)
        return detail_response(self.actor, app.pk, code=status.HTTP_201_CREATED)


class ApplicationDetailView(WriteView):
    def get_permissions(self):
        code = P_VIEW if self.request.method == "GET" else "pms.application.update"
        return [p() for p in gate(code)]

    @schema("One application with its history of decisions (UC-PMS-002)",
            response=s.PmsApplicationDetailSerializer, example_out=EXAMPLE_DETAIL)
    def get(self, request, pk: int):
        return detail_response(self.actor, pk)

    @schema("Edit a draft or an application being revised", request=s.PmsApplicationIn,
            response=s.PmsApplicationDetailSerializer, example_in={"abstract": "Revised abstract"},
            example_out=EXAMPLE_DETAIL)
    def patch(self, request, pk: int):
        body = s.PmsApplicationIn(data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        drafting.update(actor=self.actor, pk=pk, fields=body.validated_data)
        return detail_response(self.actor, pk)


class SubmitView(WriteView):
    permission_classes = gate("pms.application.create")
    throttle_scope = "pms_submit"

    @schema("Submit a draft (BR-PMS-014..017)", request=None,
            response=s.PmsApplicationDetailSerializer,
            example_out={**EXAMPLE_DETAIL, "status": "submitted"})
    def post(self, request, pk: int):
        drafting.submit(actor=self.actor, pk=pk)
        return detail_response(self.actor, pk)


class HistoryView(PmsView):
    permission_classes = gate(P_VIEW)

    @schema("The application's audit trail (PMS-AFR-047)", response=s.PmsAuditSerializer(many=True),
            example_out=[{"id": 1, "at": "2026-11-02T10:00:00+05:30", "actor_user_id": 1001,
                          "actor_role": "student", "action": "application.submit",
                          "application_id": 7, "application_reference": "PMS-2026-00007",
                          "object_type": "Application", "object_id": 7,
                          "from_state": "draft", "to_state": "submitted", "details": {}}])
    def get(self, request, pk: int):
        app = found(scoping.applications_for(self.actor).filter(pk=pk).first(), "application")
        rows = app_selector.history(app).select_related("application")
        return Response(s.PmsAuditSerializer(rows, many=True).data)


class InventorsView(WriteView):
    permission_classes = gate("pms.inventor.update")

    @schema("Replace the inventors and their shares (UC-PMS-003)", request=s.PmsInventorsIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"inventors": [{"user_id": 1001, "share_percent": "60"},
                                      {"name": "R. Rao", "affiliation": "IISc",
                                       "share_percent": "40"}]},
            example_out=EXAMPLE_DETAIL)
    def put(self, request, pk: int):
        body = s.PmsInventorsIn(data=request.data)
        body.is_valid(raise_exception=True)
        inventors.replace_inventors(actor=self.actor, pk=pk,
                                    inventors=[dict(r) for r in body.validated_data["inventors"]])
        return detail_response(self.actor, pk)


class AgreementView(WriteView):
    permission_classes = gate("pms.inventor.update")

    @schema("Record an inventor's agreement and consent (BR-PMS-075, 078)",
            request=s.PmsAgreementIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"agreement_reference": "IPR/2026/14", "consent": True},
            example_out=EXAMPLE_DETAIL)
    def post(self, request, pk: int, inventor_id: int):
        body = s.PmsAgreementIn(data=request.data)
        body.is_valid(raise_exception=True)
        inventors.record_agreement(actor=self.actor, pk=pk, inventor_id=inventor_id,
                                   **body.validated_data)
        return detail_response(self.actor, pk)


class ResubmitView(WriteView):
    permission_classes = gate("pms.application.update")
    throttle_scope = "pms_submit"

    @schema("Resubmit a revised application (UC-PMS-005)", request=s.PmsResubmitIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"responses": {"review": "Claims 2 and 3 now state the coating "
                                                "thickness the Director asked about."}},
            example_out={**EXAMPLE_DETAIL, "status": "resubmitted"})
    def post(self, request, pk: int):
        body = s.PmsResubmitIn(data=request.data)
        body.is_valid(raise_exception=True)
        revision.resubmit(actor=self.actor, pk=pk, responses=body.validated_data["responses"])
        return detail_response(self.actor, pk)


class WithdrawView(WriteView):
    permission_classes = gate("pms.withdrawal.create")

    @schema("Withdraw before filing (UC-PMS-006)", request=s.PmsWithdrawIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"reason": "Publishing instead.", "consented_inventor_ids": [12]},
            example_out={**EXAMPLE_DETAIL, "status": "withdrawn"})
    def post(self, request, pk: int):
        body = s.PmsWithdrawIn(data=request.data)
        body.is_valid(raise_exception=True)
        withdrawal.withdraw(actor=self.actor, pk=pk, **body.validated_data)
        return detail_response(self.actor, pk)


class AppealView(WriteView):
    permission_classes = gate("pms.appeal.create")

    @schema("Appeal a rejection (UC-PMS-022)", request=s.PmsAppealIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"grounds": "The prior art cited is from a different field.",
                        "justification": "The examiner-style search missed claim 4."},
            example_out={**EXAMPLE_DETAIL, "status": "appeal_submitted"})
    def post(self, request, pk: int):
        body = s.PmsAppealIn(data=request.data)
        body.is_valid(raise_exception=True)
        appeals.file_appeal(actor=self.actor, pk=pk, **body.validated_data)
        return detail_response(self.actor, pk)
