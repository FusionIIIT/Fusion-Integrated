"""The service layer end to end: every state change, every refusal, with the rows left behind.

Covers the business rules end to end: IAA-BR-001..006, 101..104, 201, 202, 301, 302, 401, 501..504.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.iaa.domain import roles
from modules.iaa.models import (
    Anomaly,
    ApprovalStep,
    AuditObservation,
    BudgetEntry,
    FinancialRecord,
    Notification,
    ObservationResponse,
    PolicyVersion,
    TrailEntry,
)
from modules.iaa.selectors import policy as policy_selectors
from modules.iaa.services import (
    anomalies,
    configuration,
    decisions,
    observations,
    processing,
    records,
    review,
)
from modules.iaa.services.records import SubmissionIncomplete
from modules.iaa.tests.helpers import DOC, FACULTY, POLICY, actor, new_expense, new_ta

pytestmark = pytest.mark.django_db


def _trail(record, action):
    return list(TrailEntry.objects.filter(entity="record", entity_id=record.pk, action=action))


# ── expense: the happy path and what it leaves behind ───────────────────────────────────

def test_an_expense_runs_from_draft_to_recorded_and_commits_the_budget(people, configured):
    draft = new_expense(people.creator, submit=False)
    assert draft.status == "draft"

    submitted = records.submit(people.creator, draft.pk)
    assert submitted.status == "submitted" and submitted.financial_year == configured

    validated = review.validate(people.finance, draft.pk)
    assert validated.status == "finance_validated" and validated.route_levels == [roles.HOD]

    approved = decisions.decide(people.hod, draft.pk, decision="approve", remarks="Within plan.")
    assert approved.status == "approved"

    done = processing.record(people.finance, draft.pk, reference="VCH-77", note="Filed")
    assert done.status == "recorded" and done.processing_reference == "VCH-77"

    commitment = BudgetEntry.objects.get(record=done)
    assert commitment.kind == "commitment" and commitment.amount == Decimal("-10000")
    assert policy_selectors.available_budget(configured, "CSE") == Decimal("490000")


def test_every_step_is_in_the_trail_with_identity_role_and_resulting_status(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="Fine")
    processing.record(people.finance, rec.pk, reference="V1")

    trail = list(TrailEntry.objects.filter(entity="record", entity_id=rec.pk).order_by("id"))
    assert [t.to_status for t in trail if t.action not in ("create", "add_document")] == [
        "submitted", "finance_validated", "approved", "recorded"]
    by_action = {t.action: t for t in trail}
    assert by_action["submit"].actor_user_id == 101 and by_action["submit"].actor_role == FACULTY
    assert by_action["validate"].actor_role == roles.FINANCE
    assert by_action["approve_final"].actor_user_id == 301
    assert by_action["approve_final"].actor_role == roles.HOD
    assert by_action["approve_final"].remarks == "Fine"
    assert by_action["record"].to_status == "recorded"


def test_recording_is_internal_only_and_says_no_payment_was_made(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="ok")
    processing.record(people.finance, rec.pk, reference="V2")
    note = _trail(rec, "record")[0].remarks
    assert "No payment executed" in note                                    # IAA-BR-006
    assert not hasattr(FinancialRecord, "bank_account")


def test_a_recorded_item_is_read_only_and_terminal(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="ok")
    processing.record(people.finance, rec.pk, reference="V3")
    with pytest.raises(ConflictError):
        records.update_draft(people.creator, rec.pk, title="Changed")
    with pytest.raises(ConflictError):
        records.add_document(people.creator, rec.pk, **DOC)
    with pytest.raises(ConflictError):
        processing.record(people.finance, rec.pk, reference="V3-again")
    with pytest.raises(ConflictError):
        decisions.decide(people.hod, rec.pk, decision="reject", remarks="late")


def test_recording_needs_a_reference(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="ok")
    with pytest.raises(DomainError) as exc:
        processing.record(people.finance, rec.pk, reference="  ")
    assert exc.value.code == "reference_required"


# ── drafts and submission (IAA-BR-101) ──────────────────────────────────────────────────

def test_an_incomplete_draft_can_be_saved_but_not_submitted(people, configured):
    draft = records.create_expense(people.creator)                 # nothing filled in
    assert draft.status == "draft"
    with pytest.raises(SubmissionIncomplete) as exc:
        records.submit(people.creator, draft.pk)
    fields = {d["field"] for d in exc.value.details}
    assert {"department", "amount", "title", "description", "request_type",
            "documents"} <= fields
    assert FinancialRecord.objects.get(pk=draft.pk).status == "draft"


def test_a_draft_stays_editable_until_it_is_submitted(people, configured):
    draft = records.create_expense(people.creator)
    updated = records.update_draft(people.creator, draft.pk, title="Kits", amount=Decimal("5"))
    assert updated.title == "Kits"
    records.update_draft(people.creator, draft.pk, department="CSE", request_type="voucher",
                         description="x", amount=Decimal("5"))
    records.add_document(people.creator, draft.pk, **DOC)
    records.submit(people.creator, draft.pk)
    with pytest.raises(ConflictError) as exc:
        records.update_draft(people.creator, draft.pk, title="Sneaky")      # IAA-BR-104
    assert exc.value.code == "record_locked"


def test_submission_needs_the_configured_number_of_documents(people, configured):
    rec = new_expense(people.creator, docs=0, submit=False)
    with pytest.raises(SubmissionIncomplete) as exc:
        records.submit(people.creator, rec.pk)
    assert [d["field"] for d in exc.value.details] == ["documents"]


def test_nothing_is_submitted_without_a_policy_or_a_financial_year(people):
    rec = new_expense(people.creator, submit=False)
    with pytest.raises(ConflictError) as exc:
        records.submit(people.creator, rec.pk)
    assert exc.value.code == "policy_missing"
    configuration.publish_policy(people.admin, POLICY)
    with pytest.raises(ConflictError) as exc:
        records.submit(people.creator, rec.pk)
    assert exc.value.code == "financial_year_missing"


def test_only_the_owner_can_touch_their_draft(people, configured):
    rec = new_expense(people.creator, submit=False)
    for call in (lambda: records.update_draft(people.other, rec.pk, title="x"),
                 lambda: records.add_document(people.other, rec.pk, **DOC),
                 lambda: records.submit(people.other, rec.pk)):
        with pytest.raises(NotFoundError):
            call()


def test_a_document_cannot_be_added_to_a_submitted_item_outside_a_query(people, configured):
    rec = new_expense(people.creator)
    with pytest.raises(ConflictError):
        records.add_document(people.creator, rec.pk, **DOC)


# ── clarification (UC-103/104) ──────────────────────────────────────────────────────────

def test_finance_can_query_the_creator_who_answers_and_review_resumes(people, configured):
    rec = new_expense(people.creator)
    queried = review.raise_query(people.finance, rec.pk, question="Which lab?")
    assert queried.status == "query_raised"
    assert Notification.objects.filter(recipient_user_id=101, kind="query_raised").exists()

    records.add_document(people.creator, rec.pk, title="Lab letter",
                         link="https://files.example/lab.pdf")
    answered = records.respond_query(people.creator, rec.pk, response="Embedded lab")
    assert answered.status == "query_responded"
    assert rec.queries.get().response == "Embedded lab"
    assert len(_trail(rec, "raise_query")) == 1 and len(_trail(rec, "respond_query")) == 1

    assert review.validate(people.finance, rec.pk).status == "finance_validated"


def test_a_query_needs_a_question_and_a_response_needs_text(people, configured):
    rec = new_expense(people.creator)
    with pytest.raises(DomainError):
        review.raise_query(people.finance, rec.pk, question=" ")
    review.raise_query(people.finance, rec.pk, question="Why?")
    with pytest.raises(DomainError):
        records.respond_query(people.creator, rec.pk, response=" ")


def test_a_response_with_no_open_query_is_refused(people, configured):
    rec = new_expense(people.creator)
    with pytest.raises(ConflictError):
        records.respond_query(people.creator, rec.pk, response="Unasked")


def test_only_the_creator_can_answer_and_only_once(people, configured):
    rec = new_expense(people.creator)
    review.raise_query(people.finance, rec.pk, question="Why?")
    with pytest.raises(NotFoundError):
        records.respond_query(people.other, rec.pk, response="Not mine")
    records.respond_query(people.creator, rec.pk, response="Because")
    with pytest.raises(ConflictError):
        records.respond_query(people.creator, rec.pk, response="Again")


# ── approval routing and levels (IAA-BR-002) ────────────────────────────────────────────

def test_a_large_expense_needs_two_levels_in_order(people, configured):
    rec = new_expense(people.creator, amount="60000")
    review.validate(people.finance, rec.pk)
    rec.refresh_from_db()
    assert rec.route_levels == [roles.HOD, roles.DEAN]

    first = decisions.decide(people.hod, rec.pk, decision="approve", remarks="Level 1")
    assert first.status == "approval_pending" and first.current_level == 1
    with pytest.raises(ConflictError) as exc:
        decisions.decide(people.hod, rec.pk, decision="approve", remarks="Again")
    assert exc.value.code == "not_assigned"
    with pytest.raises(NotFoundError):                       # no step assigned to the director yet
        decisions.decide(people.director, rec.pk, decision="approve", remarks="Early")

    final = decisions.decide(people.dean, rec.pk, decision="approve", remarks="Level 2")
    assert final.status == "approved"
    steps = list(ApprovalStep.objects.filter(record=rec).order_by("level"))
    assert [(s.designation, s.status) for s in steps] == [(roles.HOD, "approved"),
                                                          (roles.DEAN, "approved")]


def test_the_route_is_the_one_in_force_when_validated_even_if_policy_changes(
        people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    configuration.publish_policy(people.admin, {
        **POLICY, "routes": [
            {"kind": "expense", "levels": [roles.DIRECTOR], "escalation_designation": ""},
            *[r for r in POLICY["routes"] if r["kind"] == "ta"]]})
    rec.refresh_from_db()
    assert rec.route_levels == [roles.HOD]
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="old route")


def test_validation_is_refused_when_no_route_covers_the_amount(people, configured):
    configuration.publish_policy(people.admin, {
        **POLICY, "routes": [
            {"kind": "expense", "min_amount": "0", "max_amount": "1000", "levels": [roles.HOD]},
            *[r for r in POLICY["routes"] if r["kind"] == "ta"]]})
    rec = new_expense(people.creator)
    with pytest.raises(ConflictError) as exc:
        review.validate(people.finance, rec.pk)
    assert exc.value.code == "route_missing"
    assert FinancialRecord.objects.get(pk=rec.pk).status == "submitted"


# ── decisions need remarks, and a rejection ends it (IAA-BR-005) ────────────────────────

def test_a_decision_needs_remarks_and_a_valid_choice(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    for remarks in ("", "   "):
        with pytest.raises(DomainError) as exc:
            decisions.decide(people.hod, rec.pk, decision="approve", remarks=remarks)
        assert exc.value.code == "remarks_required"
    with pytest.raises(DomainError) as exc:
        decisions.decide(people.hod, rec.pk, decision="maybe", remarks="hm")
    assert exc.value.code == "invalid_decision"
    assert FinancialRecord.objects.get(pk=rec.pk).status == "finance_validated"


def test_a_rejection_is_final_and_tells_the_creator(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    out = decisions.decide(people.hod, rec.pk, decision="reject", remarks="Not budgeted")
    assert out.status == "rejected"
    step = ApprovalStep.objects.get(record=rec)
    assert (step.status, step.decided_by, step.decided_role, step.remarks) == (
        "rejected", 301, roles.HOD, "Not budgeted")
    assert step.decided_at is not None
    assert Notification.objects.filter(recipient_user_id=101, kind="rejected").exists()
    with pytest.raises(ConflictError):
        processing.record(people.finance, rec.pk, reference="V")
    with pytest.raises(ConflictError):
        decisions.decide(people.hod, rec.pk, decision="approve", remarks="reversed?")


# ── segregation of duties (IAA-BR-001) ──────────────────────────────────────────────────

def test_a_creator_cannot_approve_their_own_item_and_it_moves_to_the_next_authority(
        people, configured):
    same_person_as_hod = actor(301, FACULTY)                 # user 301 also acts as HoD
    rec = new_expense(same_person_as_hod)
    review.validate(people.finance, rec.pk)

    with pytest.raises(PermissionDeniedError) as exc:
        decisions.decide(people.hod, rec.pk, decision="approve", remarks="Mine, so fine")
    assert exc.value.code == "segregation_of_duties"

    rec.refresh_from_db()
    assert rec.status == "finance_validated"
    steps = list(ApprovalStep.objects.filter(record=rec).order_by("id"))
    assert [(s.designation, s.status) for s in steps] == [
        (roles.HOD, "rerouted"), (roles.DEAN, "pending")]
    assert _trail(rec, "reroute_sod")
    assert Notification.objects.filter(recipient_role=roles.DEAN,
                                       kind="approval_needed").exists()
    # The creator is no longer assigned, so a second attempt is simply "not yours".
    with pytest.raises(ConflictError):
        decisions.decide(people.hod, rec.pk, decision="approve", remarks="Try again")

    approved = decisions.decide(people.dean, rec.pk, decision="approve", remarks="Independent")
    assert approved.status == "approved"


def test_self_rejection_is_blocked_too(people, configured):
    rec = new_expense(actor(301, FACULTY))
    review.validate(people.finance, rec.pk)
    with pytest.raises(PermissionDeniedError):
        decisions.decide(people.hod, rec.pk, decision="reject", remarks="Mine")
    assert FinancialRecord.objects.get(pk=rec.pk).status == "finance_validated"


def test_with_nobody_else_on_the_route_a_self_decision_is_a_conflict(people, configured):
    configuration.publish_policy(people.admin, {
        **POLICY, "routes": [
            {"kind": "expense", "levels": [roles.HOD], "escalation_designation": ""},
            *[r for r in POLICY["routes"] if r["kind"] == "ta"]]})
    rec = new_expense(actor(301, FACULTY))
    review.validate(people.finance, rec.pk)
    with pytest.raises(ConflictError) as exc:
        decisions.decide(people.hod, rec.pk, decision="approve", remarks="Mine")
    assert exc.value.code == "segregation_of_duties"


def test_a_ta_claimant_cannot_approve_their_own_claim(people, configured):
    claim = new_ta(actor(301, FACULTY), amount="30000")
    review.validate(people.finance, claim.pk)
    with pytest.raises(PermissionDeniedError):
        decisions.decide(people.hod, claim.pk, decision="approve", remarks="Mine")
    assert FinancialRecord.objects.get(pk=claim.pk).status == "approval_pending"


# ── TA claims (UC-401..404) ─────────────────────────────────────────────────────────────

def test_a_normal_ta_claim_is_verified_by_finance_then_recorded_without_approval(
        people, configured):
    claim = new_ta(people.creator, amount="10000")
    assert claim.status == "submitted" and claim.kind == "ta"
    assert claim.documents.count() == 1 and claim.financial_year == configured

    verified = review.validate(people.finance, claim.pk, decision="verify")
    assert verified.status == "verified" and not ApprovalStep.objects.filter(record=claim)
    done = processing.record(people.finance, claim.pk, reference="TA-1")
    assert done.status == "recorded"


def test_a_high_value_ta_claim_goes_to_an_authority_before_recording(people, configured):
    claim = new_ta(people.creator, amount="25000")                 # exactly at the threshold
    pending = review.validate(people.finance, claim.pk)
    assert pending.status == "approval_pending" and pending.route_levels == [roles.HOD]
    with pytest.raises(ConflictError):                            # not recordable before approval
        processing.record(people.finance, claim.pk, reference="TA-2")
    decisions.decide(people.hod, claim.pk, decision="approve", remarks="Valid trip")
    assert processing.record(people.finance, claim.pk, reference="TA-2").status == "recorded"


def test_a_ta_claim_just_under_the_threshold_needs_no_authority(people, configured):
    claim = new_ta(people.creator, amount="24999.99")
    assert review.validate(people.finance, claim.pk).status == "verified"


def test_a_high_value_ta_claim_can_be_rejected_by_the_authority(people, configured):
    claim = new_ta(people.creator, amount="40000")
    review.validate(people.finance, claim.pk)
    out = decisions.decide(people.hod, claim.pk, decision="reject", remarks="Not on duty")
    assert out.status == "rejected"


def test_finance_can_reject_a_ta_claim_for_policy_but_only_with_a_reason(people, configured):
    claim = new_ta(people.creator)
    with pytest.raises(DomainError) as exc:
        review.validate(people.finance, claim.pk, decision="reject", remarks="")
    assert exc.value.code == "remarks_required"
    out = review.validate(people.finance, claim.pk, decision="reject", remarks="Over cap")
    assert out.status == "rejected"
    assert Notification.objects.filter(recipient_user_id=101, kind="rejected").exists()


def test_an_expense_cannot_be_rejected_by_finance_only_queried_or_validated(
        people, configured):
    rec = new_expense(people.creator)
    with pytest.raises(ConflictError):
        review.validate(people.finance, rec.pk, decision="reject", remarks="No")
    assert FinancialRecord.objects.get(pk=rec.pk).status == "submitted"


def test_ta_submission_is_blocked_when_details_or_documents_are_missing(people, configured):
    today = timezone.localdate()
    base = {"department": "CSE", "amount": Decimal("100"), "purpose": "Trip",
            "trip_start": today, "trip_end": today, "documents": [DOC]}
    for bad in ({"documents": []}, {"purpose": ""}, {"amount": None},
                {"trip_start": None}, {"trip_end": today - timedelta(days=2)}):
        with pytest.raises(SubmissionIncomplete):
            records.create_ta(people.creator, **{**base, **bad})
    assert not FinancialRecord.objects.filter(kind="ta").exists()


def test_finance_can_query_a_ta_claimant_who_answers(people, configured):
    claim = new_ta(people.creator)
    review.raise_query(people.finance, claim.pk, question="Boarding pass?")
    records.respond_query(people.creator, claim.pk, response="Attached")
    assert review.validate(people.finance, claim.pk).status == "verified"


# ── budget (IAA-BR-102) ─────────────────────────────────────────────────────────────────

def test_insufficient_budget_flags_an_anomaly_and_does_not_reject(people, configured):
    rec = new_expense(people.creator, department="ECE")               # no allocation
    out = review.validate(people.finance, rec.pk)
    assert out.status == "finance_validated"
    anomaly = Anomaly.objects.get(record=rec)
    assert (anomaly.category, anomaly.source, anomaly.status) == ("budget", "automatic", "open")
    assert anomaly.assigned_role == roles.FINANCE
    assert "short by 10000" in anomaly.description
    assert Notification.objects.filter(recipient_role=roles.FINANCE, kind="anomaly").exists()


def test_a_request_that_fits_the_budget_raises_nothing(people, configured):
    rec = new_expense(people.creator, amount="500000")                # exactly the allocation
    review.validate(people.finance, rec.pk)
    assert not Anomaly.objects.exists()


def test_when_the_policy_says_the_budget_is_not_required_nothing_is_checked(
        people, configured):
    configuration.publish_policy(people.admin, {**POLICY, "budget_check_required": False})
    rec = new_expense(people.creator, department="ECE")
    review.validate(people.finance, rec.pk)
    assert not Anomaly.objects.exists()


def test_the_budget_ledger_reflects_commitments_adjustments_and_allocations(
        people, configured):
    configuration.add_budget_entry(people.admin, financial_year_id=configured.pk,
                                   department="CSE", kind="adjustment", amount=Decimal("-100000"))
    assert policy_selectors.available_budget(configured, "CSE") == Decimal("400000")
    rec = new_expense(people.creator, amount="450000")
    review.validate(people.finance, rec.pk)
    assert Anomaly.objects.get(record=rec).description.count("short by 50000") == 1


# ── anomalies (IAA-BR-103) ──────────────────────────────────────────────────────────────

def test_finance_flags_an_anomaly_and_the_first_resolver_resolves_it(people, configured):
    rec = new_expense(people.creator)
    flagged = anomalies.flag(people.finance, category="policy", description="Split bills",
                             record_id=rec.pk)
    assert (flagged.status, flagged.source, flagged.assigned_role) == (
        "open", "manual", roles.FINANCE)
    assert _trail(rec, "anomaly_flagged")

    done = anomalies.resolve(people.finance, flagged.pk, resolution="Verified with vendor")
    assert (done.status, done.resolved_role, done.resolved_by) == (
        "resolved", roles.FINANCE, 201)
    with pytest.raises(ConflictError):
        anomalies.resolve(people.finance, flagged.pk, resolution="Again")


def test_an_anomaly_escalates_along_its_chain_and_then_has_nowhere_to_go(people, configured):
    flagged = anomalies.flag(people.finance, category="budget", description="Overspend")
    esc = anomalies.escalate(people.finance, flagged.pk, remarks="Above my remit")
    assert (esc.status, esc.assigned_role) == ("escalated", roles.DEAN)
    assert Notification.objects.filter(recipient_role=roles.DEAN,
                                       kind="anomaly_escalated").exists()
    with pytest.raises(ConflictError) as exc:             # visible to Finance, but no longer theirs
        anomalies.resolve(people.finance, flagged.pk, resolution="Late")
    assert exc.value.code == "not_assigned"
    with pytest.raises(ConflictError):
        anomalies.escalate(people.dean, flagged.pk, remarks="Again")
    done = anomalies.resolve(people.dean, flagged.pk, resolution="Reallocated")
    assert done.status == "resolved"


def test_a_single_resolver_category_cannot_escalate(people, configured):
    configuration.publish_policy(people.admin, {
        **POLICY, "anomaly_resolvers": {**POLICY["anomaly_resolvers"],
                                        "financial": [roles.AUDITOR]}})
    flagged = anomalies.flag(people.auditor, category="financial", description="Odd ledger")
    with pytest.raises(ConflictError) as exc:
        anomalies.escalate(people.auditor, flagged.pk, remarks="Up")
    assert exc.value.code == "no_further_resolver"


def test_only_the_assigned_role_may_act_on_an_anomaly(people, configured):
    flagged = anomalies.flag(people.finance, category="policy", description="x")
    with pytest.raises(NotFoundError):
        anomalies.resolve(people.hod, flagged.pk, resolution="Not mine")


def test_flagging_needs_a_category_a_description_and_a_flagging_role(people, configured):
    with pytest.raises(DomainError) as exc:
        anomalies.flag(people.finance, category="mood", description="x")
    assert exc.value.code == "invalid_category"
    with pytest.raises(DomainError):
        anomalies.flag(people.finance, category="policy", description=" ")
    with pytest.raises(NotFoundError):
        anomalies.flag(people.finance, category="policy", description="x", record_id=9999)
    approver_with_flag = actor(301, roles.HOD, permissions=["iaa.anomaly.create"])
    with pytest.raises(ConflictError):
        anomalies.flag(approver_with_flag, category="policy", description="x")


def test_resolving_and_escalating_need_text(people, configured):
    flagged = anomalies.flag(people.finance, category="budget", description="x")
    with pytest.raises(DomainError):
        anomalies.resolve(people.finance, flagged.pk, resolution="")
    with pytest.raises(DomainError):
        anomalies.escalate(people.finance, flagged.pk, remarks="")


# ── audit observations (IAA-BR-301/302) ─────────────────────────────────────────────────

def _observe(people, rec):
    return observations.raise_observation(
        people.auditor, title="Missing sign-off", detail="No HoD note", record_id=rec.pk)


def test_an_observation_runs_through_response_return_and_closure(people, configured):
    rec = new_expense(people.creator)
    obs = _observe(people, rec)
    assert (obs.status, obs.respondent_user_id, obs.cycle) == ("open", 101, 1)

    obs = observations.respond(people.creator, obs.pk, corrective_action="Added note",
                               evidence_link="https://files.example/note.pdf")
    assert obs.status == "responded"
    obs = observations.review(people.auditor, obs.pk, verdict="unsatisfactory",
                              remarks="Evidence is unsigned")
    assert (obs.status, obs.cycle) == ("open", 2)

    obs = observations.respond(people.creator, obs.pk, corrective_action="Signed copy")
    obs = observations.review(people.auditor, obs.pk, verdict="satisfactory")
    assert obs.status == "closed"

    history = list(ObservationResponse.objects.filter(observation=obs).order_by("cycle"))
    assert [(r.cycle, r.verdict) for r in history] == [(1, "unsatisfactory"),
                                                       (2, "satisfactory")]
    assert history[0].evidence_link.endswith("note.pdf")      # nothing was overwritten


def test_closure_is_blocked_until_a_response_exists(people, configured):
    obs = _observe(people, new_expense(people.creator))
    with pytest.raises(ConflictError) as exc:
        observations.review(people.auditor, obs.pk, verdict="satisfactory")
    assert exc.value.code == "invalid_transition"
    assert AuditObservation.objects.get(pk=obs.pk).status == "open"


def test_a_closed_observation_cannot_be_reopened_or_answered(people, configured):
    obs = _observe(people, new_expense(people.creator))
    observations.respond(people.creator, obs.pk, corrective_action="Done")
    observations.review(people.auditor, obs.pk, verdict="satisfactory")
    with pytest.raises(ConflictError):
        observations.respond(people.creator, obs.pk, corrective_action="More")
    with pytest.raises(ConflictError):
        observations.review(people.auditor, obs.pk, verdict="unsatisfactory", remarks="No")


def test_an_unsatisfactory_verdict_needs_remarks_and_a_verdict_must_be_valid(
        people, configured):
    obs = _observe(people, new_expense(people.creator))
    observations.respond(people.creator, obs.pk, corrective_action="x")
    with pytest.raises(DomainError) as exc:
        observations.review(people.auditor, obs.pk, verdict="unsatisfactory", remarks="")
    assert exc.value.code == "remarks_required"
    with pytest.raises(DomainError) as exc:
        observations.review(people.auditor, obs.pk, verdict="meh")
    assert exc.value.code == "invalid_verdict"


def test_only_the_respondent_can_respond_and_only_an_auditor_can_raise(people, configured):
    rec = new_expense(people.creator)
    obs = _observe(people, rec)
    with pytest.raises(NotFoundError):
        observations.respond(people.other, obs.pk, corrective_action="Not mine")
    with pytest.raises(PermissionDeniedError):
        observations.raise_observation(people.finance, title="t", detail="d", record_id=rec.pk)


def test_an_observation_needs_a_title_detail_and_a_respondent(people, configured):
    with pytest.raises(DomainError) as exc:
        observations.raise_observation(people.auditor, title="", detail="d", record_id=None)
    assert exc.value.code == "observation_incomplete"
    with pytest.raises(DomainError) as exc:
        observations.raise_observation(people.auditor, title="t", detail="d")
    assert exc.value.code == "respondent_required"
    named = observations.raise_observation(people.auditor, title="t", detail="d",
                                           respondent_user_id=102)
    assert named.respondent_user_id == 102 and named.record is None
    with pytest.raises(NotFoundError):
        observations.raise_observation(people.auditor, title="t", detail="d", record_id=9999)


def test_a_response_needs_a_corrective_action(people, configured):
    obs = _observe(people, new_expense(people.creator))
    with pytest.raises(DomainError):
        observations.respond(people.creator, obs.pk, corrective_action=" ")


# ── append-only ledgers and database guards (IAA-BR-301/503) ────────────────────────────

def test_the_trail_notifications_budget_and_policy_rows_are_never_changed_or_deleted(
        people, configured):
    new_expense(people.creator)
    for row in (TrailEntry.objects.first(), Notification.objects.first(),
                BudgetEntry.objects.first(), PolicyVersion.objects.first()):
        row.pk, original = row.pk, row.pk
        with pytest.raises(ValueError):
            row.save()
        with pytest.raises(ValueError):
            row.delete()
        assert type(row).objects.filter(pk=original).exists()


def test_the_database_refuses_nonsense_even_if_the_code_is_bypassed(people, configured):
    rec = new_expense(people.creator)
    with pytest.raises(IntegrityError), transaction.atomic():
        FinancialRecord.objects.filter(pk=rec.pk).update(amount=Decimal("0"))
    with pytest.raises(IntegrityError), transaction.atomic():
        FinancialRecord.objects.filter(pk=rec.pk).update(status="paid")
    review.validate(people.finance, rec.pk)
    with pytest.raises(IntegrityError), transaction.atomic():           # one open step only
        ApprovalStep.objects.create(record=rec, level=5, designation=roles.HOD,
                                    assigned_at=timezone.now())


def test_a_record_can_be_committed_against_the_budget_only_once(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="ok")
    processing.record(people.finance, rec.pk, reference="V")
    with pytest.raises(IntegrityError), transaction.atomic():
        BudgetEntry.objects.create(financial_year=configured, department="CSE",
                                   kind="commitment", amount=Decimal("-1"), record=rec)


# ── configuration (UC-703/704) ──────────────────────────────────────────────────────────

def test_only_the_system_admin_role_can_publish_policy(people, configured):
    finance_with_code = actor(201, roles.FINANCE, permissions=["iaa.configuration.update"])
    with pytest.raises(ConflictError):
        configuration.publish_policy(finance_with_code, POLICY)
    with pytest.raises(PermissionDeniedError):
        configuration.publish_policy(people.creator, POLICY)


def test_an_invalid_policy_is_rejected_with_every_error_and_changes_nothing(people, configured):
    before = PolicyVersion.objects.count()
    with pytest.raises(DomainError) as exc:
        configuration.publish_policy(people.admin, {**POLICY, "approval_timeout_hours": 0,
                                                    "request_types": []})
    assert exc.value.code == "policy_invalid"
    assert {d["field"] for d in exc.value.details} >= {"approval_timeout_hours",
                                                       "request_types"}
    assert PolicyVersion.objects.count() == before


def test_a_policy_cannot_take_effect_in_the_past_but_can_in_the_future(people, configured):
    with pytest.raises(DomainError) as exc:
        configuration.publish_policy(people.admin, POLICY,
                                     effective_from=timezone.now() - timedelta(days=1))
    assert exc.value.code == "backdated_policy"
    future = configuration.publish_policy(people.admin, {**POLICY, "approval_timeout_hours": 5},
                                          effective_from=timezone.now() + timedelta(days=2))
    assert policy_selectors.current_version().pk != future.pk          # not in force yet
    assert policy_selectors.current_version(timezone.now() + timedelta(days=3)).pk == future.pk


def test_the_latest_published_policy_is_the_one_in_force(people, configured):
    newer = configuration.publish_policy(people.admin, {**POLICY, "approval_timeout_hours": 12})
    assert policy_selectors.current_version().pk == newer.pk
    assert PolicyVersion.objects.count() == 2                           # history kept


def test_financial_years_must_be_ordered_unique_and_not_overlapping(people, configured):
    start = configured.ends_on + timedelta(days=1)
    with pytest.raises(DomainError):
        configuration.add_financial_year(people.admin, code="X", starts_on=start,
                                         ends_on=start)
    with pytest.raises(ConflictError) as exc:
        configuration.add_financial_year(people.admin, code="Y", starts_on=configured.starts_on,
                                         ends_on=start)
    assert exc.value.code == "financial_year_overlap"
    configuration.add_financial_year(people.admin, code="2027-28", starts_on=start,
                                     ends_on=start + timedelta(days=364))
    with pytest.raises(ConflictError) as exc:
        configuration.add_financial_year(people.admin, code="2027-28",
                                         starts_on=start + timedelta(days=400),
                                         ends_on=start + timedelta(days=500))
    assert exc.value.code == "duplicate_code"


def test_budget_entries_follow_the_ledger_rules(people, configured):
    year = configured.pk
    add = configuration.add_budget_entry
    with pytest.raises(DomainError):
        add(people.admin, financial_year_id=year, department="CSE", kind="commitment",
            amount=Decimal("-5"))
    with pytest.raises(DomainError):
        add(people.admin, financial_year_id=year, department="CSE", kind="allocation",
            amount=Decimal("-5"))
    with pytest.raises(DomainError):
        add(people.admin, financial_year_id=year, department="CSE", kind="adjustment",
            amount=Decimal("0"))
    with pytest.raises(DomainError):
        add(people.admin, financial_year_id=year, department=" ", kind="allocation",
            amount=Decimal("5"))
    with pytest.raises(DomainError):
        add(people.admin, financial_year_id=9999, department="CSE", kind="allocation",
            amount=Decimal("5"))
    assert add(people.admin, financial_year_id=year, department="ECE", kind="adjustment",
               amount=Decimal("-5")).amount == Decimal("-5")


def test_configuration_changes_are_in_the_trail_with_the_admin_role(people, configured):
    entry = TrailEntry.objects.filter(entity="configuration", action="publish_policy").get()
    assert entry.actor_role == roles.SYSTEM_ADMIN and entry.actor_user_id == 501


# ── notifications (IAA-BR-504) ──────────────────────────────────────────────────────────

def test_submission_notifies_finance_and_the_creator(people, configured):
    rec = new_expense(people.creator)
    assert Notification.objects.filter(recipient_role=roles.FINANCE, kind="submitted",
                                       entity_id=rec.pk).exists()
    assert Notification.objects.filter(recipient_user_id=101, kind="submitted",
                                       entity_id=rec.pk).exists()


def test_validation_hands_the_item_to_the_first_authority_with_a_notification(
        people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    assert Notification.objects.filter(recipient_role=roles.HOD, kind="approval_needed").exists()
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="ok")
    assert Notification.objects.filter(recipient_role=roles.FINANCE,
                                       kind="ready_to_record").exists()
    assert Notification.objects.filter(recipient_user_id=101, kind="approved").exists()
