from modules.department.models import Department


def unmet_prerequisites() -> list[str]:
    if not Department.objects.exists():
        return ["No departments exist yet. Run `python manage.py seed_departments` to create them."]
    return []
