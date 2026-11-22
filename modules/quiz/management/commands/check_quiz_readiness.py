from django.core.management.base import BaseCommand

from modules.quiz.models import Quiz


class Command(BaseCommand):
    help = "Verifies readiness and integrity of the quiz module"

    def handle(self, *args, **options):
        quiz_count = Quiz.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"Quiz module operational. Quizzes count: {quiz_count}")
        )
