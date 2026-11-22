"""Lab resource services (CFR-DEPT-012)."""

from __future__ import annotations

from modules.dept.models.department import Department
from modules.dept.models.labs import LabResource


def save_lab_resource(
    department_code: str,
    lab_name: str,
    location: str,
    description: str = "",
    equipment_details: list | None = None,
    in_charge_id: str = "",
    lab_id: str | None = None,
) -> LabResource:
    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    if lab_id:
        lab = LabResource.objects.get(id=lab_id, department=dept)
        lab.lab_name = lab_name.strip()
        lab.location = location.strip()
        lab.description = description.strip()
        lab.equipment_details = equipment_details or []
        lab.in_charge_id = in_charge_id.strip()
        lab.save()
        return lab

    return LabResource.objects.create(
        department=dept,
        lab_name=lab_name.strip(),
        location=location.strip(),
        description=description.strip(),
        equipment_details=equipment_details or [],
        in_charge_id=in_charge_id.strip(),
    )
