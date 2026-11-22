"""Demo fixtures.

Lives in `devtools` rather than inside a module: seeding is cross-cutting and
would otherwise make one module import three others' models. `devtools` is a
tool, not a bounded context, so .importlinter exempts it explicitly.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.directory.models import UserRef
from modules.placement.models import Application, Company, JobPosting
from modules.spacs.models import AwardCandidate, AwardCycle, SchemeCatalogue, SchemePolicyVersion, ScholarshipApplication


class Command(BaseCommand):
    help = "Load demo data (idempotent)"

    @transaction.atomic
    def handle(self, *args, **opts):
        for uid, name, kind, disc in [
            (1001, "Asha Verma", "student", "CSE"),
            (1002, "Bo Li", "student", "CSE"),
            (1003, "Chandra Rao", "student", "ECE"),
            (9001, "Dr. Meera Nair", "faculty", ""),
        ]:
            UserRef.objects.update_or_create(
                user_id=uid,
                defaults={"username": f"u{uid}", "display_name": name, "kind": kind,
                          "discipline": disc,
                          "batch_year": 2023 if kind == "student" else None},
            )

        acme, _ = Company.objects.update_or_create(
            slug="acme", defaults={"name": "Acme Corp", "sector": "IT",
                                       "tier_rank": 1, "status": "active"})

        posting, _ = JobPosting.objects.update_or_create(
            company=acme, title="SDE-1", placement_year="2026-27",
            defaults={
                "description": "Build and run backend services for campus systems.",
                "ctc_lpa": "18.00", "seats": 4, "status": "published",
                "eligibility_rule": {"all": [{"gte": ["cpi", 7.0]},
                                             {"in": ["discipline", ["CSE", "ECE"]]}]},
                "eligibility_rule_locked_at": timezone.now(),
                "opens_at": timezone.now(),
                "closes_at": timezone.now() + timedelta(days=14),
                "created_by_user_id": 9001,
            })

        for uid, status in [(1001, "submitted"), (1002, "under_review")]:
            Application.objects.update_or_create(
                posting=posting, user_id=uid,
                defaults={"status": status, "cpi_at_apply": "8.10",
                          "eligibility_snapshot": {"is_eligible": True},
                          "applied_at": timezone.now()})

        # --- SPACS Demo Data ---
        now = timezone.now()
        mcm, _ = SchemeCatalogue.objects.update_or_create(
            code="mcm-scholarship",
            defaults={
                "name": "Merit-cum-Means (MCM) Scholarship",
                "scheme_type": "scholarship",
                "description": "Tuition waiver and monthly stipend for meritorious students from lower-income families.",
                "status": "published",
            },
        )
        mcm_ver, _ = SchemePolicyVersion.objects.update_or_create(
            scheme=mcm,
            version_number=1,
            defaults={
                "title": "MCM Policy 2026-27",
                "description": "Guidelines approved by Senate for MCM award.",
                "eligibility_criteria": {"min_cpi": 6.5, "max_parental_income": 600000},
                "required_documents": [
                    {"type": "income_certificate", "name": "Income Certificate", "required": True},
                    {"type": "grade_sheet", "name": "Latest Grade Sheet", "required": True},
                ],
                "candidate_source_method": "application",
                "is_renewable": True,
                "renewal_rules": {"min_cpi": 6.5, "max_backlogs": 0, "max_years": 4},
                "policy_approval_reference": "Senate Resolution 42.4",
                "policy_approved_by": "Senate",
                "effective_from": now.date() - timedelta(days=30),
                "effective_to": now.date() + timedelta(days=335),
                "application_window_start": now - timedelta(days=10),
                "application_window_end": now + timedelta(days=20),
                "renewal_window_start": now - timedelta(days=10),
                "renewal_window_end": now + timedelta(days=20),
                "status": "published",
            },
        )

        ScholarshipApplication.objects.update_or_create(
            application_number="SPACS-2026-00001",
            defaults={
                "student_user_id": 1001,
                "scheme": mcm,
                "policy_version": mcm_ver,
                "academic_cycle": "2026-27",
                "status": "submitted",
                "submitted_at": now - timedelta(days=2),
                "application_data": {"parental_income": 450000, "cpi": 8.10, "bank_account": "1234567890"},
                "eligibility_snapshot": {"is_eligible": True},
            },
        )

        dgm, _ = SchemeCatalogue.objects.update_or_create(
            code="directors-gold-medal",
            defaults={
                "name": "Director's Gold Medal",
                "scheme_type": "award",
                "description": "For the outstanding graduating student across all disciplines.",
                "status": "published",
            },
        )
        dgm_ver, _ = SchemePolicyVersion.objects.update_or_create(
            scheme=dgm,
            version_number=1,
            defaults={
                "title": "Director's Gold Medal Guidelines 2026",
                "candidate_source_method": "academic_pool",
                "policy_approval_reference": "Board Minute 28.1",
                "policy_approved_by": "Board of Governors",
                "effective_from": now.date() - timedelta(days=60),
                "effective_to": now.date() + timedelta(days=300),
                "status": "published",
            },
        )
        dgm_cycle, _ = AwardCycle.objects.update_or_create(
            scheme=dgm,
            convocation_year=2026,
            defaults={
                "policy_version": dgm_ver,
                "academic_cycle": "2025-26",
                "evaluating_body": "Director's Gold Medal Selection Committee",
                "status": "pool_prepared",
            },
        )
        AwardCandidate.objects.update_or_create(
            award_cycle=dgm_cycle,
            student_user_id=1001,
            defaults={
                "source_method": "academic_pool",
                "cpi": "8.85",
                "discipline": "CSE",
                "is_shortlisted": True,
            },
        )



        self.stdout.write(self.style.SUCCESS("demo data loaded"))
