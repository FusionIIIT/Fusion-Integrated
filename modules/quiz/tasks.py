from celery import shared_task
from django.utils import timezone

from modules.quiz.models import Quiz
from modules.quiz.services.attempt_service import auto_submit_expired_attempts


@shared_task
def process_quiz_availability_boundaries():
    now = timezone.now()
    # SCHEDULED -> AVAILABLE
    Quiz.objects.filter(status="SCHEDULED", start_at__lte=now).update(status="AVAILABLE")
    # AVAILABLE -> CLOSED
    Quiz.objects.filter(status="AVAILABLE", close_at__lte=now).update(status="CLOSED")


@shared_task
def auto_submit_expired_attempts_task():
    auto_submit_expired_attempts()
