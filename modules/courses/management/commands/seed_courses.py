"""Seed sample course workspaces and memberships for demonstration and development."""
from django.core.management.base import BaseCommand
from django.db import transaction

from modules.courses.models import CourseMembership, CourseWorkspace
from modules.directory.models import UserRef


class Command(BaseCommand):
    help = "Seed sample course workspaces and enrollments."

    @transaction.atomic
    def handle(self, *args, **options):
        # Create or ensure sample UserRef rows exist
        faculty_user, _ = UserRef.objects.get_or_create(
            user_id=101,
            defaults={
                "username": "fac00001",
                "display_name": "Dr. A. Sharma",
                "kind": "faculty",
                "department": "Computer Science & Engineering",
                "email": "asharma@iiitdmj.ac.in",
            },
        )
        ta_user, _ = UserRef.objects.get_or_create(
            user_id=201,
            defaults={
                "username": "ta00001",
                "display_name": "Priya Patel (TA)",
                "kind": "student",
                "department": "Computer Science & Engineering",
                "email": "priya.ta@iiitdmj.ac.in",
            },
        )
        student_user, _ = UserRef.objects.get_or_create(
            user_id=301,
            defaults={
                "username": "stu00001",
                "display_name": "Rahul Verma",
                "kind": "student",
                "department": "Computer Science & Engineering",
                "email": "rahul.v@iiitdmj.ac.in",
            },
        )
        observer_user, _ = UserRef.objects.get_or_create(
            user_id=401,
            defaults={
                "username": "obs00001",
                "display_name": "Academic Observer",
                "kind": "operator",
                "department": "Academic Affairs",
                "email": "observer@iiitdmj.ac.in",
            },
        )

        # 1. Course: CS201 - Data Structures and Algorithms
        cs201, _ = CourseWorkspace.objects.update_or_create(
            code="CS201",
            semester="Monsoon 2026",
            academic_year="2026-2027",
            defaults={
                "title": "Data Structures and Algorithms",
                "description": (
                    "Fundamental data structures, abstract data types, algorithm analysis, "
                    "sorting, searching, trees, heaps, and graph algorithms."
                ),
                "credits": 4,
                "syllabus": (
                    "### Unit 1: Introduction to Data Structures\n"
                    "- Asymptotic notation, time and space complexity analysis\n"
                    "- Arrays, linked lists, stacks, and queues\n\n"
                    "### Unit 2: Trees and Graphs\n"
                    "- Binary Search Trees, AVL Trees, Red-Black Trees, Heaps\n"
                    "- Graph representations, BFS, DFS, Dijkstra, Prim, Kruskal\n\n"
                    "### Unit 3: Dynamic Programming & Greedy Algorithms\n"
                    "- Memoization vs Tabulation\n"
                    "- Knapsack, Longest Common Subsequence\n"
                ),
                "schedule": (
                    "- Lectures: Mon, Wed, Fri 10:00 - 11:00 AM (Hall L-101)\n"
                    "- Lab: Thursday 2:00 - 5:00 PM (Software Lab 2)"
                ),
                "is_published": True,
                "allow_ta_announcements": True,
            },
        )

        CourseMembership.objects.update_or_create(
            workspace=cs201, user_id=faculty_user.user_id, defaults={"role": "instructor"}
        )
        CourseMembership.objects.update_or_create(
            workspace=cs201, user_id=ta_user.user_id, defaults={"role": "ta"}
        )
        CourseMembership.objects.update_or_create(
            workspace=cs201, user_id=student_user.user_id, defaults={"role": "student"}
        )
        CourseMembership.objects.update_or_create(
            workspace=cs201, user_id=observer_user.user_id, defaults={"role": "observer"}
        )

        # 2. Course: CS302 - Database Management Systems
        cs302, _ = CourseWorkspace.objects.update_or_create(
            code="CS302",
            semester="Monsoon 2026",
            academic_year="2026-2027",
            defaults={
                "title": "Database Management Systems",
                "description": (
                    "Relational database design, relational algebra, SQL, normalization, "
                    "indexing, transaction management, and concurrency control."
                ),
                "credits": 4,
                "syllabus": (
                    "### Unit 1: Relational Model & SQL\n"
                    "- Entity-Relationship diagrams, relational algebra\n"
                    "- Advanced SQL queries, constraints, views\n\n"
                    "### Unit 2: Database Design & Normalization\n"
                    "- Functional dependencies, 1NF, 2NF, 3NF, BCNF\n\n"
                    "### Unit 3: Transactions & Storage\n"
                    "- ACID properties, serializability, two-phase locking\n"
                    "- B+ Trees, hashing\n"
                ),
                "schedule": (
                    "- Lectures: Tue, Thu 09:00 - 10:30 AM (Room CR-204)\n"
                    "- Lab: Tuesday 2:00 - 5:00 PM (Database Lab)"
                ),
                "is_published": True,
                "allow_ta_announcements": False,
            },
        )

        CourseMembership.objects.update_or_create(
            workspace=cs302, user_id=faculty_user.user_id, defaults={"role": "instructor"}
        )
        CourseMembership.objects.update_or_create(
            workspace=cs302, user_id=student_user.user_id, defaults={"role": "student"}
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded course workspaces and memberships."))
