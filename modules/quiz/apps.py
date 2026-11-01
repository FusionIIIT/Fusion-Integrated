# modules/quiz/apps.py
from django.apps import AppConfig

class QuizConfig(AppConfig):
    name = "modules.quiz"
    label = "quiz"
    verbose_name = "Quiz"

    def ready(self) -> None:
        from . import events  # registers event handlers
        events.register()
