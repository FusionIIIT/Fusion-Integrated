from django.apps import AppConfig


class QuizConfig(AppConfig):
    name = "modules.quiz"
    label = "quiz"
    verbose_name = "Quiz Management"
    default_auto_field = "django.db.models.BigAutoField"
