from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = "modules.courses"
    label = "courses"
    verbose_name = "Course Management"
    default_auto_field = "django.db.models.BigAutoField"
