"""The attorney's case work and the decisions it needs: opinions, budgets, filing, post-filing."""
from __future__ import annotations

from rest_framework.response import Response

from modules.pms.api import serializers as s
from modules.pms.api.applications import EXAMPLE_DETAIL, detail_response
from modules.pms.api.common import WriteView, gate, names, schema
from modules.pms.services import budget, communications, filing, legal, maintenance
from modules.pms.services import office_actions as oa

BUDGET = {"id": 5, "application_id": 7, "filing_fee": "8000.00", "attorney_fee": "40000.00",
          "admin_cost": "2000.00", "total": "50000.00", "status": "approved",
          "decision_note": "", "decided_at": "2026-11-12T10:00:00+05:30",
          "threshold_at_decision": "100000.00", "availability": "not_available",
          "routed_to": "", "external_reference": "", "external_decided_on": None,
          "created_at": "2026-11-11T10:00:00+05:30"}
OFFICE_ACTION = {"id": 2, "application_id": 7, "reference": "FER/2027/11",
                 "received_on": "2027-03-01", "response_due_on": "2027-09-01",
                 "current_due_on": "2027-09-01", "requires_applicant_review": True,
                 "status": "awaiting_applicant_approval", "draft_response": "...",
                 "approved_at": None, "submitted_on": None, "submission_reference": "",
                 "extensions": []}
CYCLE = {"id": 1, "application_id": 7, "seq": 1, "due_on": "2029-03-01", "source": "schedule",
         "status": "decision_requested", "deciding_director_user_id": 2001,
         "director_name": "Director 2001", "decided_at": None, "decision_note": "",
         "action_reference": "", "amount": None, "actioned_on": None}


class _Body(WriteView):
    serializer = None

    def body(self):
        data = self.serializer(data=self.request.data)
        data.is_valid(raise_exception=True)
        return data.validated_data


class AssessmentView(_Body):
    permission_classes = gate("pms.assessment.create")
    serializer = s.PmsAssessmentIn

    @schema("Save a patentability assessment draft (UC-PMS-012)", request=s.PmsAssessmentIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"analysis": "Claims 1-3 read on...", "novelty": "Novel over D1."},
            example_out=EXAMPLE_DETAIL)
    def post(self, request, pk: int):
        data = self.body()
        legal.save_assessment(actor=self.actor, pk=pk, fields=data,
                              assessment_id=data.get("assessment_id"))
        return detail_response(self.actor, pk)


class FinalizeAssessmentView(WriteView):
    permission_classes = gate("pms.assessment.create")

    @schema("Finalize the opinion with one recommendation (BR-PMS-046)", request=None,
            response=s.PmsAssessmentSerializer,
            example_out={"id": 1, "analysis": "...", "novelty": "...",
                         "non_obviousness": "...", "utility": "...",
                         "recommendation": "file_patent", "status": "final",
                         "finalized_at": "2026-11-14T10:00:00+05:30",
                         "updated_at": "2026-11-14T10:00:00+05:30"})
    def post(self, request, pk: int):
        return Response(s.PmsAssessmentSerializer(
            legal.finalize_assessment(actor=self.actor, assessment_id=pk)).data)


class LegalRequestView(_Body):
    permission_classes = gate("pms.legal_request.create")
    serializer = s.PmsLegalRequestIn

    @schema("Ask the applicant for information or an extension (PMS-AFR-086, 087)",
            request=s.PmsLegalRequestIn, response=s.PmsApplicationDetailSerializer,
            example_in={"kind": "information", "message": "Send the test data for claim 2."},
            example_out=EXAMPLE_DETAIL)
    def post(self, request, pk: int):
        legal.request(actor=self.actor, pk=pk, **self.body())
        return detail_response(self.actor, pk)


class LegalAdviceView(_Body):
    permission_classes = gate("pms.legal_advice.create")
    serializer = s.PmsAdviceIn

    @schema("Record legal advice (UC-PMS-033)", request=s.PmsAdviceIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"advice": "Avoid publishing the thesis chapter before filing."},
            example_out=EXAMPLE_DETAIL)
    def post(self, request, pk: int):
        legal.record_advice(actor=self.actor, pk=pk, **self.body())
        return detail_response(self.actor, pk)


class BudgetProposeView(_Body):
    permission_classes = gate("pms.budget.create")
    serializer = s.PmsBudgetIn

    @schema("Propose the filing and prosecution budget (UC-PMS-009)", request=s.PmsBudgetIn,
            response=s.PmsBudgetSerializer, status=201,
            example_in={"filing_fee": "8000", "attorney_fee": "40000", "admin_cost": "2000"},
            example_out={**BUDGET, "status": "proposed", "decided_at": None})
    def post(self, request, pk: int):
        row = budget.propose(actor=self.actor, pk=pk, **self.body())
        return Response(s.PmsBudgetSerializer(row).data, status=201)


class BudgetDecisionView(_Body):
    permission_classes = gate("pms.budget.approve")
    serializer = s.PmsBudgetDecisionIn

    @schema("Decide a budget; above the threshold it escalates (BR-PMS-051..053)",
            request=s.PmsBudgetDecisionIn, response=s.PmsBudgetSerializer,
            example_in={"approve": True}, example_out=BUDGET)
    def post(self, request, pk: int):
        return Response(s.PmsBudgetSerializer(
            budget.decide(actor=self.actor, budget_id=pk, **self.body())).data)


class BudgetRouteView(_Body):
    permission_classes = gate("pms.escalation.review")
    serializer = s.PmsRouteIn

    @schema("Route an escalated budget to the higher authority (BW-PMS-10)", request=s.PmsRouteIn,
            response=s.PmsBudgetSerializer, example_in={"routed_to": "Finance Committee"},
            example_out={**BUDGET, "status": "escalation_tracked",
                         "routed_to": "Finance Committee"})
    def post(self, request, pk: int):
        return Response(s.PmsBudgetSerializer(
            budget.route_escalation(actor=self.actor, budget_id=pk, **self.body())).data)


class BudgetExternalView(_Body):
    permission_classes = gate("pms.escalation.review")
    serializer = s.PmsExternalDecisionIn

    @schema("Record the higher authority's decision (ruling C14)", request=s.PmsExternalDecisionIn,
            response=s.PmsBudgetSerializer,
            example_in={"approved": True, "reference": "FC/2026/31",
                        "decided_on": "2026-11-20"},
            example_out={**BUDGET, "status": "external_approved",
                         "external_reference": "FC/2026/31"})
    def post(self, request, pk: int):
        return Response(s.PmsBudgetSerializer(budget.record_external_decision(
            actor=self.actor, budget_id=pk, **self.body())).data)


class FilingView(_Body):
    permission_classes = gate("pms.filing.create")
    serializer = s.PmsFilingIn

    @schema("Record a filing confirmed by the patent office (UC-PMS-013)", request=s.PmsFilingIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"jurisdiction": "IN", "office_name": "Indian Patent Office",
                        "external_filing_id": "202621004321", "filing_date": "2026-11-20",
                        "confirmation_reference": "CBR 11023"},
            example_out={**EXAMPLE_DETAIL, "status": "filed"})
    def post(self, request, pk: int):
        filing.record_filing(actor=self.actor, pk=pk, **self.body())
        return detail_response(self.actor, pk)


class CommunicationView(_Body):
    permission_classes = gate("pms.communication.create")
    serializer = s.PmsCommunicationIn

    @schema("Record a patent-office communication (UC-PMS-014)", request=s.PmsCommunicationIn,
            response=s.PmsApplicationDetailSerializer,
            example_in={"kind": "office_action", "received_on": "2027-03-01",
                        "reference": "FER/2027/11", "response_due_on": "2027-09-01",
                        "requires_applicant_review": True},
            example_out={**EXAMPLE_DETAIL, "status": "filed"})
    def post(self, request, pk: int):
        communications.record(actor=self.actor, pk=pk, **self.body())
        return detail_response(self.actor, pk)


def _oa(row):
    return Response(s.PmsOfficeActionSerializer(row).data)


class ResponseDraftView(_Body):
    permission_classes = gate("pms.office_action_response.create")
    serializer = s.PmsDraftResponseIn

    @schema("Prepare the office-action response (UC-PMS-015)", request=s.PmsDraftResponseIn,
            response=s.PmsOfficeActionSerializer, example_in={"draft": "Claim 1 is amended..."},
            example_out=OFFICE_ACTION)
    def post(self, request, pk: int):
        return _oa(oa.prepare_response(actor=self.actor, office_action_id=pk, **self.body()))


class ResponseApproveView(WriteView):
    permission_classes = gate("pms.office_action_response.approve")

    @schema("Approve the response as the applicant (UC-PMS-029)", request=None,
            response=s.PmsOfficeActionSerializer,
            example_out={**OFFICE_ACTION, "status": "applicant_approved"})
    def post(self, request, pk: int):
        return _oa(oa.approve_response(actor=self.actor, office_action_id=pk))


class ResponseSubmissionView(_Body):
    permission_classes = gate("pms.office_action_response.update")
    serializer = s.PmsSubmissionIn

    @schema("Record the response's submission (BR-PMS-065)", request=s.PmsSubmissionIn,
            response=s.PmsOfficeActionSerializer,
            example_in={"submitted_on": "2027-08-20", "reference": "RESP/2027/4"},
            example_out={**OFFICE_ACTION, "status": "submitted",
                         "submitted_on": "2027-08-20"})
    def post(self, request, pk: int):
        return _oa(oa.record_submission(actor=self.actor, office_action_id=pk, **self.body()))


class ResponseExtensionView(_Body):
    permission_classes = gate("pms.office_action_response.update")
    serializer = s.PmsExtensionIn

    @schema("Record an extension the office granted (PMS-AFR-122)", request=s.PmsExtensionIn,
            response=s.PmsOfficeActionSerializer,
            example_in={"new_due_on": "2027-10-01", "reason": "Lab data pending."},
            example_out={**OFFICE_ACTION, "current_due_on": "2027-10-01"})
    def post(self, request, pk: int):
        return _oa(oa.record_extension(actor=self.actor, office_action_id=pk, **self.body()))


def _cycle(row):
    return Response(s.PmsMaintenanceCycleSerializer(
        row, context={"names": names([row.deciding_director_user_id])}).data)


class CycleAddView(_Body):
    permission_classes = gate("pms.maintenance.update")
    serializer = s.PmsDueDateIn

    @schema("Enter a maintenance due date by hand (blueprint Q-12)", request=s.PmsDueDateIn,
            response=s.PmsMaintenanceCycleSerializer, example_in={"due_on": "2029-03-01"},
            example_out={**CYCLE, "status": "scheduled", "source": "manual"})
    def post(self, request, pk: int):
        return _cycle(maintenance.add_cycle(actor=self.actor, pk=pk, **self.body()))


class CycleRequestView(WriteView):
    permission_classes = gate("pms.maintenance.update")

    @schema("Ask the Director for a renewal decision (PMS-AFR-111)", request=None,
            response=s.PmsMaintenanceCycleSerializer, example_out=CYCLE)
    def post(self, request, pk: int):
        return _cycle(maintenance.request_decision(actor=self.actor, cycle_id=pk))


class CycleDecisionView(_Body):
    permission_classes = gate("pms.renewal.approve")
    serializer = s.PmsRenewalIn

    @schema("Decide Renew or Do Not Renew (UC-PMS-018)", request=s.PmsRenewalIn,
            response=s.PmsMaintenanceCycleSerializer, example_in={"renew": True},
            example_out={**CYCLE, "status": "renew_approved"})
    def post(self, request, pk: int):
        return _cycle(maintenance.decide(actor=self.actor, cycle_id=pk, **self.body()))


class CycleActionView(_Body):
    permission_classes = gate("pms.maintenance.update")
    serializer = s.PmsMaintenanceActionIn

    @schema("Record the maintenance payment (PMS-AFR-113)", request=s.PmsMaintenanceActionIn,
            response=s.PmsMaintenanceCycleSerializer,
            example_in={"reference": "RCPT-88", "amount": "4000", "actioned_on": "2029-02-20"},
            example_out={**CYCLE, "status": "renewed", "action_reference": "RCPT-88"})
    def post(self, request, pk: int):
        return _cycle(maintenance.record_action(actor=self.actor, cycle_id=pk, **self.body()))


class CycleReassignView(_Body):
    permission_classes = gate("pms.renewal.assign")
    serializer = s.PmsPersonIn

    @schema("Give the renewal decision to another Director (ruling C19)", request=s.PmsPersonIn,
            response=s.PmsMaintenanceCycleSerializer, example_in={"director_user_id": 2002},
            example_out={**CYCLE, "deciding_director_user_id": 2002})
    def post(self, request, pk: int):
        return _cycle(maintenance.reassign_decider(actor=self.actor, cycle_id=pk,
                                                   **self.body()))
