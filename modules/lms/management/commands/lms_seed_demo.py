from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

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


class Command(BaseCommand):
    help = "Seeds idempotent demo workspaces, memberships and content for LMS module."

    def handle(self, *args, **options):
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
        self.stdout.write(self.style.SUCCESS("LMS demo data loaded successfully"))
