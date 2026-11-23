"""Director and attorney assignment, review decisions, appeals, and the rosters behind them."""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response

from modules.pms.api import serializers as s
from modules.pms.api.applications import EXAMPLE_DETAIL, detail_response
from modules.pms.api.common import PmsView, WriteView, found, gate, names, schema
from modules.pms.domain import assignment
from modules.pms.selectors import candidates, scoping
from modules.pms.services import appeals, attorneys, review, rosters
from modules.pms.services.base import inventor_ids

P_ASSIGN = "pms.review.assign"
P_ATTORNEY = "pms.attorney.assign"
CANDIDATE = {"user_id": 2001, "name": "Director 2001", "domain_codes": ["materials"],
             "workload": 1}
ROSTER_ROW = {"id": 3, "user_id": 2001, "name": "Director 2001", "domain_codes": ["materials"],
              "valid_from": "2026-11-01T09:00:00+05:30", "valid_to": None, "workload": 1}
APPEAL = {"id": 4, "application_id": 7, "director_user_id": 2002, "director_name": "D 2002",
          "grounds": "...", "justification": "...", "status": "decided", "outcome": "remand",
          "modified_decision": "", "outcome_note": "Remanded so claim 4 can be narrowed to...",
          "created_at": "2026-11-05T09:00:00+05:30", "decided_at": "2026-11-09T09:00:00+05:30"}
ASSIGNMENT = {"id": 9, "application_id": 7, "application_reference": "PMS-2026-00007",
              "application_title": "Graphene anode", "attorney_user_id": 3001,
              "attorney_name": "Attorney 3001", "is_exception": False, "exception_reason": "",
              "status": "accepted", "responded_at": "2026-11-10T09:00:00+05:30",
              "decline_reason": "", "created_at": "2026-11-09T09:00:00+05:30"}


def _app(actor, pk):
    return found(scoping.applications_for(actor).filter(pk=pk).first(), "application")


class DirectorCandidatesView(PmsView):
    permission_classes = gate(P_ASSIGN)

    @schema("Eligible Directors, least loaded first (BR-PMS-023..026)",
            response=s.PmsCandidateSerializer(many=True), example_out=[CANDIDATE])
    def get(self, request, pk: int):
        app = _app(self.actor, pk)
        pool = assignment.eligible_directors(candidates.director_candidates(), app.domain_code,
                                             app.applicant_user_id, inventor_ids(app))
        ctx = {"names": names(c.user_id for c in pool)}
        return Response(s.PmsCandidateSerializer(pool, many=True, context=ctx).data)


class AssignDirectorView(WriteView):
    permission_classes = gate(P_ASSIGN)

    @schema("Assign or reassign the reviewing Director (UC-PMS-007)", request=s.PmsPersonIn,
            response=s.PmsApplicationDetailSerializer, example_in={"director_user_id": 2001},
            example_out={**EXAMPLE_DETAIL, "status": "under_review"})
    def post(self, request, pk: int):
        body = s.PmsPersonIn(data=request.data)
        body.is_valid(raise_exception=True)
        review.assign_director(actor=self.actor, pk=pk, **body.validated_data)
        return detail_response(self.actor, pk)


class ReviewDecisionView(WriteView):
    permission_classes = gate("pms.review.approve")

    @schema("Record the review decision (UC-PMS-008; BR-PMS-029..031)", request=s.PmsDecisionIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"decision": "approve",
                        "justification": "Novel coating method; claims are clear and enabled."},
            example_out={**EXAMPLE_DETAIL, "status": "approved"})
    def post(self, request, pk: int):
        body = s.PmsDecisionIn(data=request.data)
        body.is_valid(raise_exception=True)
        review.decide(actor=self.actor, pk=pk, **body.validated_data)
        return detail_response(self.actor, pk)


class AppealAssignView(WriteView):
    permission_classes = gate(P_ASSIGN)

    @schema("Assign the Director who hears an appeal (blueprint Q-1)", request=s.PmsPersonIn,
            response=s.PmsAppealSerializer, example_in={"director_user_id": 2002},
            example_out={**APPEAL, "status": "open", "outcome": "", "decided_at": None})
    def post(self, request, pk: int):
        body = s.PmsPersonIn(data=request.data)
        body.is_valid(raise_exception=True)
        appeal = appeals.assign_appeal(actor=self.actor, appeal_id=pk, **body.validated_data)
        return Response(s.PmsAppealSerializer(
            appeal, context={"names": names([appeal.director_user_id])}).data)


class AppealDecisionView(WriteView):
    permission_classes = gate("pms.appeal.review")

    @schema("Decide an appeal (UC-PMS-023; BR-PMS-095)", request=s.PmsAppealDecisionIn,
            response=s.PmsAppealSerializer,
            example_in={"outcome": "remand", "note": "Remanded so claim 4 can be narrowed to "
                                                     "the tested temperature range."},
            example_out=APPEAL)
    def post(self, request, pk: int):
        body = s.PmsAppealDecisionIn(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        appeal = appeals.decide_appeal(actor=self.actor, appeal_id=pk, outcome=data["outcome"],
                                       modified_decision=data.get("modified_decision"),
                                       note=data["note"])
        return Response(s.PmsAppealSerializer(
            appeal, context={"names": names([appeal.director_user_id])}).data)


class AttorneyCandidatesView(PmsView):
    permission_classes = gate(P_ATTORNEY)

    @schema("Panel attorneys for this application, preference first (BR-PMS-041..045)",
            response=s.PmsCandidateSerializer(many=True),
            example_out=[{**CANDIDATE, "user_id": 3001, "name": "Attorney 3001"}])
    def get(self, request, pk: int):
        app = _app(self.actor, pk)
        pool = assignment.rank_attorneys(candidates.attorney_candidates(), app.domain_code,
                                         app.applicant_user_id, inventor_ids(app),
                                         app.preferred_attorney_user_id)
        ctx = {"names": names(c.user_id for c in pool)}
        return Response(s.PmsCandidateSerializer(pool, many=True, context=ctx).data)


class AssignAttorneyView(WriteView):
    permission_classes = gate(P_ATTORNEY)

    @schema("Offer the case to an attorney (UC-PMS-010)", request=s.PmsAttorneyIn,
            response=s.PmsApplicationDetailSerializer, example_in={"attorney_user_id": 3001},
            example_out=EXAMPLE_DETAIL)
    def post(self, request, pk: int):
        body = s.PmsAttorneyIn(data=request.data)
        body.is_valid(raise_exception=True)
        attorneys.assign_attorney(actor=self.actor, pk=pk, **body.validated_data)
        return detail_response(self.actor, pk)


class RespondView(WriteView):
    permission_classes = gate("pms.attorney_assignment.review")

    @schema("Accept or decline an offered case (UC-PMS-011)", request=s.PmsRespondIn,
            response=s.PmsAssignmentSerializer, example_in={"accept": True},
            example_out=ASSIGNMENT)
    def post(self, request, pk: int):
        body = s.PmsRespondIn(data=request.data)
        body.is_valid(raise_exception=True)
        row = attorneys.respond(actor=self.actor, assignment_id=pk, **body.validated_data)
        return Response(s.PmsAssignmentSerializer(
            row, context={"names": names([row.attorney_user_id])}).data)


def _roster_response(rows, loads, code=status.HTTP_200_OK):
    ctx = {"names": names(r.user_id for r in rows), "workloads": loads}
    return Response(s.PmsRosterSerializer(rows, many=True, context=ctx).data, status=code)


class DirectorsView(WriteView):
    permission_classes = gate("pms.director_profile.update")

    @schema("The Director roster with workloads (PMS-AFR-222)",
            response=s.PmsRosterSerializer(many=True), example_out=[ROSTER_ROW])
    def get(self, request):
        return _roster_response(list(candidates.active_directors()),
                                candidates.director_workloads())

    @schema("Add a Director or change their areas (ruling C13)", request=s.PmsRosterIn,
            response=s.PmsRosterSerializer(many=True), status=201,
            example_in={"user_id": 2001, "domain_codes": ["materials"]},
            example_out=[ROSTER_ROW])
    def post(self, request):
        body = s.PmsRosterIn(data=request.data)
        body.is_valid(raise_exception=True)
        rosters.set_director(actor=self.actor, **body.validated_data)
        return _roster_response(list(candidates.active_directors()),
                                candidates.director_workloads(), status.HTTP_201_CREATED)


class DirectorEndView(WriteView):
    permission_classes = gate("pms.director_profile.update")

    @schema("Take a Director off the roster", request=None,
            response=s.PmsRosterSerializer(many=True), example_out=[])
    def post(self, request, pk: int):
        rosters.end_director(actor=self.actor, entry_id=pk)
        return _roster_response(list(candidates.active_directors()),
                                candidates.director_workloads())


class PanelView(WriteView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [p() for p in gate("pms.attorney_panel.update", P_ATTORNEY)]
        return [p() for p in gate("pms.attorney_panel.update")]

    @schema("The approved attorney panel (UC-PMS-026)", response=s.PmsRosterSerializer(many=True),
            example_out=[{**ROSTER_ROW, "user_id": 3001, "name": "Attorney 3001"}])
    def get(self, request):
        return _roster_response(list(candidates.active_panel()),
                                candidates.attorney_workloads())

    @schema("Add an attorney to the panel or change their areas", request=s.PmsRosterIn,
            response=s.PmsRosterSerializer(many=True), status=201,
            example_in={"user_id": 3001, "domain_codes": ["materials"]},
            example_out=[{**ROSTER_ROW, "user_id": 3001, "name": "Attorney 3001"}])
    def post(self, request):
        body = s.PmsRosterIn(data=request.data)
        body.is_valid(raise_exception=True)
        rosters.set_panel_attorney(actor=self.actor, **body.validated_data)
        return _roster_response(list(candidates.active_panel()),
                                candidates.attorney_workloads(), status.HTTP_201_CREATED)


class PanelEndView(WriteView):
    permission_classes = gate("pms.attorney_panel.update")

    @schema("Take an attorney off the panel", request=None,
            response=s.PmsRosterSerializer(many=True), example_out=[])
    def post(self, request, pk: int):
        rosters.end_panel_attorney(actor=self.actor, entry_id=pk)
        return _roster_response(list(candidates.active_panel()),
                                candidates.attorney_workloads())


class PanelOptionsView(PmsView):
    permission_classes = gate("pms.application.create")

    @schema("Panel attorneys an applicant may name as a preference (BR-PMS-045)",
            response=s.PmsPanelOptionSerializer(many=True),
            example_out=[{"user_id": 3001, "name": "Attorney 3001",
                          "domain_codes": ["materials"]}])
    def get(self, request):
        rows = list(candidates.active_panel())
        ctx = {"names": names(r.user_id for r in rows)}
        return Response(s.PmsPanelOptionSerializer(rows, many=True, context=ctx).data)
