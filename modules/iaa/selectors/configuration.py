from modules.iaa.models import DepartmentBudget, IAAConfiguration


def get_active_configuration() -> IAAConfiguration:
    config = IAAConfiguration.objects.filter(is_active=True).first()
    if not config:
        config = IAAConfiguration.objects.create(
            financial_year="2026-2027",
            high_value_ta_threshold=50000.00,
            approval_timeout_days=3,
            is_active=True,
        )
    return config


def get_department_budget(
    department: str, financial_year: str | None = None
) -> DepartmentBudget | None:
    if not financial_year:
        config = get_active_configuration()
        financial_year = config.financial_year
    return DepartmentBudget.objects.filter(
        department=department, financial_year=financial_year
    ).first()
