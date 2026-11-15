from django.apps import AppConfig


class QuizzingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.quizzing"
    label = "quizzing"
    verbose_name = "Quizzing & Assessment"
