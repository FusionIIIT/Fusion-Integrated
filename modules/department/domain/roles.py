# modules/department/domain/roles.py
def role_kind(active_role: str) -> str | None:
    """Maps an active role string to a standardized role kind."""
    if not active_role:
        return None
    if active_role == "student":
        return "student"
    if active_role == "faculty":
        return "faculty"
    if active_role == "acadadmin":
        return "institute_admin"
    if active_role.startswith("HOD ("):
        return "hod"
    if active_role == "dept_admin" or active_role.startswith("deptadmin_"):
        return "dept_admin"
    return None
