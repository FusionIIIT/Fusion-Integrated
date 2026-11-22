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
from modules.quiz.models import AttemptResponse, Question, Quiz, QuizAttempt


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

        # Demo Quiz Data
        quiz1, _ = Quiz.objects.update_or_create(
            title="CS201 Data Structures Midterm",
            course="CS201",
            defaults={
                "description": "Midterm assessment covering trees, sorting, and graphs.",
                "instructions": "Attempt all questions. Calculators are not allowed.",
                "status": "available",
                "duration_minutes": 30,
                "max_marks": 20,
                "passing_marks": 8,
                "max_attempts": 2,
                "allow_back_navigation": True,
                "one_question_at_a_time": False,
                "allow_unanswered": True,
                "tab_block": True,
                "result_visibility": "after_release",
                "created_by_user_id": 9001,
            },
        )

        q1, _ = Question.objects.update_or_create(
            quiz=quiz1,
            order=1,
            defaults={
                "question_type": "mcq",
                "text": "What is the worst-case time complexity of standard QuickSort?",
                "marks": 5,
                "negative_marks": 1,
                "topic": "Algorithms",
                "difficulty": "medium",
                "is_bank_question": True,
                "options": [
                    {"id": "opt_1", "text": "O(n)"},
                    {"id": "opt_2", "text": "O(n log n)"},
                    {"id": "opt_3", "text": "O(n^2)"},
                    {"id": "opt_4", "text": "O(log n)"},
                ],
                "correct_answer": "opt_3",
            },
        )

        q2, _ = Question.objects.update_or_create(
            quiz=quiz1,
            order=2,
            defaults={
                "question_type": "tf",
                "text": (
                    "In a binary search tree, an in-order traversal yields "
                    "elements in sorted ascending order."
                ),
                "marks": 5,
                "negative_marks": 0,
                "topic": "Trees",
                "difficulty": "easy",
                "is_bank_question": True,
                "correct_answer": True,
            },
        )

        q3, _ = Question.objects.update_or_create(
            quiz=quiz1,
            order=3,
            defaults={
                "question_type": "short",
                "text": (
                    "Explain the architectural difference between a Stack and a Queue, "
                    "providing one real-world application for each."
                ),
                "marks": 10,
                "negative_marks": 0,
                "topic": "Data Structures",
                "difficulty": "medium",
                "is_bank_question": False,
                "reference_answer": (
                    "Stack is LIFO (e.g., undo stack or function call recursion). "
                    "Queue is FIFO (e.g., CPU scheduler or print spooler)."
                ),
                "evaluation_criteria": (
                    "5 marks for correct LIFO/FIFO explanation, "
                    "5 marks for valid real-world examples."
                ),
            },
        )

        # Demo Student Submission for Evaluation & Reports
        attempt1, _ = QuizAttempt.objects.update_or_create(
            quiz=quiz1,
            user_id=1001,
            attempt_number=1,
            defaults={
                "status": "partially_evaluated",
                "started_at": timezone.now() - timedelta(minutes=25),
                "submitted_at": timezone.now() - timedelta(minutes=5),
                "score": 10,
                "percentage": 50,
                "passed": True,
                "time_taken_seconds": 1200,
                "tab_violations": 0,
            },
        )

        AttemptResponse.objects.update_or_create(
            attempt=attempt1,
            question=q1,
            defaults={
                "response": "opt_3",
                "is_correct": True,
                "marks_obtained": 5,
            },
        )

        AttemptResponse.objects.update_or_create(
            attempt=attempt1,
            question=q2,
            defaults={
                "response": True,
                "is_correct": True,
                "marks_obtained": 5,
            },
        )

        AttemptResponse.objects.update_or_create(
            attempt=attempt1,
            question=q3,
            defaults={
                "response": (
                    "A stack operates on Last-In First-Out principle like browser history undo. "
                    "A queue is First-In First-Out like printer jobs."
                ),
                "is_correct": None,
                "marks_obtained": None,
                "ai_suggested_marks": 9.0,
                "ai_reasoning": (
                    "Correctly defines LIFO and FIFO with accurate real-world examples "
                    "(browser history, printer jobs). Well articulated."
                ),
                "professor_feedback": "",
            },
        )

        # Demo Draft Quiz
        Quiz.objects.update_or_create(
            title="CS302 Computer Networks Quiz 1",
            course="CS302",
            defaults={
                "description": "Introductory quiz on the OSI model and TCP/IP stack.",
                "instructions": "Draft version - pending review by course instructor.",
                "status": "draft",
                "duration_minutes": 20,
                "max_marks": 15,
                "passing_marks": 6,
                "max_attempts": 1,
                "created_by_user_id": 9001,
            },
        )



        self.stdout.write(self.style.SUCCESS("demo data loaded"))
