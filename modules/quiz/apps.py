from django.apps import AppConfig


class QuizConfig(AppConfig):
    name = "modules.quiz"
    label = "quiz"
    verbose_name = "Quiz"

    def ready(self) -> None:
        pass  # Reserved for event registration when needed
