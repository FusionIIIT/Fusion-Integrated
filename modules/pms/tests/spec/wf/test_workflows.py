"""Workflow scenarios derived from the frozen WF design."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from modules.pms.models import (
    Application,
    AttorneyAssignment,
    BudgetProposal,
    MaintenanceCycle,
    OfficeActionResponse,
    PatentOfficeCommunication,
)
from modules.pms.services import workflows as services
from modules.pms.tests.spec.conftest import case_id

ROOT = Path(__file__).resolve().parents[5]
CASES = json.loads(
    (ROOT / "docs" / "11-pms" / "spec-tests" / "WF_DESIGN.json").read_text(encoding="utf-8")
)
JUSTIFICATION = (
    "The evidence supports this decision and records the reasons for the selected outcome."
)


def submit_then_review(ctx, decision="approved"):
    app = ctx.ready()
    services.submit_application(app.pk, ctx.applicant)
    ctx.director_profile()
    services.assign_director(app.pk, ctx.director, ctx.admin)
    services.review_application(app.pk, ctx.director, decision, JUSTIFICATION)
    app.refresh_from_db()
    return app


def approved_application(ctx):
    return submit_then_review(ctx, "approved")


def office_action_response(ctx, *, review_required):
    app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
    ctx.config("office_action_applicant_review_required", review_required)
    communication = PatentOfficeCommunication.objects.create(
        application=app,
        kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
        external_reference="OA-2026-01",
        received_date=date.today(),
        response_due_date=date.today() + timedelta(days=30),
        deadline_source="Office action notice",
        summary="Respond to the examiner's stated objections.",
        recorded_by_user_id=ctx.attorney,
    )
    attorney = ctx.client(
        user_id=ctx.attorney,
        role="Attorney",
        permissions=("pms.office_action.respond",),
    )
    response = attorney.post(
        f"/api/v1/pms/office-actions/{communication.pk}/responses",
        {"response_text": "The response addresses each objection in the office action."},
        format="json",
    )
    assert response.status_code == 201, response.content
    return app, communication, response.json()["id"], attorney


def run_workflow(case, ctx):
    wid = case["source_id"]
    if wid in {"BW-PMS-01", "CW-PMS-01"}:
        app = submit_then_review(ctx)
        assert app.status == Application.Status.APPROVED
        assert app.transitions.filter(to_status=Application.Status.UNDER_REVIEW).exists()
        assert app.transitions.filter(to_status=Application.Status.APPROVED).exists()
    elif wid == "BW-PMS-02":
        app = submit_then_review(ctx, "needs_revision")
        ctx.ready(app)
        services.resubmit_revision(app.pk, ctx.applicant, "Revised the described claim scope.")
        ctx.director_profile(user_id=ctx.director + 1)
        services.assign_director(app.pk, ctx.director + 1, ctx.admin)
        services.review_application(app.pk, ctx.director + 1, "approved", JUSTIFICATION)
        app.refresh_from_db()
        assert app.status == Application.Status.APPROVED
        assert app.revision_count == 1
    elif wid in {"BW-PMS-03", "BW-PMS-04", "BW-PMS-05"}:
        app = submit_then_review(ctx, "rejected")
        ctx.config("appeal_period_days", 30)
        appeal = services.file_appeal(
            app.pk, ctx.applicant, "The cited prior art differs.", JUSTIFICATION
        )
        outcome = {
            "BW-PMS-03": "remand_for_amendment",
            "BW-PMS-04": "uphold_rejection",
            "BW-PMS-05": "modify_decision",
        }[wid]
        services.decide_appeal(appeal.pk, ctx.director, outcome, JUSTIFICATION)
        app.refresh_from_db()
        expected = {
            "BW-PMS-03": Application.Status.NEEDS_REVISION,
            "BW-PMS-04": Application.Status.REJECTED,
            "BW-PMS-05": Application.Status.APPROVED,
        }[wid]
        assert app.status == expected
        assert app.transitions.filter(action=f"appeal_{outcome}").exists()
    elif wid in {"BW-PMS-06", "BW-PMS-07"}:
        app = approved_application(ctx)
        first = ctx.attorney
        ctx.attorney_profile(user_id=first)
        assignment = services.assign_attorney(app.pk, first, ctx.admin)
        if wid == "BW-PMS-06":
            services.respond_to_attorney_assignment(assignment.pk, first, True)
            assert AttorneyAssignment.objects.get(pk=assignment.pk).status == "accepted"
        else:
            services.respond_to_attorney_assignment(assignment.pk, first, False)
            second = first + 1
            ctx.attorney_profile(user_id=second)
            reassigned = services.assign_attorney(app.pk, second, ctx.admin)
            assert reassigned.attorney_user_id == second
            assert app.attorney_assignments.filter(status="declined").exists()
    elif wid in {"BW-PMS-08", "BW-PMS-09", "BW-PMS-10"}:
        app = approved_application(ctx)
        app.assigned_director_user_id = ctx.director
        app.save(update_fields=["assigned_director_user_id"])
        data = {"filing_fees": "100.00", "attorney_fees": "200.00", "administrative_costs": "50.00"}
        if wid == "BW-PMS-10":
            ctx.config("budget_escalation_threshold", "200.00")
            ctx.config("budget_escalation_user_ids", [ctx.admin + 1])
            data = {
                "filing_fees": "500.00",
                "attorney_fees": "600.00",
                "administrative_costs": "50.00",
            }
        proposal = services.propose_budget(app.pk, ctx.director, data)
        decision = "rejected" if wid == "BW-PMS-09" else "approved"
        row = services.decide_budget(proposal.pk, ctx.director, decision, JUSTIFICATION)
        expected = {
            "BW-PMS-08": BudgetProposal.Status.APPROVED,
            "BW-PMS-09": BudgetProposal.Status.REJECTED,
            "BW-PMS-10": BudgetProposal.Status.ESCALATED,
        }[wid]
        assert row.status == expected
    elif wid == "BW-PMS-11":
        app = approved_application(ctx)
        ctx.attorney_profile()
        assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, True)
        budget = services.propose_budget(
            app.pk,
            ctx.director,
            {"filing_fees": "100.00", "attorney_fees": "200.00", "administrative_costs": "50.00"},
        )
        services.decide_budget(budget.pk, ctx.director, "approved", JUSTIFICATION)
        filing = services.record_filing(
            app.pk,
            ctx.attorney,
            jurisdiction="India",
            external_filing_id="IPO-2026-1",
            filing_date=date.today(),
            confirmation_reference="receipt-1",
        )
        app.refresh_from_db()
        assert filing.external_filing_id == "IPO-2026-1"
        assert app.status == Application.Status.FILED
    elif wid == "BW-PMS-12":
        app, _communication, response_id, attorney = office_action_response(
            ctx, review_required=True
        )
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.office_action_response.review",),
            kind="student",
        )
        approved = applicant.post(
            f"/api/v1/pms/office-action-responses/{response_id}/approval",
            {"approved": True},
            format="json",
        )
        assert approved.status_code == 200, approved.content
        submitted = attorney.post(
            f"/api/v1/pms/office-action-responses/{response_id}/submission",
            {"external_submission_reference": "RESP-2026-01"},
            format="json",
        )
        assert submitted.status_code == 200, submitted.content
        assert submitted.json()["status"] == OfficeActionResponse.Status.SUBMITTED
    elif wid == "BW-PMS-13":
        app, _communication, response_id, attorney = office_action_response(
            ctx, review_required=False
        )
        submitted = attorney.post(
            f"/api/v1/pms/office-action-responses/{response_id}/submission",
            {"external_submission_reference": "RESP-2026-02"},
            format="json",
        )
        assert submitted.status_code == 200, submitted.content
        assert submitted.json()["status"] == OfficeActionResponse.Status.SUBMITTED
    elif wid in {"BW-PMS-14", "BW-PMS-15", "CW-PMS-04"}:
        app = ctx.app(
            status=Application.Status.GRANTED,
            assigned_attorney_user_id=ctx.attorney,
            assigned_director_user_id=ctx.director,
        )
        cycle = MaintenanceCycle.objects.create(
            application=app,
            jurisdiction="India",
            due_date=date.today() + timedelta(days=30),
            schedule_source="Configured India schedule",
        )
        attorney = ctx.client(
            user_id=ctx.attorney, role="Attorney", permissions=("pms.maintenance.manage",)
        )
        requested = attorney.post(
            f"/api/v1/pms/maintenance-cycles/{cycle.pk}/request-decision", {}, format="json"
        )
        assert requested.status_code == 200, requested.content
        director = ctx.client(
            user_id=ctx.director, role="Director", permissions=("pms.maintenance.decide",)
        )
        decision = "renew" if wid in {"BW-PMS-14", "CW-PMS-04"} else "do_not_renew"
        decided = director.post(
            f"/api/v1/pms/maintenance-cycles/{cycle.pk}/decision",
            {"decision": decision},
            format="json",
        )
        assert decided.status_code == 200, decided.content
        cycle.refresh_from_db()
        if decision == "renew":
            acted = attorney.post(
                f"/api/v1/pms/maintenance-cycles/{cycle.pk}/record-action",
                {
                    "transaction_reference": "PAY-2026-1",
                    "next_cycle_due_date": str(date.today() + timedelta(days=365)),
                },
                format="json",
            )
            assert acted.status_code == 200, acted.content
            assert MaintenanceCycle.objects.filter(application=app).count() == 2
        else:
            assert cycle.status == MaintenanceCycle.Status.DO_NOT_RENEW
    elif wid in {"BW-PMS-16", "CW-PMS-05"}:
        app = ctx.ready()
        ctx.config("withdrawal_eligible_statuses", [Application.Status.DRAFT])
        withdrawn = services.withdraw_application(
            app.pk, ctx.applicant, "The inventor team withdrew the proposal."
        )
        assert withdrawn.status == Application.Status.WITHDRAWN
        assert withdrawn.transitions.filter(action="application_withdrawn").exists()
    elif wid in {"CW-PMS-02", "CW-PMS-03"}:
        if wid == "CW-PMS-02":
            run_workflow({"source_id": "BW-PMS-11"}, ctx)
        else:
            run_workflow({"source_id": "BW-PMS-12"}, ctx)
    else:
        pytest.skip(f"NOT_AUTOMATED: no test adapter exists for workflow {wid} in this baseline.")


@pytest.mark.django_db
def test_frozen_workflow_cases(case, pms_ctx):
    """Each pytest node carries the frozen test_id and exact WF source_id."""
    run_workflow(case, pms_ctx)


test_frozen_workflow_cases = pytest.mark.parametrize("case", CASES, ids=case_id)(
    test_frozen_workflow_cases
)
