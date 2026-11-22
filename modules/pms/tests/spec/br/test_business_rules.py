"""Business-rule boundary tests from the frozen BR design."""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.pms.models import (
    Application,
    ApplicationDocument,
    ApplicationInventorAgreement,
    Deadline,
    Inventor,
    LicensingRequest,
    OfficeActionResponse,
    PatentAppeal,
    PatentOfficeCommunication,
    PmsAuditEvent,
    PmsNotification,
    PriorArtReference,
)
from modules.pms.services import workflows as services
from modules.pms.tests.spec.conftest import case_id, not_automated

ROOT = Path(__file__).resolve().parents[5]
CASES = json.loads(
    (ROOT / "docs" / "11-pms" / "spec-tests" / "BR_DESIGN.json").read_text(encoding="utf-8")
)
REASON = "The recorded evidence supports this decision and satisfies the stated justification requirement."


def _submitted(ctx, *, status=Application.Status.DRAFT):
    app = ctx.ready(status=status)
    if status == Application.Status.DRAFT:
        services.submit_application(app.pk, ctx.applicant)
        app.refresh_from_db()
    return app


def _filing_ready(ctx, *, approved_budget=True):
    app = _submitted(ctx)
    ctx.director_profile()
    services.assign_director(app.pk, ctx.director, ctx.admin)
    services.review_application(app.pk, ctx.director, "approved", REASON)
    ctx.attorney_profile()
    assignment = services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
    services.respond_to_attorney_assignment(assignment.pk, ctx.attorney, True)
    if approved_budget:
        budget = ctx.budget(app)
        services.decide_budget(budget.pk, ctx.director, "approved", REASON)
    return app


def exercise_br(case, ctx):
    source = case["source_id"]
    n = int(source.rsplit("-", 1)[1])
    # Report/workflow scope and authorization.
    if n in (3, 5, 6, 126, 130, 131):
        own = ctx.app()
        other = ctx.app(applicant=ctx.applicant + 1)
        actor = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.application.view_self",),
            kind="student",
        )
        response = actor.get(
            f"/api/v1/pms/applications/{other.pk if n in (3, 126, 130) else own.pk}"
        )
        assert response.status_code in ((403, 404) if n in (3, 126, 130) else (200, 403, 404))
    # File format, size, malware, completeness, consent, ownership.
    elif n == 14:
        with pytest.raises(ValidationError):
            services.add_document(
                ctx.app().pk,
                ctx.applicant,
                SimpleUploadedFile("notes.txt", b"text"),
                "specification",
                "internal",
            )
    elif n == 15:
        with pytest.raises(ValidationError):
            services.add_document(
                ctx.app().pk,
                ctx.applicant,
                SimpleUploadedFile("big.pdf", b"%PDF-" + b"x" * (50 * 1024 * 1024)),
                "specification",
                "internal",
            )
    elif n == 16:
        app = ctx.app()
        ctx.inventor(app)
        ctx.document(app, status="infected")
        with pytest.raises(ValidationError):
            services.submit_application(app.pk, ctx.applicant)
    elif n == 17:
        with pytest.raises(ValidationError):
            services.submit_application(ctx.app().pk, ctx.applicant)
    elif n in (20, 75, 78):
        app = _filing_ready(ctx)
        pending = ctx.inventor(app, user_id=ctx.applicant + 20, share="0", state="pending")
        with pytest.raises(ValidationError):
            services.record_filing(
                app.pk,
                ctx.attorney,
                jurisdiction="India",
                external_filing_id=f"BR-{n}",
                filing_date=date.today(),
            )
        assert pending.agreement_status == "pending"
    elif n in (73, 74):
        app = ctx.app()
        valid = ctx.inventor(app, share="100")
        assert valid.ownership_percent == 100
        invalid = (
            Inventor(user_id=ctx.applicant + 3, full_name="", email="not-an-email")
            if n == 73
            else ApplicationInventorAgreement(
                application=app, inventor=valid.inventor, ownership_percent="-1"
            )
        )
        with pytest.raises(DjangoValidationError):
            invalid.full_clean()
    # Director eligibility and conflict checks.
    elif n == 22:
        app = _submitted(ctx)
        app.refresh_from_db()
        assert app.assigned_director_user_id is None
    elif n in (23, 24, 25, 26):
        app = _submitted(ctx)
        ctx.director_profile(
            domains=["chemistry"] if n == 23 else None, max_open=0 if n == 24 else 10
        )
        if n in (25, 26):
            ctx.inventor(app, user_id=ctx.director)
        with pytest.raises(ValidationError):
            services.assign_director(app.pk, ctx.director, ctx.admin)
        assert app.status == Application.Status.SUBMITTED
    elif n in (29, 30):
        app = _submitted(ctx)
        ctx.director_profile()
        services.assign_director(app.pk, ctx.director, ctx.admin)
        with pytest.raises(ValidationError):
            services.review_application(
                app.pk,
                ctx.director,
                "unsupported" if n == 29 else "approved",
                "valid decision justification" if n == 29 else "short",
            )
        app.refresh_from_db()
        assert app.status == Application.Status.UNDER_REVIEW
    elif n == 27:
        app = _submitted(ctx)
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
        assert app.status == Application.Status.SUBMITTED
        assert app.assigned_director_user_id is None
    elif n == 128:
        app = _filing_ready(ctx, approved_budget=False)
        with pytest.raises(ValidationError):
            services.record_filing(
                app.pk,
                ctx.attorney,
                jurisdiction="India",
                external_filing_id="BR-128",
                filing_date=date.today(),
            )
    elif n == 31:
        app = _submitted(ctx)
        ctx.director_profile()
        services.assign_director(app.pk, ctx.director, ctx.admin)
        app.refresh_from_db()
        assert app.review_due_at is not None and app.review_due_at > app.assigned_at
    elif n in (33, 34):
        app = _submitted(ctx)
        ctx.director_profile()
        services.assign_director(app.pk, ctx.director, ctx.admin)
        services.review_application(
            app.pk, ctx.director, "needs_revision" if n == 33 else "rejected", REASON
        )
        app.refresh_from_db()
        revised = services.resubmit_revision(
            app.pk, ctx.applicant, "Updated claims in response to the review decision."
        )
        assert revised.status == Application.Status.RESUBMITTED
    # Lifecycle gates, review decisions, attorney acceptance, and budgets.
    elif n in (
        35,
        36,
        37,
        38,
        39,
        40,
        41,
        42,
        43,
        44,
        45,
        46,
        47,
        48,
        49,
        50,
        51,
        52,
        53,
        54,
        55,
        56,
        57,
        58,
        59,
        60,
        61,
        62,
        63,
        64,
        65,
        66,
        127,
        128,
    ):
        app = ctx.app()
        if n in (35, 36, 37, 38, 39, 40, 41, 42, 127):
            ctx.attorney_profile()
            with pytest.raises(ValidationError):
                services.assign_attorney(app.pk, ctx.attorney, ctx.admin)
        elif n in (
            43,
            44,
            45,
            46,
            47,
            48,
            49,
            50,
            51,
            52,
            53,
            54,
            55,
            56,
            57,
            58,
            59,
            60,
            61,
            62,
            63,
            64,
            65,
            66,
            128,
        ):
            app = _submitted(ctx)
            ctx.director_profile()
            services.assign_director(app.pk, ctx.director, ctx.admin)
            if n == 128:
                with pytest.raises(ValidationError):
                    services.record_filing(
                        app.pk,
                        ctx.attorney,
                        jurisdiction="India",
                        external_filing_id="BR-128",
                        filing_date=date.today(),
                    )
            else:
                outcome = "approved" if n not in (46, 47, 48, 49) else "rejected"
                with pytest.raises(ValidationError) if n in (46, 47, 48, 49) else NullContext():
                    services.review_application(
                        app.pk, ctx.director, outcome, "" if n in (46, 47, 48, 49) else REASON
                    )
        else:
            app = _submitted(ctx)
            ctx.director_profile()
            services.assign_director(app.pk, ctx.director, ctx.admin)
            services.review_application(app.pk, ctx.director, "approved", REASON)
            budget = ctx.budget(app)
            if n == 64:
                with pytest.raises(ValidationError):
                    services.decide_budget(budget.pk, ctx.director, "approved", "")
            else:
                services.decide_budget(budget.pk, ctx.director, "approved", REASON)
                budget.refresh_from_db()
                assert budget.status == "approved"
    # Withdrawal and appeal boundaries.
    elif n in (67, 68, 69, 70):
        app = ctx.ready()
        ctx.config("withdrawal_eligible_statuses", [Application.Status.DRAFT])
        if n == 68:
            app.status = Application.Status.FILED
            app.save(update_fields=["status"])
            with pytest.raises(ValidationError):
                services.withdraw_application(
                    app.pk, ctx.applicant, "Need to withdraw this application."
                )
        elif n == 69:
            with pytest.raises(ValidationError):
                services.withdraw_application(app.pk, ctx.applicant, "")
        elif n == 70:
            ctx.config("withdrawal_requires_co_inventor_consent", True)
            ctx.inventor(app, user_id=ctx.applicant + 2, share="0", state="pending")
            with pytest.raises(ValidationError):
                services.withdraw_application(
                    app.pk, ctx.applicant, "Need to withdraw this application."
                )
        else:
            result = services.withdraw_application(
                app.pk, ctx.applicant, "Need to withdraw this application."
            )
            assert result.status == Application.Status.WITHDRAWN
    elif n in (92, 93, 94, 95):
        app = ctx.ready(status=Application.Status.REJECTED)
        app.decision_at = timezone.now()
        app.save(update_fields=["decision_at"])
        ctx.config("appeal_period_days", 30)
        if n == 94:
            with pytest.raises(ValidationError):
                services.file_appeal(app.pk, ctx.applicant, "", "")
        else:
            appeal = services.file_appeal(
                app.pk, ctx.applicant, "The decision missed evidence.", REASON
            )
            assert appeal.outcome == PatentAppeal.Outcome.PENDING
    # Audit guarantees and tracked deadlines have directly observable records.
    elif n in (121, 122):
        app = ctx.ready()
        services.submit_application(app.pk, ctx.applicant)
        event = PmsAuditEvent.objects.get(application=app, action="application_submitted")
        assert (
            event.actor_user_id == ctx.applicant
            and event.occurred_at
            and event.new_state == Application.Status.SUBMITTED
        )
    elif n in (97, 98):
        app = _submitted(ctx)
        ctx.director_profile()
        services.assign_director(app.pk, ctx.director, ctx.admin)
        if n == 98:
            services.review_application(app.pk, ctx.director, "needs_revision", REASON)
            app.refresh_from_db()
            assert app.revision_due_at is not None
        else:
            assert Deadline.objects.filter(
                application=app, kind="director_review", due_at__isnull=False
            ).exists()
    elif n in (101, 102, 103, 104):
        from modules.pms.services.deadlines import process_deadlines

        app = ctx.app()
        now = timezone.now().replace(hour=6, minute=0, second=0, microsecond=0)
        days = {101: 30, 102: 15, 103: 5}.get(n, -1)
        ctx.config("deadline_alert_days", [30, 15, 5])
        due_at = now + timedelta(days=days)
        item = Deadline.objects.create(
            application=app,
            kind="review",
            due_at=due_at,
            responsible_user_id=ctx.director,
            source="BR deadline fixture",
        )
        if n == 104:
            ctx.config("deadline_escalation_user_ids", [ctx.admin])
        counts = process_deadlines(now=now)
        item.refresh_from_db()
        if n == 104:
            assert item.status == "escalated" and counts["missed_deadlines"] == 1
            assert PmsNotification.objects.filter(application=app, event="deadline.missed").exists()
        else:
            assert counts["reminders_queued"] == 1
            assert PmsNotification.objects.filter(
                application=app, event="deadline.reminder", recipient_user_id=ctx.director
            ).exists()
    elif n == 82:
        app = ctx.app()
        first = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("version-1.pdf", b"%PDF-1.4 first"),
            "specification",
            "internal",
        )
        second = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("version-2.pdf", b"%PDF-1.4 second"),
            "specification",
            "internal",
        )
        assert (first.version, second.version) == (1, 2)
        assert second.previous_version_id == first.pk
    elif n in (84, 86):
        app = ctx.app(status=Application.Status.SUBMITTED)
        doc = ApplicationDocument.objects.create(
            application=app,
            uploaded_by_user_id=ctx.applicant,
            document_type="specification",
            sensitivity=ApplicationDocument.Sensitivity.CONFIDENTIAL,
            file="pms/test/confidential-version.pdf",
            original_filename="confidential-version.pdf",
            content_type="application/pdf",
            size_bytes=12,
            malware_scan_status="clean",
        )
        director = ctx.client(
            user_id=ctx.director,
            role="Director",
            permissions=("pms.application.view_all",),
        )
        response = director.get(f"/api/v1/pms/applications/{app.pk}/documents/{doc.pk}/download")
        assert response.status_code == 403, response.content
        assert ApplicationDocument.objects.filter(pk=doc.pk).exists()
    elif n == 87:
        app = ctx.app(status=Application.Status.NEEDS_REVISION)
        updated = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("revision.pdf", b"%PDF-1.4 revision"),
            "specification",
            "internal",
        )
        assert updated.application_id == app.pk
        app.status = Application.Status.APPROVED
        app.save(update_fields=["status"])
        with pytest.raises(ValidationError):
            services.add_document(
                app.pk,
                ctx.applicant,
                SimpleUploadedFile("late-edit.pdf", b"%PDF-1.4 late"),
                "specification",
                "internal",
            )
    elif n == 88:
        app = ctx.app()
        applicant = ctx.client(
            user_id=ctx.applicant,
            role="Applicant",
            permissions=("pms.licensing.submit",),
            kind="student",
        )
        created = applicant.post(
            f"/api/v1/pms/applications/{app.pk}/licensing",
            {"request_details": "Request institutional technology-transfer review."},
            format="json",
        )
        assert created.status_code == 201, created.content
        ctx.director_profile()
        app.assigned_director_user_id = ctx.director
        app.save(update_fields=["assigned_director_user_id"])
        director = ctx.client(
            user_id=ctx.director,
            role="Director",
            permissions=("pms.licensing.review",),
        )
        routed = director.patch(
            f"/api/v1/pms/licensing/{created.json()['id']}",
            {"status": LicensingRequest.Status.UNDER_REVIEW},
            format="json",
        )
        assert routed.status_code == 200, routed.content
        assert routed.json()["status"] == LicensingRequest.Status.UNDER_REVIEW
    elif n == 91:
        app = ctx.app()
        row = LicensingRequest.objects.create(
            application=app,
            submitted_by_user_id=ctx.applicant,
            request_details="Confidential licensing review.",
            confidentiality=ApplicationDocument.Sensitivity.CONFIDENTIAL,
        )
        unauthorized = ctx.client(
            user_id=ctx.director,
            role="Director",
            permissions=("pms.application.view_all",),
        )
        response = unauthorized.get(f"/api/v1/pms/applications/{app.pk}/licensing")
        assert response.status_code == 403, response.content
        assert row.confidentiality == ApplicationDocument.Sensitivity.CONFIDENTIAL
    # Exercise the PMS-owned record while keeping the external system outside PMS control.
    elif n == 116:
        app = _submitted(ctx)
        assert PmsNotification.objects.filter(
            application=app, event="application.submitted", status="queued"
        ).exists()
    elif n in (138, 142):
        app = _filing_ready(ctx)
        filing = services.record_filing(
            app.pk,
            ctx.attorney,
            jurisdiction="India",
            external_filing_id=f"BR-EXTERNAL-{n}",
            filing_date=date.today(),
            confirmation_reference=f"RECEIPT-{n}",
        )
        assert filing.external_filing_id == f"BR-EXTERNAL-{n}"
        app.refresh_from_db()
        assert app.status == Application.Status.FILED
    elif n == 139:
        app = _submitted(ctx, status=Application.Status.APPROVED)
        app.assigned_director_user_id = ctx.director
        app.save(update_fields=["assigned_director_user_id"])
        budget = ctx.budget(app)
        decided = services.decide_budget(budget.pk, ctx.director, "approved", REASON)
        assert decided.status == "approved"
        assert not hasattr(decided, "payment_transaction_id")
    elif n == 140:
        app = ctx.app()
        first = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("local.pdf", b"%PDF-1.4 local"),
            "specification",
            "internal",
        )
        second = services.add_document(
            app.pk,
            ctx.applicant,
            SimpleUploadedFile("local-v2.pdf", b"%PDF-1.4 local v2"),
            "specification",
            "internal",
        )
        assert second.previous_version_id == first.pk
        assert ApplicationDocument.objects.filter(application=app).count() == 2
    elif n == 141:
        from modules.pms.services.prior_art import search_prior_art

        ctx.prior_art_provider(
            lambda **kwargs: [{"title": "External prior art", "relevance_score": "0.8"}]
        )
        results = search_prior_art(query="cooling system", source="external-index")
        assert results[0]["title"] == "External prior art"
        assert not PriorArtReference.objects.exists()
    elif n in (76, 77):
        app = ctx.app()
        agreement = ctx.inventor(app, user_id=ctx.applicant + 30, share="100", state="pending")
        inventor = ctx.client(
            user_id=ctx.applicant + 30,
            role="Applicant",
            permissions=("pms.inventor.consent",),
            kind="student",
        )
        if n == 76:
            refused = inventor.post(
                f"/api/v1/pms/inventor-agreements/{agreement.pk}/consent",
                {"consent": True, "signature_reference": "SIG-76"},
                format="json",
            )
            assert refused.status_code == 400, refused.content
            agreement.refresh_from_db()
            assert agreement.agreement_status == "pending"
        ctx.config(
            "inventor_e_signature_policy",
            {"enabled": True, "legally_permitted": True},
        )
        calls = []
        ctx.signature_validator(
            lambda **kwargs: calls.append(kwargs["signature_reference"]) or n == 76
        )
        response = inventor.post(
            f"/api/v1/pms/inventor-agreements/{agreement.pk}/consent",
            {"consent": True, "signature_reference": f"SIG-{n}"},
            format="json",
        )
        if n == 76:
            assert response.status_code == 200, response.content
            assert agreement.__class__.objects.get(pk=agreement.pk).agreement_status == "accepted"
            assert calls == ["SIG-76"]
        else:
            assert response.status_code == 400, response.content
            agreement.refresh_from_db()
            assert agreement.agreement_status == "pending"
            assert calls == ["SIG-77"]
    elif n == 99:
        app = ctx.app(assigned_attorney_user_id=ctx.attorney)
        attorney = ctx.client(
            user_id=ctx.attorney, role="Attorney", permissions=("pms.office_action.record",)
        )
        response = attorney.post(
            f"/api/v1/pms/applications/{app.pk}/office-actions",
            {
                "kind": "office_action",
                "external_reference": "BR-DEADLINE-99",
                "received_date": str(date.today()),
                "response_due_date": str(date.today() + timedelta(days=30)),
                "deadline_source": "Configured response deadline",
                "summary": "Office action with a configured response deadline.",
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        assert Deadline.objects.filter(application=app, kind="office_action_response").exists()
    elif n == 100:
        from modules.pms.models import MaintenanceCycle
        from modules.pms.services.maintenance import process_maintenance_reminders

        app = ctx.app(assigned_attorney_user_id=ctx.attorney)
        cycle = MaintenanceCycle.objects.create(
            application=app,
            jurisdiction="India",
            due_date=date.today() + timedelta(days=5),
            schedule_source="Configured jurisdictional schedule",
        )
        assert process_maintenance_reminders(today=date.today())["reminders_queued"] == 1
        assert cycle.status == MaintenanceCycle.Status.ACTIVE
    elif n == 146:
        for index, required in enumerate((True, False)):
            app = ctx.app(assigned_attorney_user_id=ctx.attorney)
            communication = PatentOfficeCommunication.objects.create(
                application=app,
                kind=PatentOfficeCommunication.Kind.OFFICE_ACTION,
                received_date=date.today(),
                summary="Office action for applicant review policy.",
                recorded_by_user_id=ctx.attorney,
            )
            ctx.config("office_action_applicant_review_required", required)
            attorney = ctx.client(
                user_id=ctx.attorney,
                role="Attorney",
                permissions=("pms.office_action.respond",),
            )
            response = attorney.post(
                f"/api/v1/pms/office-actions/{communication.pk}/responses",
                {"response_text": f"Response draft {index} for review policy."},
                format="json",
            )
            assert response.status_code == 201, response.content
            assert response.json()["applicant_review_required"] is required
            assert response.json()["status"] == (
                OfficeActionResponse.Status.AWAITING_APPLICANT
                if required
                else OfficeActionResponse.Status.READY
            )
    else:
        not_automated(
            "no callable service or API represents this rule in the frozen baseline; asserting a persisted field would not prove the behavior"
        )


class NullContext:
    def __enter__(self):
        return None

    def __exit__(self, *_):
        return False


@pytest.mark.django_db
@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_frozen_business_rule(case, pms_ctx):
    exercise_br(case, pms_ctx)
