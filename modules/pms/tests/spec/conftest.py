"""Reusable data builders for specification-driven PMS backend tests."""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.models import (
    Application,
    ApplicationDocument,
    ApplicationInventorAgreement,
    AttorneyProfile,
    BudgetProposal,
    DirectorProfile,
    Inventor,
    PmsConfiguration,
)


class SessionBoundAPIClient(APIClient):
    """Reinstall each request's IAM session before dispatching the request."""

    def __init__(self, session, install_session):
        super().__init__()
        self._session = session
        self._install_session = install_session

    def request(self, *args, **kwargs):
        self._install_session(self._session)
        return super().request(*args, **kwargs)


@pytest.fixture
def pms_ctx(db, stub_iam, tmp_path, settings):
    settings.PMS_UPLOAD_ROOT = str(tmp_path / "pms-private")

    class Context:
        applicant = 1101
        admin = 2201
        director = 3301
        attorney = 4401

        def app(self, *, status=Application.Status.DRAFT, applicant=None, **overrides):
            values = {
                "applicant_user_id": applicant or self.applicant,
                "title": "Adaptive Cooling System",
                "abstract": "A system that improves thermal efficiency.",
                "detailed_description": "A complete technical description for testing.",
                "claims": "1. A cooling system comprising a variable flow controller.",
                "technical_domain": "mechanical engineering",
                "status": status,
            }
            values.update(overrides)
            return Application.objects.create(**values)

        def inventor(
            self,
            app,
            *,
            user_id=None,
            share="100.00",
            state="accepted",
            full_name="Asha Inventor",
            email="asha@example.test",
        ):
            person, _ = Inventor.objects.get_or_create(
                user_id=user_id or self.applicant,
                full_name=full_name,
                email=email,
            )
            return ApplicationInventorAgreement.objects.create(
                application=app,
                inventor=person,
                ownership_percent=Decimal(str(share)),
                agreement_status=state,
                consent_recorded_at=timezone.now() if state == "accepted" else None,
            )

        def document(self, app, *, status="clean", filename="specification.pdf", size=128):
            return ApplicationDocument.objects.create(
                application=app,
                uploaded_by_user_id=self.applicant,
                document_type="specification",
                sensitivity=ApplicationDocument.Sensitivity.INTERNAL,
                file=f"pms/test/{filename}",
                original_filename=filename,
                content_type="application/pdf",
                size_bytes=size,
                malware_scan_status=status,
            )

        def ready(self, app=None, *, status=None):
            app = app or self.app(status=status or Application.Status.DRAFT)
            if not app.inventor_agreements.exists():
                self.inventor(app)
            if not app.documents.exists():
                self.document(app)
            return app

        def director_profile(self, *, user_id=None, domains=None, max_open=10, active=True):
            profile, _ = DirectorProfile.objects.update_or_create(
                user_id=user_id or self.director,
                defaults={
                    "expertise_domains": domains or ["mechanical engineering"],
                    "max_open_reviews": max_open,
                    "active": active,
                },
            )
            return profile

        def attorney_profile(
            self, *, user_id=None, domains=None, max_open=10, panel=True, active=True
        ):
            profile, _ = AttorneyProfile.objects.update_or_create(
                user_id=user_id or self.attorney,
                defaults={
                    "expertise_domains": domains or ["mechanical engineering"],
                    "max_open_matters": max_open,
                    "panel_approved": panel,
                    "active": active,
                },
            )
            return profile

        def config(self, key, value):
            row, _ = PmsConfiguration.objects.update_or_create(
                key=key, defaults={"value": value, "updated_by_user_id": self.admin}
            )
            return row

        def prior_art_provider(self, provider):
            settings.PMS_PRIOR_ART_SEARCH_PROVIDER = provider

        def signature_validator(self, provider):
            settings.PMS_INVENTOR_SIGNATURE_VALIDATOR = provider

        def client(self, *, user_id, role, permissions, kind="staff"):
            session = make_session(
                user_id=user_id,
                permissions=tuple(permissions),
                modules=("pms",),
                kind=kind,
                roles=(role,),
                active_role=role,
            )
            stub_iam(session)
            client = SessionBoundAPIClient(session, stub_iam)
            client.credentials(HTTP_AUTHORIZATION="Token a8-test-session")
            return client

        def budget(
            self,
            app,
            *,
            status=BudgetProposal.Status.PROPOSED,
            filing="100.00",
            attorney="200.00",
            admin_cost="50.00",
        ):
            return BudgetProposal.objects.create(
                application=app,
                filing_fees=Decimal(filing),
                attorney_fees=Decimal(attorney),
                administrative_costs=Decimal(admin_cost),
                status=status,
            )

    return Context()


def case_id(case):
    return f"{case['test_id']}__{case['source_id']}"


def not_automated(reason):
    pytest.skip(f"NOT_AUTOMATED: {reason}")
