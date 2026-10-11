"""HR module registry entry and permissions."""
from core.registry import ModuleManifest as M, NavItem as N, Permission as P

MODULE = M(
    code="hr",
    label="Human Resources",
    icon="FaUsers",
    base_path="/hr",
    nav_section="Administration",
    sort_order=200,
    status="active",
)

PERMISSIONS = [
    P("hr.department.view",    "View department structure"),
    P("hr.department.manage",  "Create and edit departments"),
    P("hr.employee.view",      "View employee profiles and contracts"),
    P("hr.employee.manage",    "Create, update and end employment contracts"),
]

NAV_ITEMS = [
    N("hr.departments", "Departments", "FaBuilding", "/hr/departments",
      required_permission="hr.department.view"),
    N("hr.employees",   "Employees",   "FaUsers",    "/hr/employees",
      required_permission="hr.employee.view"),
]

SYSTEM_PERMISSIONS: list[str] = []

ROLE_GRANTS: dict[str, list[str]] = {
    "hr_officer": [
        "hr.department.view",
        "hr.department.manage",
        "hr.employee.view",
        "hr.employee.manage",
    ],
    "faculty": [
        "hr.department.view",
    ],
    "staff": [
        "hr.department.view",
    ],
}
