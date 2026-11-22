HOD_DEPARTMENTS = {
    "HOD (CSE)": "CSE",
    "HOD (Design)": "Design",
    "HOD (ECE)": "ECE",
    "HOD (ME)": "ME",
    "HOD (NS)": "Natural Science",
}

ADMIN_DEPARTMENTS = {
    "deptadmin_cse": "CSE",
    "deptadmin_design": "Design",
    "deptadmin_ece": "ECE",
    "deptadmin_me": "ME",
    "deptadmin_ns": "Natural Science",
    "deptadmin_sm": "SM",
}

STUDENT_ROLES = {"student", "ug_student", "pg_student", "phd_student"}


def acting_role(principal):
    return principal.active_role or principal.kind


def audience_role(principal):
    role = acting_role(principal)
    return "student" if role in STUDENT_ROLES else role
