"""Atomic requirement tests from the frozen FR design."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.pms.models import (
    Application,
    ApplicationDocument,
    BudgetProposal,
    Deadline,
    LicensingRequest,
    MaintenanceCycle,
    OfficeActionExtensionRequest,
    OfficeActionResponse,
    PatentAppeal,
    PatentFiling,
    PatentOfficeCommunication,
    PmsAuditEvent,
    PmsConfiguration,
    PmsNotification,
    PmsReportSchedule,
    PriorArtReference,
    PriorArtSearchSession,
)
from modules.pms.services import workflows as services
from modules.pms.tests.spec.conftest import case_id, not_automated

ROOT = Path(__file__).resolve().parents[5]
CASES = json.loads(
    (ROOT / "docs" / "11-pms" / "spec-tests" / "FR_DESIGN.json").read_text(encoding="utf-8")
)
JUSTIFICATION = "The available evidence supports this decision and explains the selected outcome."


def submit(ctx, app=None):
    app = ctx.ready(app)
    return services.submit_application(app.pk, ctx.applicant)


def director_assignment(ctx, app=None, *, director=None):
    app = submit(ctx, app)
    director = director or ctx.director
    ctx.director_profile(user_id=director)
    return services.assign_director(app.pk, director, ctx.admin)


def approved(ctx, app=None):
    app = director_assignment(ctx, app)
    services.review_application(app.pk, ctx.director, "approved", JUSTIFICATION)
    app.refresh_from_db()
    return app


def prepare_for_filing(ctx):
    app = approved(ctx)
    ctx.attorney_profile()
    assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
    services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, True)
    budget = services.propose_budget(
        app.pk,
        ctx.director,
        {"filing_fees": "100.00", "attorney_fees": "200.00", "administrative_costs": "50.00"},
    )
    services.decide_budget(budget.pk, ctx.director, "approved", JUSTIFICATION)
    return app


def exercise_fr(case, ctx):
    sid = case["source_id"]
    number = int(sid.rsplit("-", 1)[1])

    # Application tracking, reporting, administration, and legal review.
    if number == 10:
        app = submit(ctx)
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.application.view_self",),
            kind="student",
        )
        detail = applicant.get(f"/api/v1/pms/applications/{app.pk}")
        history = applicant.get(f"/api/v1/pms/applications/{app.pk}/history")
        assert detail.status_code == history.status_code == 200
        assert detail.json()["status"] == Application.Status.SUBMITTED
        assert any(item["action"] == "application_submitted" for item in history.json())
    elif number == 16:
        owned = ctx.app()
        ctx.app(applicant=ctx.applicant + 1)
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.report.view_self",),
            kind="student",
        )
        response = applicant.get("/api/v1/pms/reports")
        assert response.status_code == 200, response.content
        assert response.json()["total"] == 1
        assert [row["id"] for row in response.json()["applications"]] == [str(owned.pk)]
    elif number == 23:
        owned = director_assignment(ctx)
        other = ctx.app(applicant=ctx.admin)
        ctx.ready(other)
        services.submit_application(other.pk, ctx.admin)
        ctx.director_profile(user_id=ctx.director + 1)
        services.assign_director(other.pk, ctx.director + 1, ctx.admin)
        other.refresh_from_db()
        director = ctx.client(
            user_id=ctx.director,
            role="Director",
            permissions=("pms.application.review", "pms.report.view"),
        )
        response = director.get("/api/v1/pms/reports")
        assert response.status_code == 200, response.content
        assert response.json()["total"] == 1
        assert response.json()["applications"][0]["id"] == str(owned.pk)
    elif number == 26:
        app = submit(ctx)
        ctx.config("pcc_admin_user_id", ctx.admin)
        ctx.director_profile(user_id=ctx.admin)
        ctx.inventor(app, user_id=ctx.admin)
        admin = ctx.client(
            user_id=ctx.admin,
            role="PCC_ADMIN",
            permissions=("pms.workflow.manage", "pms.workflow.assign_director", "pms.report.view"),
        )
        blocked = admin.post(
            f"/api/v1/pms/applications/{app.pk}/assign-director",
            {"director_user_id": ctx.admin},
            format="json",
        )
        assert blocked.status_code == 400, blocked.content
        report = admin.get("/api/v1/pms/reports")
        assert report.status_code == 200, report.content
        assert report.json()["total"] >= 1
    elif number == 27:
        ctx.config("pcc_admin_user_id", ctx.admin)
        admin = ctx.client(
            user_id=ctx.admin,
            role="PCC_ADMIN",
            permissions=("pms.configuration.manage",),
        )
        updated = admin.put(
            "/api/v1/pms/configuration",
            {"key": "deadline_alert_days", "value": [14, 7]},
            format="json",
        )
        assert updated.status_code == 200, updated.content
        assert PmsConfiguration.objects.get(key="deadline_alert_days").value == [14, 7]
    elif number == 29:
        app = ctx.app(status=Application.Status.FILED)
        ctx.config("deadline_alert_days", [])
        ctx.config("deadline_escalation_user_ids", [ctx.admin + 1])
        deadline = Deadline.objects.create(
            application=app,
            kind="office_action_response",
            due_at=timezone.now() - timedelta(days=1),
            responsible_user_id=ctx.attorney,
            source="Official notice",
        )
        from modules.pms.services.deadlines import process_deadlines

        counts = process_deadlines(now=timezone.now())
        deadline.refresh_from_db()
        assert counts["missed_deadlines"] == 1
        assert deadline.status == "escalated"
        assert PmsAuditEvent.objects.filter(application=app, action="deadline_escalated").exists()
    elif number == 30:
        ctx.config("pcc_admin_user_id", ctx.admin)
        profile = ctx.attorney_profile(domains=["mechanical engineering", "thermal systems"])
        admin = ctx.client(
            user_id=ctx.admin,
            role="PCC_ADMIN",
            permissions=("pms.panel.manage",),
        )
        response = admin.get("/api/v1/pms/panel")
        assert response.status_code == 200, response.content
        assert any(row["user_id"] == profile.user_id for row in response.json()["attorneys"])
    elif number == 37:
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.legal_opinion.create",),
        )
        response = attorney.post(
            f"/api/v1/pms/applications/{app.pk}/legal-advice",
            {
                "advice": "The claim appears novel over the reviewed references.",
                "lifecycle_stage": "filed",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert app.legal_advice.filter(attorney_user_id=ctx.attorney).exists()
    elif number == 50:
        app = submit(ctx)
        assert app.assigned_director_user_id is None
        assert not app.transitions.filter(action="director_assigned").exists()
    elif number == 55:
        app = submit(ctx)
        ctx.config("pcc_admin_user_id", ctx.admin)
        ctx.director_profile(user_id=ctx.admin)
        ctx.inventor(app, user_id=ctx.admin)
        admin = ctx.client(
            user_id=ctx.admin,
            role="PCC_ADMIN",
            permissions=("pms.workflow.assign_director",),
        )
        response = admin.post(
            f"/api/v1/pms/applications/{app.pk}/assign-director",
            {"director_user_id": ctx.admin},
            format="json",
        )
        assert response.status_code == 400, response.content
        app.refresh_from_db()
        assert app.assigned_director_user_id is None
        assert app.status == Application.Status.SUBMITTED

    # Application submission, validation, history, and notification.
    elif number == 38:
        app = submit(ctx)
        assert app.status == Application.Status.SUBMITTED
    elif number == 39:
        app = ctx.app()
        bad = SimpleUploadedFile("notes.txt", b"not a PDF", content_type="text/plain")
        with pytest.raises(ValidationError):
            services.add_document(app.pk, ctx.applicant, bad, "specification", "internal")
    elif number == 40:
        app = ctx.app()
        large = SimpleUploadedFile("large.pdf", b"%PDF-" + b"x" * (50 * 1024 * 1024))
        with pytest.raises(ValidationError):
            services.add_document(app.pk, ctx.applicant, large, "specification", "internal")
    elif number == 41:
        app = ctx.app()
        ctx.inventor(app)
        ctx.document(app, status="infected")
        with pytest.raises(ValidationError):
            services.submit_application(app.pk, ctx.applicant)
    elif number == 42:
        app = ctx.app(title="", abstract="")
        ctx.ready(app)
        with pytest.raises(ValidationError):
            services.submit_application(app.pk, ctx.applicant)
    elif number == 43:
        app = ctx.app()
        doc = ApplicationDocument.objects.create(
            application=app,
            uploaded_by_user_id=ctx.applicant,
            document_type="specification",
            sensitivity="confidential",
            file="pms/test/classified.pdf",
            original_filename="classified.pdf",
            content_type="application/pdf",
            size_bytes=12,
            malware_scan_status="clean",
        )
        assert doc.sensitivity == ApplicationDocument.Sensitivity.CONFIDENTIAL
    elif number == 44:
        first, second = ctx.app(), ctx.app()
        assert first.application_number and second.application_number
        assert first.application_number != second.application_number
    elif number == 45:
        app = submit(ctx)
        assert app.status == Application.Status.SUBMITTED
    elif number == 46:
        app = prepare_for_filing(ctx)
        pending = ctx.inventor(app, user_id=ctx.applicant + 5, share="0", state="pending")
        with pytest.raises(ValidationError):
            services.record_filing(
                app.pk,
                ctx.attorney,
                jurisdiction="India",
                external_filing_id="F-46",
                filing_date=date.today(),
            )
        assert pending.agreement_status == "pending"
    elif number == 47:
        app = submit(ctx)
        assert app.transitions.filter(action="application_submitted").exists()
    elif number == 48:
        app = submit(ctx)
        assert PmsNotification.objects.filter(
            application=app, event="application.submitted"
        ).exists()

    # Director routing, review, outcomes, timelines, audit and feedback.
    elif number == 49:
        app = director_assignment(ctx)
        assert app.assigned_director_user_id == ctx.director
    elif number == 50:
        not_automated("the baseline has no automatic Director-routing worker/service to invoke")
    elif number == 51:
        app = submit(ctx)
        ctx.director_profile(domains=["chemistry"])
        with pytest.raises(ValidationError):
            services.assign_director(app.pk, ctx.director, ctx.admin)
    elif number == 52:
        app = submit(ctx)
        ctx.director_profile(max_open=0)
        with pytest.raises(ValidationError):
            services.assign_director(app.pk, ctx.director, ctx.admin)
    elif number in (53, 54):
        app = submit(ctx)
        ctx.director_profile()
        ctx.inventor(app, user_id=ctx.director, share="0")
        with pytest.raises(ValidationError):
            services.assign_director(app.pk, ctx.director, ctx.admin)
    elif number == 55:
        not_automated("the baseline has no PCC_ADMIN review operation; PCC_ADMIN only routes work")
    elif number in (56, 57):
        app = director_assignment(ctx)
        assert app.status == Application.Status.UNDER_REVIEW
        assert app.review_due_at is not None
        assert PmsNotification.objects.filter(
            application=app, event="application.director_assigned"
        ).exists()
    elif number == 58:
        app = director_assignment(ctx)
        c = ctx.client(
            user_id=ctx.director, role="Director", permissions=("pms.application.view_all",)
        )
        response = c.get(f"/api/v1/pms/applications/{app.pk}")
        assert response.status_code == 200, response.content
        assert response.json()["id"] == str(app.pk)
    elif number == 59:
        for decision in ("approved", "rejected", "needs_revision"):
            app = director_assignment(ctx)
            services.review_application(app.pk, ctx.director, decision, JUSTIFICATION)
            app.refresh_from_db()
            assert (
                app.status
                == {
                    "approved": Application.Status.APPROVED,
                    "rejected": Application.Status.REJECTED,
                    "needs_revision": Application.Status.NEEDS_REVISION,
                }[decision]
            )
    elif number == 60:
        app = director_assignment(ctx)
        with pytest.raises(ValidationError):
            services.review_application(app.pk, ctx.director, "approved", "too short")
    elif number == 61:
        app = director_assignment(ctx)
        assert app.review_due_at is not None and app.assigned_at is not None
        assert Deadline.objects.filter(application=app, kind="director_review").exists()
    elif number in (62, 63):
        app = director_assignment(ctx)
        decision = "rejected" if number == 62 else "needs_revision"
        services.review_application(app.pk, ctx.director, decision, JUSTIFICATION)
        assert PmsNotification.objects.filter(
            application=app, event=f"application.{decision}"
        ).exists()
    elif number == 64:
        app = approved(ctx)
        ctx.attorney_profile()
        assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        assert assignment.application_id == app.pk
    elif number == 65:
        app = director_assignment(ctx)
        services.review_application(app.pk, ctx.director, "approved", JUSTIFICATION)
        assert PmsAuditEvent.objects.filter(
            application=app, action="director_decision_approved"
        ).exists()

    # Revision and re-review.
    elif number in (66, 67, 68, 69, 70, 71, 72):
        decision = "needs_revision" if number in (66, 68, 69, 70, 71) else "rejected"
        app = director_assignment(ctx)
        services.review_application(app.pk, ctx.director, decision, JUSTIFICATION)
        app.refresh_from_db()
        if number in (66, 67):
            services.resubmit_revision(
                app.pk, ctx.applicant, "Updated the requested application details."
            )
            app.refresh_from_db()
            assert app.status == Application.Status.RESUBMITTED
        elif number == 68:
            assert app.revision_due_at is not None
        elif number == 69:
            with pytest.raises(ValidationError):
                services.resubmit_revision(app.pk, ctx.applicant, "")
        elif number in (70, 71):
            old_count = app.revision_count
            services.resubmit_revision(app.pk, ctx.applicant, "Addressed the Director feedback.")
            app.refresh_from_db()
            assert app.revision_count == old_count + 1
            assert app.transitions.filter(action="application_resubmitted").exists()
        else:
            app.revision_due_at = timezone.now() - timedelta(days=1)
            app.save(update_fields=["revision_due_at"])
            expired = services.resubmit_revision(app.pk, ctx.applicant, "Late revision.")
            assert expired.status == Application.Status.EXPIRED

    # Attorney assignment and response.
    elif number in (74, 75, 76, 77, 78, 79, 80, 81):
        app = approved(ctx)
        panel = number != 75
        ctx.attorney_profile(
            panel=panel,
            domains=["chemistry"] if number == 76 else None,
            max_open=0 if number == 77 else 10,
        )
        if number == 78:
            ctx.inventor(app, user_id=ctx.attorney, share="0")
        if number == 79:
            app.preferred_attorney_user_id = ctx.attorney
            app.save(update_fields=["preferred_attorney_user_id"])
        if number in (75, 76, 77, 78):
            with pytest.raises(ValidationError):
                services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        else:
            row = services.assign_attorney(
                app.pk,
                ctx.attorney,
                ctx.admin,
                panel_exception="Institutional exception" if number == 75 else "",
            )
            if number == 79:
                assert row.preference_recorded
            elif number in (80, 81):
                result = services.respond_to_attorney_assignment(row.pk, ctx.attorney, number == 80)
                assert result.status == ("accepted" if number == 80 else "declined")

    # Business/legal assessment and budget APIs.
    elif number in (82, 84, 85, 88, 89):
        app = approved(ctx)
        app.assigned_attorney_user_id = ctx.attorney
        app.save(update_fields=["assigned_attorney_user_id"])
        c = ctx.client(
            user_id=ctx.attorney, role="Attorney", permissions=("pms.legal_opinion.create",)
        )
        recommendation = "file_patent"
        response = c.post(
            f"/api/v1/pms/applications/{app.pk}/opinion",
            {
                "analysis": "The application has a plausible patentability case.",
                "novelty": "The claims disclose a new arrangement.",
                "non_obviousness": "The combination is not obvious from the cited record.",
                "utility": "The invention has a practical industrial use.",
                "recommendation": recommendation,
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert response.json()["recommendation"] == recommendation
    elif number == 83:
        app = ctx.app(status=Application.Status.APPROVED, assigned_attorney_user_id=ctx.attorney)
        ctx.prior_art_provider(
            lambda *, query, source: [
                {
                    "title": "Prior-art reference",
                    "external_reference": "FR-PRIOR-ART-83",
                    "source_url": "https://patents.example.test/FR-PRIOR-ART-83",
                }
            ]
        )
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.prior_art.search",),
        )
        response = attorney.post(
            "/api/v1/pms/prior-art/search",
            {
                "application_id": str(app.pk),
                "query": "cooling controller",
                "source": "configured-test-provider",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert response.json()["integration_available"] is True
        assert response.json()["results"][0]["external_reference"] == "FR-PRIOR-ART-83"
    elif number == 86:
        app = ctx.app(status=Application.Status.APPROVED, assigned_attorney_user_id=ctx.attorney)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.legal_opinion.create",),
        )
        response = attorney.post(
            f"/api/v1/pms/applications/{app.pk}/legal-information-requests",
            {"request_details": "Please provide the updated experimental validation results."},
            format="json",
        )
        assert response.status_code == 201, response.content
        row = app.legal_information_requests.get(pk=response.json()["id"])
        assert row.requested_by_user_id == ctx.attorney
        assert PmsNotification.objects.filter(
            application=app,
            recipient_user_id=ctx.applicant,
            event="legal_information.requested",
        ).exists()
    elif number == 87:
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        communication = PatentOfficeCommunication.objects.create(
            application=app,
            kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
            external_reference="FR-OA-87",
            received_date=date.today(),
            response_due_date=date.today() + timedelta(days=30),
            deadline_source="Official notice",
            summary="Additional response time required.",
            recorded_by_user_id=ctx.attorney,
        )
        ctx.config("office_action_extension_permitted", True)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.office_action.respond",),
        )
        response = attorney.post(
            f"/api/v1/pms/office-actions/{communication.pk}/extensions",
            {"request_details": "Additional time is needed to complete legal review."},
            format="json",
        )
        assert response.status_code == 201, response.content
        assert OfficeActionExtensionRequest.objects.filter(
            communication=communication,
            requested_by_user_id=ctx.attorney,
        ).exists()
    elif number in (90, 91, 92, 93, 94, 95, 96, 97, 98, 236):
        app = approved(ctx)
        app.assigned_director_user_id = ctx.director
        app.save(update_fields=["assigned_director_user_id"])
        budget = services.propose_budget(
            app.pk,
            ctx.director,
            {"filing_fees": "100.00", "attorney_fees": "200.00", "administrative_costs": "50.00"},
        )
        if number == 95:
            ctx.config("budget_escalation_threshold", "100.00")
            ctx.config("budget_escalation_user_ids", [ctx.admin + 1])
        if number == 97:
            ctx.config("budget_availability_required", True)
            with pytest.raises(ValidationError):
                services.decide_budget(budget.pk, ctx.director, "approved", JUSTIFICATION)
            return
        outcome = "rejected" if number == 236 else "approved"
        result = services.decide_budget(budget.pk, ctx.director, outcome, JUSTIFICATION)
        if number == 236:
            assert result.status == BudgetProposal.Status.REJECTED
        elif number == 95:
            assert result.status == BudgetProposal.Status.ESCALATED
        else:
            assert result.status == BudgetProposal.Status.APPROVED

    # Patent-office filing, office action, maintenance and deadline behavior.
    elif number in (99, 101, 102, 103, 104, 105):
        app = prepare_for_filing(ctx)
        args = {
            "jurisdiction": "India",
            "external_filing_id": f"IPO-{number}",
            "filing_date": date.today(),
        }
        if number == 103:
            args.update(
                jurisdiction="United States", international_justification="Institutional strategy."
            )
        filing = services.record_filing(app.pk, ctx.attorney, **args)
        app.refresh_from_db()
        assert filing.external_filing_id == f"IPO-{number}"
        assert app.status == Application.Status.FILED
    elif number in range(192, 205):
        app = ctx.app()
        if number == 192:
            app = submit(ctx, app)
            expected_events = {"application.submitted"}
        elif number == 193:
            app = director_assignment(ctx, app)
            services.review_application(app.pk, ctx.director, "needs_revision", JUSTIFICATION)
            expected_events = {"application.needs_revision"}
        elif number == 194:
            app = director_assignment(ctx, app)
            expected_events = {"application.director_assigned"}
        elif number == 195:
            app = approved(ctx, app)
            ctx.attorney_profile()
            services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
            expected_events = {"application.attorney_assigned"}
        elif number == 196:
            app = director_assignment(ctx, app)
            services.review_application(app.pk, ctx.director, "approved", JUSTIFICATION)
            expected_events = {"application.approved"}
        elif number == 197:
            app = approved(ctx, app)
            budget = services.propose_budget(
                app.pk,
                ctx.director,
                {
                    "filing_fees": "100.00",
                    "attorney_fees": "200.00",
                    "administrative_costs": "50.00",
                },
            )
            services.decide_budget(budget.pk, ctx.director, "approved", JUSTIFICATION)
            expected_events = {"budget.approved"}
        elif number == 198:
            app = prepare_for_filing(ctx)
            ctx.attorney_profile()
            assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
            services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, True)
            services.record_filing(
                app.pk,
                ctx.attorney,
                jurisdiction="India",
                external_filing_id="FR-NOTIFY-198",
                filing_date=date.today(),
                confirmation_reference="RECEIPT-198",
            )
            expected_events = {"application.filed"}
        elif number == 199:
            app = ctx.app(assigned_attorney_user_id=ctx.attorney)
            attorney = ctx.client(
                user_id=ctx.attorney,
                role="Attorney",
                permissions=("pms.office_action.record",),
            )
            response = attorney.post(
                f"/api/v1/pms/applications/{app.pk}/office-actions",
                {
                    "kind": PatentOfficeCommunication.Kind.OFFICE_ACTION,
                    "external_reference": "OFFICE-199",
                    "received_date": str(date.today()),
                    "summary": "Office action received for notification testing.",
                },
                format="json",
            )
            assert response.status_code == 201, response.content
            expected_events = {"office_action.received"}
        elif number in (200, 201):
            from modules.pms.services.deadlines import process_deadlines

            due_at = (
                timezone.now() + timedelta(days=5)
                if number == 200
                else timezone.now() - timedelta(days=1)
            )
            ctx.config("deadline_alert_days", [30, 15, 5])
            if number == 201:
                ctx.config("deadline_escalation_user_ids", [ctx.admin])
            Deadline.objects.create(
                application=app,
                kind="office_action_response",
                due_at=due_at,
                responsible_user_id=ctx.attorney,
                source=f"FR-{number} notification test",
            )
            process_deadlines()
            expected_events = {"deadline.reminder"} if number == 200 else {"deadline.missed"}
        elif number == 202:
            from modules.pms.services.maintenance import process_maintenance_reminders

            app.assigned_attorney_user_id = ctx.attorney
            app.save(update_fields=["assigned_attorney_user_id"])
            cycle = MaintenanceCycle.objects.create(
                application=app,
                jurisdiction="India",
                due_date=date.today() + timedelta(days=5),
                schedule_source="Configured India maintenance schedule",
            )
            process_maintenance_reminders(today=date.today())
            assert cycle.status == MaintenanceCycle.Status.ACTIVE
            expected_events = {"maintenance.reminder"}
        else:
            first = services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("specification-v1.pdf", b"%PDF-1.4 version one"),
                "specification",
                ApplicationDocument.Sensitivity.INTERNAL,
            )
            if number == 204:
                services.add_document(
                    app.pk,
                    ctx.applicant,
                    SimpleUploadedFile("specification-v2.pdf", b"%PDF-1.4 version two"),
                    "specification",
                    ApplicationDocument.Sensitivity.INTERNAL,
                )
                assert ApplicationDocument.objects.filter(pk=first.pk, application=app).exists()
                expected_events = {"document.version_changed"}
            else:
                expected_events = {"document.updated"}
        assert PmsNotification.objects.filter(application=app, event__in=expected_events).exists()
    elif number == 106:
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.office_action.record", "pms.application.view_all"),
        )
        response = attorney.post(
            f"/api/v1/pms/applications/{app.pk}/office-actions",
            {
                "kind": PatentOfficeCommunication.Kind.OTHER,
                "external_reference": "FR-COMM-106",
                "received_date": str(date.today()),
                "summary": "Official patent-office communication recorded.",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert app.office_communications.filter(pk=response.json()["id"]).exists()
    elif number in range(107, 116):
        if number == 107:
            app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
            attorney = ctx.client(
                user_id=ctx.attorney,
                role="Attorney",
                permissions=("pms.maintenance.manage",),
            )
            response = attorney.post(
                f"/api/v1/pms/applications/{app.pk}/maintenance-cycles",
                {
                    "jurisdiction": "India",
                    "due_date": str(date.today() + timedelta(days=365)),
                    "schedule_source": "Test schedule",
                },
                format="json",
            )
            assert response.status_code == 400, response.content
            assert not app.maintenance_cycles.exists()
        elif number == 108:
            app = ctx.app(status=Application.Status.GRANTED, grant_date=date.today())
            assert not app.maintenance_cycles.exists()
            assert not PmsConfiguration.objects.filter(key="maintenance_schedule").exists()
        else:
            app = ctx.app(
                status=Application.Status.GRANTED,
                grant_date=date.today(),
                assigned_attorney_user_id=ctx.attorney,
                assigned_director_user_id=ctx.director,
            )
            attorney = ctx.client(
                user_id=ctx.attorney,
                role="Attorney",
                permissions=("pms.maintenance.manage", "pms.application.view_all"),
            )
            director = ctx.client(
                user_id=ctx.director,
                role="Director",
                permissions=("pms.maintenance.decide",),
            )
            cycle_response = attorney.post(
                f"/api/v1/pms/applications/{app.pk}/maintenance-cycles",
                {
                    "jurisdiction": "India",
                    "due_date": str(date.today() + timedelta(days=365)),
                    "schedule_source": "Configured test schedule",
                },
                format="json",
            )
            assert cycle_response.status_code == 201, cycle_response.content
            cycle_id = cycle_response.json()["id"]
            if number == 109:
                listed = attorney.get(f"/api/v1/pms/applications/{app.pk}/maintenance-cycles")
                assert listed.status_code == 200, listed.content
                assert listed.json()[0]["id"] == cycle_id
            elif number == 110:
                refused = attorney.post(
                    f"/api/v1/pms/maintenance-cycles/{cycle_id}/record-action",
                    {"transaction_reference": "PAY-BEFORE-DECISION"},
                    format="json",
                )
                assert refused.status_code == 400, refused.content
            elif number == 111:
                requested = attorney.post(
                    f"/api/v1/pms/maintenance-cycles/{cycle_id}/request-decision",
                    {},
                    format="json",
                )
                assert requested.status_code == 200, requested.content
                assert requested.json()["status"] == MaintenanceCycle.Status.DECISION_REQUESTED
                assert PmsNotification.objects.filter(
                    application=app,
                    recipient_user_id=ctx.director,
                    event="maintenance.decision_requested",
                ).exists()
            elif number == 112:
                for index, decision in enumerate(("renew", "do_not_renew")):
                    current_id = cycle_id
                    if index:
                        next_cycle = MaintenanceCycle.objects.create(
                            application=app,
                            jurisdiction="India",
                            due_date=date.today() + timedelta(days=730),
                            schedule_source="Configured test schedule",
                        )
                        current_id = next_cycle.pk
                    assert (
                        attorney.post(
                            f"/api/v1/pms/maintenance-cycles/{current_id}/request-decision",
                            {},
                            format="json",
                        ).status_code
                        == 200
                    )
                    decided = director.post(
                        f"/api/v1/pms/maintenance-cycles/{current_id}/decision",
                        {"decision": decision},
                        format="json",
                    )
                    assert decided.status_code == 200, decided.content
                    assert decided.json()["status"] == (
                        MaintenanceCycle.Status.RENEWAL_APPROVED
                        if decision == "renew"
                        else MaintenanceCycle.Status.DO_NOT_RENEW
                    )
            else:
                attorney.post(
                    f"/api/v1/pms/maintenance-cycles/{cycle_id}/request-decision", {}, format="json"
                )
                decision = director.post(
                    f"/api/v1/pms/maintenance-cycles/{cycle_id}/decision",
                    {"decision": "renew"},
                    format="json",
                )
                assert decision.status_code == 200, decision.content
                acted = attorney.post(
                    f"/api/v1/pms/maintenance-cycles/{cycle_id}/record-action",
                    {
                        "transaction_reference": f"FR-{number}-PAYMENT",
                        "next_cycle_due_date": str(date.today() + timedelta(days=730)),
                    },
                    format="json",
                )
                assert acted.status_code == 200, acted.content
                assert acted.json()["status"] == MaintenanceCycle.Status.RENEWED
                if number in (114, 115):
                    assert MaintenanceCycle.objects.filter(application=app).count() == 2
                    assert app.maintenance_cycles.get(status=MaintenanceCycle.Status.ACTIVE)
    elif number == 117:
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        communication = PatentOfficeCommunication.objects.create(
            application=app,
            kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
            external_reference="FR-OA-117",
            received_date=date.today(),
            response_due_date=date.today() + timedelta(days=30),
            deadline_source="Official notice",
            summary="Review recorded office action.",
            recorded_by_user_id=ctx.attorney,
        )
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.application.view_all",),
        )
        response = attorney.get(f"/api/v1/pms/applications/{app.pk}/office-actions")
        assert response.status_code == 200, response.content
        assert any(row["id"] == communication.pk for row in response.json())
    elif number in (118, 119, 120, 121, 122, 123, 124):
        app = ctx.app(status=Application.Status.FILED, assigned_attorney_user_id=ctx.attorney)
        communication = PatentOfficeCommunication.objects.create(
            application=app,
            kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
            external_reference=f"FR-OA-{number}",
            received_date=date.today(),
            response_due_date=date.today() + timedelta(days=30),
            deadline_source="Official notice",
            summary="Examiner objections require a response.",
            recorded_by_user_id=ctx.attorney,
        )
        ctx.config("office_action_applicant_review_required", True)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.office_action.respond",),
        )
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.office_action_response.review",),
            kind="student",
        )
        if number == 124:
            assert (
                Deadline.objects.filter(
                    application=app,
                    kind="office_action_response",
                    responsible_user_id=ctx.attorney,
                ).exists()
                is False
            )
            recorded = ctx.client(
                user_id=ctx.attorney,
                role="Attorney",
                permissions=("pms.office_action.record",),
            ).post(
                f"/api/v1/pms/applications/{app.pk}/office-actions",
                {
                    "kind": PatentOfficeCommunication.Kind.OFFICE_ACTION,
                    "external_reference": "FR-OA-124-RECORDED",
                    "received_date": str(date.today()),
                    "response_due_date": str(date.today() + timedelta(days=30)),
                    "deadline_source": "Official notice",
                    "summary": "Response deadline recorded.",
                },
                format="json",
            )
            assert recorded.status_code == 201, recorded.content
            assert Deadline.objects.filter(
                application=app,
                kind="office_action_response",
                responsible_user_id=ctx.attorney,
            ).exists()
        elif number == 122:
            ctx.config("office_action_extension_permitted", True)
            extension = attorney.post(
                f"/api/v1/pms/office-actions/{communication.pk}/extensions",
                {"request_details": "Additional time is needed for response preparation."},
                format="json",
            )
            assert extension.status_code == 201, extension.content
            assert OfficeActionExtensionRequest.objects.filter(pk=extension.json()["id"]).exists()
        else:
            drafted = attorney.post(
                f"/api/v1/pms/office-actions/{communication.pk}/responses",
                {"response_text": "The response addresses the examiner's objections."},
                format="json",
            )
            assert drafted.status_code == 201, drafted.content
            response_id = drafted.json()["id"]
            assert drafted.json()["status"] == OfficeActionResponse.Status.AWAITING_APPLICANT
            if number >= 119:
                approved_response = applicant.post(
                    f"/api/v1/pms/office-action-responses/{response_id}/approval",
                    {"approved": True},
                    format="json",
                )
                assert approved_response.status_code == 200, approved_response.content
                assert approved_response.json()["status"] == OfficeActionResponse.Status.READY
            if number in (120, 121, 123):
                submitted_response = attorney.post(
                    f"/api/v1/pms/office-action-responses/{response_id}/submission",
                    {"external_submission_reference": f"FR-RESP-{number}"},
                    format="json",
                )
                assert submitted_response.status_code == 200, submitted_response.content
                assert submitted_response.json()["status"] == OfficeActionResponse.Status.SUBMITTED
            if number == 123:
                assert OfficeActionResponse.objects.filter(
                    pk=response_id, submitted_at__isnull=False
                ).exists()
    elif number in (125, 126, 127, 128, 129, 130, 131):
        app = ctx.ready()
        ctx.config("withdrawal_eligible_statuses", [Application.Status.DRAFT])
        if number == 127:
            with pytest.raises(ValidationError):
                services.withdraw_application(app.pk, ctx.applicant, "")
        elif number == 128:
            ctx.config("withdrawal_requires_co_inventor_consent", True)
            ctx.inventor(app, user_id=ctx.applicant + 2, share="0", state="pending")
            with pytest.raises(ValidationError):
                services.withdraw_application(app.pk, ctx.applicant, "Reason for withdrawal")
        else:
            result = services.withdraw_application(
                app.pk, ctx.applicant, "The team withdrew the proposal."
            )
            assert result.status == Application.Status.WITHDRAWN
            assert result.transitions.filter(action="application_withdrawn").exists()
    elif number in (132, 133, 134, 135, 136, 137, 138, 140):
        app = ctx.app()
        ctx.inventor(app, share="100")
        assert app.inventor_agreements.count() == 1
        assert app.inventor_agreements.get().ownership_percent == Decimal("100.00")
    elif number == 139:
        not_automated(
            "the baseline does not expose an inventor-change event workflow separate from creation/consent"
        )
    elif number in range(141, 150):
        app = ctx.app(status=Application.Status.APPROVED, assigned_attorney_user_id=ctx.attorney)
        user_id = ctx.applicant if number == 141 else ctx.attorney
        role = "Applicant" if number == 141 else "Attorney"
        kind = "student" if number == 141 else "staff"
        observed = []

        def provider(**arguments):
            observed.append(arguments)
            return [
                {
                    "title": "Lower-ranked prior-art result",
                    "external_reference": "FR-LOW",
                    "relevance_score": "0.70",
                },
                {
                    "title": "Higher-ranked prior-art result",
                    "external_reference": "FR-HIGH",
                    "relevance_score": "0.95",
                },
            ]

        ctx.prior_art_provider(provider)
        actor = ctx.client(
            user_id=user_id,
            role=role,
            permissions=("pms.prior_art.search",),
            kind=kind,
        )
        query = "thermal control"
        source = (
            "patent_database"
            if number == 143
            else "publication_database"
            if number == 144
            else "configured-test-provider"
        )
        classification = "F24F"
        payload = {
            "application_id": str(app.pk),
            "query": query,
            "source": source,
            "classification": classification if number == 149 else "",
        }
        response = actor.post("/api/v1/pms/prior-art/search", payload, format="json")
        assert response.status_code == 201, response.content
        session = PriorArtSearchSession.objects.get(pk=response.json()["id"])
        assert session.application_id == app.pk
        assert session.user_id == user_id
        assert session.query == query
        if number in (143, 144):
            assert observed[0]["source"] == source
        if number == 145:
            assert [item["relevance_score"] for item in response.json()["results"]] == [
                "0.95",
                "0.70",
            ]
        if number == 146:
            reference_id = response.json()["results"][0]["id"]
            attached = actor.post(
                f"/api/v1/pms/prior-art/references/{reference_id}/attach",
                {"application_id": str(app.pk)},
                format="json",
            )
            assert attached.status_code == 200, attached.content
            assert (
                PriorArtReference.objects.get(pk=reference_id).attached_to_application_id == app.pk
            )
        if number == 147:
            assert PmsAuditEvent.objects.filter(
                application=app, action="prior_art_search_recorded"
            ).exists()
        if number == 148:
            optimized = "thermal control cooling system high-efficiency"
            second = actor.post(
                "/api/v1/pms/prior-art/search",
                {"application_id": str(app.pk), "query": optimized, "source": source},
                format="json",
            )
            assert second.status_code == 201
            assert observed[-1]["query"] == optimized
        if number == 149:
            assert session.classification == classification
            assert observed[0]["classification"] == classification
    elif number in range(150, 165):
        app = ctx.app(status=Application.Status.NEEDS_REVISION)
        if number == 150:
            first = services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("history-1.pdf", b"%PDF-1.4 v1"),
                "specification",
                "internal",
            )
            second = services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("history-2.pdf", b"%PDF-1.4 v2"),
                "specification",
                "internal",
            )
            assert second.previous_version_id == first.pk
            assert list(app.documents.order_by("version").values_list("version", flat=True)) == [
                1,
                2,
            ]
        elif number in range(151, 158):
            applicant = ctx.client(
                user_id=ctx.applicant,
                role="Applicant",
                permissions=("pms.document.upload", "pms.application.view_self"),
                kind="student",
            )
            if number == 156:
                doc = ApplicationDocument.objects.create(
                    application=app,
                    uploaded_by_user_id=ctx.applicant,
                    document_type="specification",
                    sensitivity=ApplicationDocument.Sensitivity.RESTRICTED,
                    file="pms/test/restricted-version.pdf",
                    original_filename="restricted-version.pdf",
                    content_type="application/pdf",
                    size_bytes=12,
                    malware_scan_status="clean",
                )
                director = ctx.client(
                    user_id=ctx.director,
                    role="Director",
                    permissions=("pms.application.view_all",),
                )
                denied = director.get(
                    f"/api/v1/pms/applications/{app.pk}/documents/{doc.pk}/download"
                )
                assert denied.status_code == 403, denied.content
            elif number == 157:
                uploaded = applicant.post(
                    f"/api/v1/pms/applications/{app.pk}/documents",
                    {
                        "file": SimpleUploadedFile("needs-revision.pdf", b"%PDF-1.4 revision"),
                        "document_type": "specification",
                        "sensitivity": "internal",
                    },
                    format="multipart",
                )
                assert uploaded.status_code == 201, uploaded.content
                app.status = Application.Status.APPROVED
                app.save(update_fields=["status"])
                refused = applicant.post(
                    f"/api/v1/pms/applications/{app.pk}/documents",
                    {
                        "file": SimpleUploadedFile("approved-edit.pdf", b"%PDF-1.4 not allowed"),
                        "document_type": "specification",
                        "sensitivity": "internal",
                    },
                    format="multipart",
                )
                assert refused.status_code == 400, refused.content
            else:
                first = applicant.post(
                    f"/api/v1/pms/applications/{app.pk}/documents",
                    {
                        "file": SimpleUploadedFile("api-version-1.pdf", b"%PDF-1.4 v1"),
                        "document_type": "specification",
                        "sensitivity": "internal",
                    },
                    format="multipart",
                )
                assert first.status_code == 201, first.content
                second = applicant.post(
                    f"/api/v1/pms/applications/{app.pk}/documents",
                    {
                        "file": SimpleUploadedFile("api-version-2.pdf", b"%PDF-1.4 v2"),
                        "document_type": "specification",
                        "sensitivity": "internal",
                    },
                    format="multipart",
                )
                assert second.status_code == 201, second.content
                if number == 151:
                    assert first.json()["version"] == 1
                elif number == 152:
                    assert (first.json()["version"], second.json()["version"]) == (1, 2)
                elif number == 153:
                    assert ApplicationDocument.objects.filter(
                        pk=first.json()["id"], next_versions__pk=second.json()["id"]
                    ).exists()
                elif number == 154:
                    versions = applicant.get(f"/api/v1/pms/applications/{app.pk}/documents")
                    assert versions.status_code == 200, versions.content
                    assert {item["version"] for item in versions.json()} == {1, 2}
                elif number == 155:
                    event = PmsAuditEvent.objects.filter(
                        application=app,
                        actor_user_id=ctx.applicant,
                        action="document_version_uploaded",
                    ).first()
                    assert event is not None
                    assert event.metadata["document_id"] == second.json()["id"]
        else:
            applicant = ctx.client(
                user_id=ctx.applicant,
                role="Applicant",
                permissions=("pms.licensing.submit",),
                kind="student",
            )
            created = applicant.post(
                f"/api/v1/pms/applications/{app.pk}/licensing",
                {
                    "request_details": "Request licensing and technology-transfer review.",
                    "confidentiality": "confidential",
                },
                format="json",
            )
            assert created.status_code == 201, created.content
            request_id = created.json()["id"]
            request_row = LicensingRequest.objects.get(pk=request_id)
            if number in (158, 159):
                assert request_row.status == LicensingRequest.Status.SUBMITTED
            elif number == 163:
                assert not PmsConfiguration.objects.filter(key="financial_system_provider").exists()
                assert request_row.application_id == app.pk
            elif number == 164:
                unauthorized = ctx.client(
                    user_id=ctx.director,
                    role="Director",
                    permissions=("pms.application.view_all",),
                )
                denied = unauthorized.get(f"/api/v1/pms/applications/{app.pk}/licensing")
                assert denied.status_code == 403, denied.content
                assert request_row.confidentiality == ApplicationDocument.Sensitivity.CONFIDENTIAL
            else:
                app.assigned_director_user_id = ctx.director
                app.save(update_fields=["assigned_director_user_id"])
                director = ctx.client(
                    user_id=ctx.director,
                    role="Director",
                    permissions=("pms.licensing.review",),
                )
                target = (
                    LicensingRequest.Status.UNDER_REVIEW
                    if number == 160
                    else LicensingRequest.Status.NEGOTIATING
                    if number == 161
                    else LicensingRequest.Status.AGREEMENT_RECORDED
                )
                if number > 160:
                    director.patch(
                        f"/api/v1/pms/licensing/{request_id}",
                        {"status": LicensingRequest.Status.UNDER_REVIEW},
                        format="json",
                    )
                data = {"status": target}
                if number == 161:
                    data["negotiation_notes"] = "Terms are being reviewed with the licensee."
                if number == 162:
                    data["agreement_reference"] = "LIC-AGREEMENT-162"
                routed = director.patch(f"/api/v1/pms/licensing/{request_id}", data, format="json")
                assert routed.status_code == 200, routed.content
                assert routed.json()["status"] == target
                if number == 161:
                    request_row.refresh_from_db()
                    assert request_row.negotiation_notes
                if number == 162:
                    assert routed.json()["agreement_reference"] == "LIC-AGREEMENT-162"
    elif number in (165, 166, 167, 168, 169, 170, 171):
        app = ctx.ready(status=Application.Status.REJECTED)
        app.decision_at = timezone.now()
        app.assigned_director_user_id = ctx.director
        app.save(update_fields=["decision_at", "assigned_director_user_id"])
        ctx.config("appeal_period_days", 30)
        appeal = services.file_appeal(
            app.pk, ctx.applicant, "The decision misread claim 1.", JUSTIFICATION
        )
        if number == 169:
            services.decide_appeal(appeal.pk, ctx.director, "remand_for_amendment", JUSTIFICATION)
            assert appeal.__class__.objects.get(pk=appeal.pk).outcome == PatentAppeal.Outcome.REMAND
        elif number == 170:
            assert appeal.outcome == PatentAppeal.Outcome.PENDING
        else:
            assert appeal.pk and appeal.grounds
    elif number in (172, 173, 174, 175, 176, 177, 178, 179, 180, 181):
        from modules.pms.services.deadlines import process_deadlines

        now = timezone.now().replace(hour=6, minute=0, second=0, microsecond=0)
        app = ctx.app(
            status=Application.Status.NEEDS_REVISION
            if number in (176, 177)
            else Application.Status.SUBMITTED
        )
        due_in = {172: 30, 173: 15, 174: 5, 175: 30}.get(number, -1)
        if number in (176, 177):
            app.revision_due_at = now - timedelta(days=1)
            app.save(update_fields=["revision_due_at"])
        else:
            Deadline.objects.create(
                application=app,
                kind="review",
                due_at=now + timedelta(days=due_in),
                responsible_user_id=ctx.director,
                source="FR deadline test",
            )
            if number >= 178:
                ctx.config("deadline_escalation_user_ids", [ctx.admin])
        counts = process_deadlines(now=now)
        if number in (176, 177):
            app.refresh_from_db()
            assert app.status == Application.Status.EXPIRED
        elif number in (172, 173, 174, 175):
            assert counts["reminders_queued"] == 1
            assert PmsNotification.objects.filter(
                application=app, event="deadline.reminder"
            ).exists()
        else:
            assert counts["missed_deadlines"] == 1
    elif number == 100:
        app = prepare_for_filing(ctx)
        with pytest.raises(ValidationError):
            services.record_filing(
                app.pk,
                ctx.attorney,
                jurisdiction="India",
                external_filing_id="FR-FORMAT-100",
                filing_date=date.today(),
                format_validation_available=True,
                format_compliant=False,
            )
        assert not PatentFiling.objects.filter(application=app).exists()
    elif number == 116:
        app = ctx.app(assigned_attorney_user_id=ctx.attorney)
        attorney = ctx.client(
            user_id=ctx.attorney,
            role="Attorney",
            permissions=("pms.office_action.record",),
        )
        response = attorney.post(
            f"/api/v1/pms/applications/{app.pk}/office-actions",
            {
                "kind": PatentOfficeCommunication.Kind.OFFICE_ACTION,
                "external_reference": "OFFICE-116",
                "received_date": str(date.today()),
                "summary": "Office action received for response.",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert PatentOfficeCommunication.objects.filter(
            pk=response.json()["id"], application=app
        ).exists()
    elif number == 206:
        app = submit(ctx)
        queued = PmsNotification.objects.filter(
            application=app,
            event="application.submitted",
            status="queued",
        )
        assert queued.exists()
        assert not queued.filter(sent_at__isnull=False).exists()
    elif number in (207, 208, 209, 210, 211, 212, 213):
        app = submit(ctx)
        event = PmsAuditEvent.objects.filter(
            application=app, action="application_submitted"
        ).first()
        assert event is not None
        assert event.actor_user_id == ctx.applicant
        assert event.new_state == Application.Status.SUBMITTED
    elif number in (228, 232):
        app = prepare_for_filing(ctx)
        ctx.attorney_profile()
        assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, True)
        filing = services.record_filing(
            app.pk,
            ctx.attorney,
            jurisdiction="India",
            external_filing_id=f"FR-EXTERNAL-{number}",
            filing_date=date.today(),
            confirmation_reference=f"RECEIPT-{number}",
        )
        assert PatentFiling.objects.filter(
            pk=filing.pk, external_filing_id=f"FR-EXTERNAL-{number}"
        ).exists()
        app.refresh_from_db()
        assert app.status == Application.Status.FILED
    elif number == 229:
        app = ctx.app(status=Application.Status.APPROVED, assigned_director_user_id=ctx.director)
        budget = ctx.budget(app, filing="100.00", attorney="200.00", admin_cost="50.00")
        decided = services.decide_budget(budget.pk, ctx.director, "approved", JUSTIFICATION)
        assert decided.status == BudgetProposal.Status.APPROVED
        assert decided.decided_at is not None and decided.decision_by_user_id == ctx.director
    elif number == 230:
        app = ctx.app()
        first = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("boundary-v1.pdf", b"%PDF-1.4 v1"),
            "specification",
            ApplicationDocument.Sensitivity.INTERNAL,
        )
        second = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("boundary-v2.pdf", b"%PDF-1.4 v2"),
            "specification",
            ApplicationDocument.Sensitivity.INTERNAL,
        )
        assert second.previous_version_id == first.pk and second.version == 2
    elif number == 231:
        from modules.pms.services.prior_art import search_prior_art

        ctx.prior_art_provider(
            lambda **kwargs: [{"title": "External reference", "relevance_score": "0.9"}]
        )
        references = search_prior_art(query="patent search query", source="external-catalog")
        assert references and references[0]["title"] == "External reference"
        assert not PriorArtReference.objects.exists()
    elif number in (214, 215):
        not_automated(
            "encryption at rest and in transit are platform controls outside the isolated PMS database boundary"
        )
    elif number in (216, 220):
        app = ctx.app()
        c = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.application.view_self",),
            kind="student",
        )
        response = c.get(f"/api/v1/pms/applications/{app.pk}")
        assert response.status_code == 200, response.content
    elif number in (217, 218):
        app = ctx.app(status=Application.Status.SUBMITTED, assigned_attorney_user_id=ctx.attorney)
        ctx.attorney_profile()
        with pytest.raises(ValidationError):
            services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
    elif number in (221, 222, 223, 224):
        if number == 221:
            ctx.config("pcc_admin_user_id", ctx.admin)
            assert ctx.config("pcc_admin_user_id", ctx.admin).value == ctx.admin
        elif number == 222:
            ctx.director_profile(user_id=ctx.director)
            ctx.director_profile(user_id=ctx.director + 1)
            from modules.pms.models import DirectorProfile

            assert DirectorProfile.objects.count() == 2
        elif number == 223:
            ctx.attorney_profile(user_id=ctx.attorney)
            ctx.attorney_profile(user_id=ctx.attorney + 1)
            from modules.pms.models import AttorneyProfile

            assert AttorneyProfile.objects.count() == 2
        else:
            ctx.app(applicant=ctx.applicant)
            ctx.app(applicant=ctx.applicant + 1)
            assert Application.objects.count() == 2
    elif number == 225:
        app = ctx.app(assigned_director_user_id=ctx.director)
        with pytest.raises(ValidationError):
            services.review_application(app.pk, ctx.director, "approved", JUSTIFICATION)
    elif number == 226:
        from modules.pms.services.deadlines import process_deadlines

        app = ctx.app()
        ctx.config("deadline_escalation_user_ids", [ctx.admin])
        deadline = Deadline.objects.create(
            application=app,
            kind="office_action_response",
            due_at=timezone.now() - timedelta(days=1),
            responsible_user_id=ctx.attorney,
            source="FR delayed-action test",
        )
        result = process_deadlines()
        deadline.refresh_from_db()
        assert deadline.status == "escalated"
        assert result["missed_deadlines"] == 1
        assert PmsNotification.objects.filter(application=app, event="deadline.missed").exists()
    elif number == 227:
        not_automated(
            "the specification does not identify a concrete parallel process or a callable process-level interface"
        )
    elif number in range(182, 192):
        app = ctx.app(
            status=Application.Status.FILED,
            assigned_director_user_id=ctx.director,
            assigned_attorney_user_id=ctx.attorney,
        )
        director = ctx.client(
            user_id=ctx.director,
            role="Director",
            permissions=("pms.application.review", "pms.report.view"),
        )
        if number == 182:
            response = director.get("/api/v1/pms/reports")
            assert response.status_code == 200, response.content
            assert response.json()["total"] == 1
            assert response.json()["by_status"][0]["status"] == Application.Status.FILED
        elif number == 183:
            ctx.budget(app, filing="100.00", attorney="200.00", admin_cost="50.00")
            report = director.get("/api/v1/pms/reports")
            assert report.status_code == 200, report.content
            assert report.json()["financial"]["budget_count"] == 1
            assert report.json()["financial"]["proposed_total"] == 350.0
        elif number == 184:
            Deadline.objects.create(
                application=app,
                kind="office_action_response",
                due_at=timezone.now() + timedelta(days=5),
                responsible_user_id=ctx.attorney,
                source="Official notice",
            )
            report = director.get("/api/v1/pms/reports")
            assert report.status_code == 200, report.content
            assert report.json()["deadlines"]["open_count"] == 1
        elif number == 185:
            ctx.inventor(app, user_id=ctx.applicant, share="60")
            ctx.inventor(app, user_id=ctx.applicant + 1, share="40", full_name="Second Inventor")
            report = director.get("/api/v1/pms/reports")
            assert report.status_code == 200, report.content
            assert report.json()["inventors"]["agreement_count"] == 2
        elif number == 186:
            PatentFiling.objects.create(
                application=app,
                filed_by_user_id=ctx.attorney,
                jurisdiction="India",
                external_filing_id="FR-PORTFOLIO-186",
                filing_date=date.today(),
                confirmation_reference="RECEIPT-186",
            )
            report = director.get("/api/v1/pms/reports")
            assert report.status_code == 200, report.content
            assert report.json()["portfolio"]["filing_count"] == 1
            assert report.json()["portfolio"]["by_jurisdiction"][0]["jurisdiction"] == "India"
        elif number == 187:
            report = director.get("/api/v1/pms/reports")
            assert report.status_code == 200, report.content
            assert report.json()["workload"]["directors"] == [
                {"assigned_director_user_id": ctx.director, "count": 1}
            ]
            assert report.json()["workload"]["attorneys"] == [
                {"assigned_attorney_user_id": ctx.attorney, "count": 1}
            ]
        elif number == 188:
            applicant = ctx.client(
                user_id=ctx.applicant,
                role="Applicant",
                permissions=("pms.report.view_self",),
                kind="student",
            )
            scheduled = applicant.post(
                "/api/v1/pms/reports/schedules",
                {
                    "frequency": "weekly",
                    "output_format": "csv",
                    "filters": {"status": Application.Status.FILED},
                },
                format="json",
            )
            assert scheduled.status_code == 201, scheduled.content
            assert PmsReportSchedule.objects.filter(
                pk=scheduled.json()["id"], requested_by_user_id=ctx.applicant
            ).exists()
        elif number == 189:
            applicant = ctx.client(
                user_id=ctx.applicant,
                role="Applicant",
                permissions=("pms.report.view_self",),
                kind="student",
            )
            exported = applicant.get(
                "/api/v1/pms/reports?export=csv&fields=application_number,status"
            )
            assert exported.status_code == 200
            assert exported["Content-Type"].startswith("text/csv")
            assert app.application_number in exported.content.decode()
        elif number == 190:
            other = ctx.app(status=Application.Status.DRAFT)
            applicant = ctx.client(
                user_id=ctx.applicant,
                role="Applicant",
                permissions=("pms.report.view_self",),
                kind="student",
            )
            custom = applicant.get("/api/v1/pms/reports?status=filed&fields=title,status&limit=1")
            assert custom.status_code == 200, custom.content
            assert custom.json()["total"] == 1
            assert custom.json()["applications"] == [
                {"title": app.title, "status": Application.Status.FILED}
            ]
            assert other.status == Application.Status.DRAFT
        else:
            report = director.get("/api/v1/pms/reports")
            assert report.status_code == 200, report.content
            assert PmsAuditEvent.objects.filter(
                actor_user_id=ctx.director, action="report_accessed"
            ).exists()
    elif number in (237, 238, 239):
        app = ctx.ready(status=Application.Status.DRAFT)
        services.submit_application(app.pk, ctx.applicant)
        if number == 238:
            ctx.director_profile()
            services.assign_director(app.pk, ctx.director, ctx.admin)
            services.review_application(app.pk, ctx.director, "approved", JUSTIFICATION)
        if number == 239:
            ctx.applicant = ctx.applicant + 10
            other = ctx.ready(status=Application.Status.DRAFT)
            services.submit_application(other.pk, ctx.applicant)
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.report.view_self",),
            kind="student",
        )
        response = applicant.get("/api/v1/pms/reports")
        assert response.status_code == 200, response.content
        body = response.json()
        if number == 237:
            assert body["total"] >= 1 and "by_status" in body
        elif number == 238:
            assert body["history"]
            assert any(row["to_status"] == Application.Status.APPROVED for row in body["history"])
        else:
            assert body["trends"]
            assert all(
                "month" in row and "status" in row and "count" in row for row in body["trends"]
            )
    else:
        not_automated(f"no deterministic backend operation is available for {sid} in this baseline")


@pytest.mark.django_db
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_frozen_atomic_requirement(case, pms_ctx):
    """The pytest node name includes both test_id and source_id from the frozen design."""
    exercise_fr(case, pms_ctx)
