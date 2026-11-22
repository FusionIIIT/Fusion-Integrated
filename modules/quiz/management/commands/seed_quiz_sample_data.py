from django.core.management.base import BaseCommand

from modules.quiz.models import Quiz, QuizOption, QuizQuestion, QuizSettings


class Command(BaseCommand):
    help = "Seeds initial sample quiz data for local testing"

    def handle(self, *args, **options):
        quiz, created = Quiz.objects.get_or_create(
            title="Sample Placement Readiness Quiz",
            course_id=101,
            created_by_user_id=1,
            defaults={
                "instructions": "Answer all questions within 30 minutes.",
                "duration_minutes": 30,
                "max_attempts": 2,
                "status": "AVAILABLE",
            },
        )
        QuizSettings.objects.get_or_create(quiz=quiz)
        if created:
            q = QuizQuestion.objects.create(
                quiz=quiz,
                question_text="What is the time complexity of binary search on a sorted array?",
                question_type="MCQ",
                marks=5,
                negative_marks=1,
                correct=["O(log n)"],
                position=1,
            )
            for opt_id, text in [
                ("A", "O(n)"),
                ("B", "O(log n)"),
                ("C", "O(n log n)"),
                ("D", "O(1)"),
            ]:
                QuizOption.objects.create(question=q, option_id=opt_id, option_text=text)
        self.stdout.write(self.style.SUCCESS(f"Sample quiz ready (id={quiz.pk})"))
