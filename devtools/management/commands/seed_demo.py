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

        # LMS demo data
        from modules.lms.domain.constants import (
            AssignmentStatus,
            CourseRole,
            MaterialStatus,
            MaterialType,
            MembershipStatus,
            SubmissionType,
        )
        from modules.lms.models import (
            Assignment,
            CourseAnnouncement,
            CourseMaterial,
            CourseMembership,
            CourseWorkspace,
        )

        CourseWorkspace.objects.update_or_create(
            course_id=101,
            defaults={
                "course_code": "CS101",
                "title": "Computer Science 101",
                "syllabus": "Data structures, algorithms, and modular design.",
                "schedule_info": "MWF 10:00 - 11:00 AM, Hall 1",
            },
        )
        CourseMembership.objects.update_or_create(
            course_id=101,
            user_id=5328,
            defaults={
                "role": CourseRole.INSTRUCTOR,
                "status": MembershipStatus.ACTIVE,
                "can_grade": True,
                "can_post_announcement": True,
            },
        )
        CourseMembership.objects.update_or_create(
            course_id=101,
            user_id=6565,
            defaults={"role": CourseRole.STUDENT, "status": MembershipStatus.ACTIVE},
        )
        CourseMembership.objects.update_or_create(
            course_id=101,
            user_id=4093,
            defaults={
                "role": CourseRole.TA,
                "status": MembershipStatus.ACTIVE,
                "can_grade": True,
                "can_post_announcement": True,
            },
        )
        CourseMembership.objects.update_or_create(
            course_id=101,
            user_id=3298,
            defaults={"role": CourseRole.OBSERVER, "status": MembershipStatus.ACTIVE},
        )
        CourseAnnouncement.objects.update_or_create(
            course_id=101,
            title="Welcome to CS101",
            defaults={
                "content": "Welcome to Computer Science 101! Classes start this Monday.",
                "author_id": 5328,
                "author_role": CourseRole.INSTRUCTOR,
            },
        )
        CourseMaterial.objects.update_or_create(
            course_id=101,
            title="Syllabus & Lecture Notes",
            defaults={
                "material_type": MaterialType.NOTE,
                "content_text": "Read Chapter 1 before Wednesday.",
                "status": MaterialStatus.PUBLISHED,
                "uploaded_by": 5328,
            },
        )
        Assignment.objects.update_or_create(
            course_id=101,
            title="Assignment 1: Algorithms Analysis",
            defaults={
                "instructions": "Implement and analyze binary search and quicksort.",
                "points_possible": "100.00",
                "submission_type": SubmissionType.TEXT,
                "due_date": timezone.now() + timedelta(days=7),
                "status": AssignmentStatus.PUBLISHED,
                "created_by": 5328,
            },
        )



        self.stdout.write(self.style.SUCCESS("demo data loaded"))
