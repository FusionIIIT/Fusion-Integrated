from collections.abc import Sequence

from modules.dept.models import Department


def get_departments(department_codes: Sequence[str]) -> dict[str, dict]:
    """Read a batch of public DEPT department summaries."""
    codes = {str(code).strip().upper() for code in department_codes if code}
    return {
        department.code: {
            "code": department.code,
            "name": department.name,
            "general_info": department.general_info,
            "official_info": department.official_info,
        }
        for department in Department.objects.filter(code__in=codes)
    }
