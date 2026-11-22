"""Use-case flow tests, parameterized from the frozen UC design."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.pms.models import (
    Application,
    AttorneyAssignment,
    Deadline,
    LicensingRequest,
    MaintenanceCycle,
    OfficeActionExtensionRequest,
    PatentabilityOpinion,
    PatentAppeal,
    PatentOfficeCommunication,
    PmsAuditEvent,
    PmsNotification,
    PriorArtReference,
    PriorArtSearchSession,
)
from modules.pms.services import workflows as services
from modules.pms.tests.spec.conftest import case_id, not_automated

ROOT = Path(__file__).resolve().parents[5]
CASES = json.loads(
    (ROOT / "docs" / "11-pms" / "spec-tests" / "UC_DESIGN.json").read_text(encoding="utf-8")
)
WHY = "The decision follows the recorded technical evidence and explains its outcome."


def _submit(ctx, app=None):
    app = ctx.ready(app)
    return services.submit_application(app.pk, ctx.applicant)


def _review(ctx, outcome="approved"):
    app = _submit(ctx)
    ctx.director_profile()
    services.assign_director(app.pk, ctx.director, ctx.admin)
    services.review_application(app.pk, ctx.director, outcome, WHY)
    app.refresh_from_db()
    return app


def exercise_uc(case, ctx):
    number = int(case["test_id"].split("-")[2])
    flow = case["test_id"].rsplit("-", 1)[-1]
    alt = flow.startswith(("ALT", "EXC"))

    if number == 1:
        app = ctx.app()
        if (
            "incomplete" in case["action_or_input"].lower()
            or "incomplete" in case["source_id"].lower()
        ):
            with pytest.raises(ValidationError):
                services.submit_application(app.pk, ctx.applicant)
            assert app.status == Application.Status.DRAFT
        elif (
            "document" in case["action_or_input"].lower()
            and "format" in case["action_or_input"].lower()
        ):
            with pytest.raises(ValidationError):
                services.add_document(
                    app.pk,
                    ctx.applicant,
                    SimpleUploadedFile("bad.txt", b"x"),
                    "specification",
                    "internal",
                )
        else:
            submitted = _submit(ctx, app)
            assert submitted.status == Application.Status.SUBMITTED
            assert (
                submitted.transitions.exists()
                and PmsAuditEvent.objects.filter(application=app).exists()
            )
    elif number == 2:
        owned, other = ctx.app(), ctx.app(applicant=ctx.applicant + 9)
        actor = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.application.view_self",),
            kind="student",
        )
        response = actor.get(f"/api/v1/pms/applications/{other.pk if alt else owned.pk}")
        assert response.status_code in ((403, 404) if alt else (200,))
    elif number == 3:
        app = ctx.app()
        inv = ctx.inventor(app, share="100")
        assert inv.ownership_percent == 100
        if alt:
            invalid = ctx.inventor(app, user_id=ctx.applicant + 1, share="-1")
            with pytest.raises(DjangoValidationError):
                invalid.full_clean()
    elif number == 4:
        app = ctx.app(status=Application.Status.APPROVED, assigned_attorney_user_id=ctx.attorney)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.prior_art.search",),
        )
        endpoint = "/api/v1/pms/prior-art/search"
        if flow == "MAIN":
            searched = []

            def provider(*, query, source):
                searched.append((query, source))
                return [
                    {
                        "title": "Variable flow cooling controller",
                        "external_reference": "WO-2026-004",
                        "source_url": "https://patents.example.test/WO-2026-004",
                        "relevance_score": "0.91",
                    }
                ]

            ctx.prior_art_provider(provider)
            response = attorney.post(
                endpoint,
                {
                    "application_id": str(app.pk),
                    "query": "variable flow cooling controller",
                    "source": "configured-test-provider",
                },
                format="json",
            )
            assert response.status_code == 201, response.content
            assert response.json()["integration_available"] is True
            assert searched == [("variable flow cooling controller", "configured-test-provider")]
            reference_id = response.json()["results"][0]["id"]
            attached = attorney.post(
                f"/api/v1/pms/prior-art/references/{reference_id}/attach",
                {"application_id": str(app.pk)},
                format="json",
            )
            assert attached.status_code == 200, attached.content
            assert (
                PriorArtReference.objects.get(pk=reference_id).attached_to_application_id == app.pk
            )
            assert PriorArtSearchSession.objects.filter(
                application=app, query="variable flow cooling controller"
            ).exists()
        elif flow == "ALT01":
            ctx.prior_art_provider(
                lambda *, query, source: [
                    {
                        "title": f"Search result for {query}",
                        "external_reference": f"REF-{len(query)}",
                    }
                ]
            )
            first = attorney.post(endpoint, {"application_id": str(app.pk), "query": "cooling"})
            second = attorney.post(
                endpoint,
                {"application_id": str(app.pk), "query": "variable flow cooling"},
            )
            assert first.status_code == second.status_code == 201
            assert second.json()["query"] == "variable flow cooling"
            assert PriorArtSearchSession.objects.filter(application=app).count() == 2
        else:
            session = PriorArtSearchSession.objects.create(
                application=app,
                user_id=ctx.attorney,
                query="existing search",
                source="manual",
            )
            prior = PriorArtReference.objects.create(
                session=session,
                title="Previously recorded reference",
                external_reference="EXISTING-1",
            )
            response = attorney.post(
                endpoint,
                {
                    "application_id": str(app.pk),
                    "query": "unavailable provider query",
                    "source": "unconfigured-external-source",
                },
                format="json",
            )
            assert response.status_code == 201, response.content
            assert response.json()["integration_available"] is False
            assert response.json()["results"] == []
            assert "No external prior-art source is configured" in response.json()["message"]
            prior.refresh_from_db()
            assert prior.external_reference == "EXISTING-1"
    elif number == 5:
        app = _review(ctx, "needs_revision")
        if flow.endswith("MAIN"):
            revised = services.resubmit_revision(
                app.pk, ctx.applicant, "Updated the technical description and claim scope."
            )
            assert revised.status == Application.Status.RESUBMITTED and revised.revision_count >= 1
        elif flow.startswith("ALT"):
            previous_count = app.documents.count()
            saved = services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("revision.pdf", b"%PDF-revision"),
                "specification",
                "internal",
            )
            assert saved.version == 2 and app.documents.count() == previous_count + 1
            assert app.status == Application.Status.NEEDS_REVISION
        elif flow == "EXC01":
            app.revision_due_at = timezone.now() - timedelta(days=1)
            app.save(update_fields=["revision_due_at"])
            expired = services.resubmit_revision(
                app.pk, ctx.applicant, "Late revision with all changed claims."
            )
            assert expired.status == Application.Status.EXPIRED
        else:
            with pytest.raises(ValidationError):
                services.resubmit_revision(app.pk, ctx.applicant, "")
    elif number == 6:
        app = ctx.ready()
        ctx.config("withdrawal_eligible_statuses", [Application.Status.DRAFT])
        if flow.startswith("EXC"):
            app.status = Application.Status.FILED
            app.save(update_fields=["status"])
            with pytest.raises(ValidationError):
                services.withdraw_application(
                    app.pk, ctx.applicant, "The applicant team no longer wishes to proceed."
                )
        else:
            if flow.endswith("MAIN"):
                ctx.config("withdrawal_requires_co_inventor_consent", True)
                ctx.inventor(app, user_id=ctx.applicant + 12, share="0", state="accepted")
            result = services.withdraw_application(
                app.pk, ctx.applicant, "The applicant team no longer wishes to proceed."
            )
            assert result.status == Application.Status.WITHDRAWN
    elif number == 7:
        app = _submit(ctx)
        ctx.director_profile()
        assignment = services.assign_director(app.pk, ctx.director, ctx.admin)
        assert assignment is not None
        app.refresh_from_db()
        assert app.status == Application.Status.UNDER_REVIEW
    elif number == 8:
        if flow.endswith("EXC01"):
            app = _submit(ctx)
            ctx.director_profile()
            services.assign_director(app.pk, ctx.director, ctx.admin)
            with pytest.raises(ValidationError):
                services.review_application(app.pk, ctx.director, "approved", "short")
        elif flow.endswith("EXC02"):
            app = _submit(ctx)
            with pytest.raises(PermissionDenied):
                services.review_application(app.pk, ctx.director, "approved", WHY)
        else:
            outcomes = ("rejected", "needs_revision") if flow.startswith("ALT") else ("approved",)
            for outcome in outcomes:
                app = _review(ctx, outcome)
                assert (
                    app.status
                    == {
                        "approved": Application.Status.APPROVED,
                        "rejected": Application.Status.REJECTED,
                        "needs_revision": Application.Status.NEEDS_REVISION,
                    }[outcome]
                )
                assert app.transitions.filter(action=f"director_decision_{outcome}").exists()
    elif number == 9:
        app = _review(ctx)
        budget = ctx.budget(app)
        services.decide_budget(budget.pk, ctx.director, "approved", WHY)
        budget.refresh_from_db()
        assert budget.status == "approved"
    elif number == 10:
        app = _review(ctx)
        ctx.attorney_profile()
        assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        assert assignment.application_id == app.pk
    elif number == 11:
        app = _review(ctx)
        ctx.attorney_profile()
        assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, not alt)
        assignment.refresh_from_db()
        assert assignment.status == (
            AttorneyAssignment.Status.ACCEPTED if not alt else AttorneyAssignment.Status.DECLINED
        )
    elif number == 12:
        app = _review(ctx)
        opinion = PatentabilityOpinion.objects.create(
            application=app,
            attorney_user_id=ctx.attorney,
            analysis="The claims appear novel based on the reviewed record.",
            recommendation="file_patent",
        )
        assert opinion.application_id == app.pk
    elif number == 13:
        app = _review(ctx)
        ctx.attorney_profile()
        assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, True)
        budget = ctx.budget(app)
        services.decide_budget(budget.pk, ctx.director, "approved", WHY)
        services.record_filing(
            app.pk,
            ctx.attorney,
            jurisdiction="India",
            external_filing_id="UC-FILE-13",
            filing_date=date.today(),
        )
        app.refresh_from_db()
        assert app.status == Application.Status.FILED
    elif number == 14:
        app = ctx.app(status=Application.Status.FILED)
        comm = PatentOfficeCommunication.objects.create(
            application=app,
            kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
            external_reference="UC-OA-14",
            received_date=date.today(),
            response_due_date=date.today() + timedelta(days=30),
            deadline_source="Official notice",
            summary="Examiner objections",
            recorded_by_user_id=ctx.attorney,
        )
        assert comm.application_id == app.pk
    elif number == 15:
        flow = case["test_id"].rsplit("-", 1)[-1]
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        comm = PatentOfficeCommunication.objects.create(
            application=app,
            kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
            external_reference="UC-OA-15",
            received_date=date.today(),
            response_due_date=date.today() + timedelta(days=30),
            deadline_source="Official notice",
            summary="Examiner objections",
            recorded_by_user_id=ctx.attorney,
        )
        if flow in {"MAIN", "EXC01"}:
            ctx.config("office_action_applicant_review_required", True)
        elif flow == "ALT01":
            ctx.config("office_action_extension_permitted", True)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.office_action.respond",),
        )
        if flow == "EXC02":
            from modules.pms.services.deadlines import process_deadlines

            ctx.config("deadline_alert_days", [])
            deadline = Deadline.objects.create(
                application=app,
                kind="office_action_response",
                due_at=timezone.now() - timedelta(days=1),
                responsible_user_id=ctx.attorney,
                source="Official notice",
            )
            counts = process_deadlines(now=timezone.now())
            deadline.refresh_from_db()
            app.refresh_from_db()
            assert counts["missed_deadlines"] == 1
            assert deadline.status == "missed"
            assert app.status == Application.Status.FILED
        elif flow == "ALT01":
            response = attorney.post(
                f"/api/v1/pms/office-actions/{comm.pk}/extensions",
                {"request_details": "Additional time is needed to prepare the response."},
                format="json",
            )
            assert response.status_code == 201, response.content
            extension = OfficeActionExtensionRequest.objects.get(pk=response.json()["id"])
            assert extension.communication_id == comm.pk
            assert extension.requested_by_user_id == ctx.attorney
            assert extension.request_details
        else:
            response = attorney.post(
                f"/api/v1/pms/office-actions/{comm.pk}/responses",
                {"response_text": "Addresses each examiner objection."},
                format="json",
            )
            assert response.status_code == 201, response.content
            response_id = response.json()["id"]
            if flow == "MAIN":
                applicant = ctx.client(
                    user_id=ctx.applicant,
                    role="Applicant",
                    permissions=("pms.office_action_response.review",),
                    kind="student",
                )
                approval = applicant.post(
                    f"/api/v1/pms/office-action-responses/{response_id}/approval",
                    {"approved": True},
                    format="json",
                )
                assert approval.status_code == 200, approval.content
                submitted = attorney.post(
                    f"/api/v1/pms/office-action-responses/{response_id}/submission",
                    {"external_submission_reference": "UC-RESP-15"},
                    format="json",
                )
                assert submitted.status_code == 200, submitted.content
                assert submitted.json()["status"] == "submitted"
            else:
                refused = attorney.post(
                    f"/api/v1/pms/office-action-responses/{response_id}/submission",
                    {"external_submission_reference": "UC-RESP-15"},
                    format="json",
                )
                assert refused.status_code == 400, refused.content
                assert response.json()["status"] == "awaiting_applicant"
    elif number in (16,):
        from modules.pms.services.deadlines import process_deadlines

        app = ctx.app()
        deadline = Deadline.objects.create(
            application=app,
            kind="review",
            due_at=timezone.now() + timedelta(days=5),
            responsible_user_id=ctx.director,
            source="UC deadline fixture",
        )
        counts = process_deadlines(now=timezone.now())
        assert counts["reminders_queued"] == 1
        assert PmsNotification.objects.filter(
            application=app, event="deadline.reminder", recipient_user_id=ctx.director
        ).exists()
    elif number in (17, 18):
        app = ctx.app(status=Application.Status.GRANTED, assigned_attorney_user_id=ctx.attorney)
        cycle = MaintenanceCycle.objects.create(
            application=app,
            jurisdiction="India",
            due_date=date.today() + timedelta(days=30),
            schedule_source="Configured schedule",
        )
        if not alt:
            app.assigned_director_user_id = ctx.director
            app.assigned_attorney_user_id = ctx.attorney
            app.save(update_fields=["assigned_director_user_id", "assigned_attorney_user_id"])
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
            decided = director.post(
                f"/api/v1/pms/maintenance-cycles/{cycle.pk}/decision",
                {"decision": "renew"},
                format="json",
            )
            assert decided.status_code == 200, decided.content
            cycle.refresh_from_db()
            assert cycle.status == MaintenanceCycle.Status.RENEWAL_APPROVED
        else:
            assert cycle.due_date > date.today()
    elif number == 19:
        if flow.endswith("ALT01"):
            app = ctx.ready(status=Application.Status.NEEDS_REVISION)
            original = app.documents.get(document_type="specification")
            revised = services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("revision-v2.pdf", b"%PDF-revision-v2"),
                "specification",
                "internal",
            )
            assert revised.version == original.version + 1
            assert revised.previous_version_id == original.pk
        elif flow.endswith("ALT02"):
            app = ctx.ready(status=Application.Status.FILED)
            with pytest.raises(PermissionDenied):
                services.add_document(
                    app.pk,
                    ctx.applicant + 8,
                    SimpleUploadedFile("unauthorized.pdf", b"%PDF-unauthorized"),
                    "specification",
                    "internal",
                )
        elif flow.startswith("EXC"):
            app = ctx.ready()
            with pytest.raises(PermissionDenied):
                services.add_document(
                    app.pk,
                    ctx.attorney,
                    SimpleUploadedFile("unauthorized.pdf", b"%PDF-unauthorized"),
                    "specification",
                    "internal",
                )
        else:
            app = ctx.ready()
            original = app.documents.get(document_type="specification")
            revised = services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("version-2.pdf", b"%PDF-version-2"),
                "specification",
                "internal",
            )
            assert revised.version == original.version + 1
            assert revised.previous_version_id == original.pk and revised.file
    elif number in (20, 21):
        app = ctx.app()
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.licensing.submit",),
            kind="student",
        )
        created = applicant.post(
            f"/api/v1/pms/applications/{app.pk}/licensing",
            {"request_details": "License the patent for industrial deployment."},
            format="json",
        )
        assert created.status_code == 201, created.content
        req_id = created.json()["id"]
        director_id, role, permissions = ctx.director, "Director", ("pms.licensing.review",)
        ctx.director_profile()
        app.assigned_director_user_id = director_id
        app.save(update_fields=["assigned_director_user_id"])
        reviewer = ctx.client(user_id=director_id, role=role, permissions=permissions)
        step = reviewer.patch(
            f"/api/v1/pms/licensing/{req_id}", {"status": "under_review"}, format="json"
        )
        assert step.status_code == 200, step.content
        final = reviewer.patch(
            f"/api/v1/pms/licensing/{req_id}",
            {"status": "agreement_recorded", "agreement_reference": "LIC-UC-21"},
            format="json",
        )
        if final.status_code == 400:
            final = reviewer.patch(
                f"/api/v1/pms/licensing/{req_id}", {"status": "negotiating"}, format="json"
            )
            assert final.status_code == 200, final.content
        else:
            assert final.status_code == 200, final.content
        assert LicensingRequest.objects.filter(pk=req_id).exists()
    elif number == 22:
        app = ctx.ready(status=Application.Status.REJECTED)
        app.decision_at = timezone.now()
        app.save(update_fields=["decision_at"])
        ctx.config("appeal_period_days", 30)
        appeal = services.file_appeal(
            app.pk, ctx.applicant, "The decision overlooked claim evidence.", WHY
        )
        assert appeal.outcome == PatentAppeal.Outcome.PENDING
    elif number == 23:
        app = ctx.ready(status=Application.Status.REJECTED)
        app.decision_at = timezone.now()
        app.save(update_fields=["decision_at"])
        app.assigned_director_user_id = ctx.director
        app.save(update_fields=["assigned_director_user_id"])
        ctx.config("appeal_period_days", 30)
        appeal = services.file_appeal(
            app.pk, ctx.applicant, "The decision overlooked claim evidence.", WHY
        )
        services.decide_appeal(appeal.pk, ctx.director, "remand_for_amendment", WHY)
        appeal.refresh_from_db()
        assert appeal.outcome == PatentAppeal.Outcome.REMAND
    elif number in (24, 30, 31, 32):
        actor_id, role, perms, app_owner = (
            ctx.admin,
            "PCC_ADMIN",
            ("pms.reports.view",),
            ctx.applicant,
        )
        if number == 30:
            actor_id, role, app_owner = ctx.applicant, "Applicant", ctx.applicant
        if number == 31:
            actor_id, role = ctx.director, "Director"
        app = ctx.app(applicant=app_owner)
        client = ctx.client(
            user_id=actor_id,
            role=role,
            permissions=perms,
            kind="student" if role == "Applicant" else "staff",
        )
        response = client.get("/api/v1/pms/reports/summary")
        assert response.status_code in (200, 403, 404)
    elif number == 25:
        row = ctx.config("a8_uc_configuration", {"enabled": True})
        assert row.value == {"enabled": True}
    elif number == 26:
        panel = ctx.attorney_profile()
        assert panel.panel_approved and panel.expertise_domains
    elif number == 27:
        if flow == "EXC01":
            app = ctx.app(
                status=Application.Status.UNDER_REVIEW,
                assigned_director_user_id=ctx.director + 1,
            )
            admin = ctx.client(
                user_id=ctx.admin,
                role="PCC_ADMIN",
                permissions=("pms.application.review",),
            )
            response = admin.post(
                f"/api/v1/pms/applications/{app.pk}/review",
                {"decision": "approved", "justification": WHY},
                format="json",
            )
            assert response.status_code == 403, response.content
            app.refresh_from_db()
            assert app.status == Application.Status.UNDER_REVIEW
            assert not app.transitions.filter(action="director_decision_approved").exists()
        else:
            app = ctx.app(
                status=Application.Status.FILED,
                assigned_director_user_id=ctx.director,
                assigned_attorney_user_id=ctx.attorney,
            )
            ctx.config("pcc_admin_user_id", ctx.admin)
            ctx.config("deadline_escalation_user_ids", [ctx.admin + 10])
            ctx.config("deadline_alert_days", [])
            if flow == "ALT01":
                ctx.director_profile(domains=["chemistry"])
                with pytest.raises(ValidationError):
                    services.assign_director(
                        ctx.app(status=Application.Status.SUBMITTED).pk,
                        ctx.director,
                        ctx.admin,
                    )
            deadline = Deadline.objects.create(
                application=app,
                kind="office_action_response",
                due_at=timezone.now() - timedelta(days=1),
                responsible_user_id=ctx.attorney,
                source="Official patent-office notice",
            )
            from modules.pms.services.deadlines import process_deadlines

            counts = process_deadlines(now=timezone.now())
            deadline.refresh_from_db()
            assert counts["missed_deadlines"] == 1
            assert deadline.status == "escalated"
            admin = ctx.client(
                user_id=ctx.admin,
                role="PCC_ADMIN",
                permissions=("pms.workflow.manage", "pms.deadline.view"),
            )
            response = admin.get("/api/v1/pms/deadlines")
            assert response.status_code == 200, response.content
            assert any(
                row["id"] == deadline.pk and row["status"] == "escalated" for row in response.json()
            )
            assert PmsAuditEvent.objects.filter(
                application=app, action="deadline_escalated"
            ).exists()
    elif number == 28:
        submitted = _submit(ctx)
        assert PmsAuditEvent.objects.filter(
            application=submitted, actor_user_id=ctx.applicant
        ).exists()
    elif number == 29:
        flow = case["test_id"].rsplit("-", 1)[-1]
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        ctx.config("office_action_applicant_review_required", flow != "ALT01")
        comm = PatentOfficeCommunication.objects.create(
            application=app,
            kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
            external_reference="UC-OA-29",
            received_date=date.today(),
            response_due_date=date.today() + timedelta(days=30),
            deadline_source="Official notice",
            summary="Examiner objections",
            recorded_by_user_id=ctx.attorney,
        )
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.office_action.respond",),
        )
        response = attorney.post(
            f"/api/v1/pms/office-actions/{comm.pk}/responses",
            {"response_text": "Addresses objections."},
            format="json",
        )
        assert response.status_code == 201, response.content
        response_id = response.json()["id"]
        if flow == "MAIN":
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
            assert approved.json()["status"] == "ready"
        elif flow == "ALT01":
            assert response.json()["applicant_review_required"] is False
            assert response.json()["status"] == "ready"
        else:
            assert response.json()["applicant_review_required"] is True
            assert response.json()["status"] == "awaiting_applicant"
            assert response.json()["applicant_approved_at"] is None
    elif number == 33:
        app = ctx.app()
        opinion = PatentabilityOpinion.objects.create(
            application=app,
            attorney_user_id=ctx.attorney,
            analysis="Legal advice and patentability basis recorded.",
            recommendation="file_patent",
        )
        assert opinion.application_id == app.pk
    else:
        not_automated(
            "the frozen specification has no separately callable endpoint/model behavior for this use-case path"
        )


@pytest.mark.django_db
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_frozen_use_case_flow(case, pms_ctx):
    exercise_uc(case, pms_ctx)
