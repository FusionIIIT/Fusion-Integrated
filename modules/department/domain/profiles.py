BASIC = frozenset({"name", "programme", "department"})
LIMITED = BASIC | frozenset({"email", "title", "office"})
DETAILED = LIMITED | frozenset({"username", "discipline", "batch_year"})
FULL = DETAILED | frozenset({"bio", "graduation_year", "is_active", "record_kind"})

def visible_fields(viewer_kind, target_kind, in_course):
    if viewer_kind in ("hod", "dept_admin"):
        return FULL
    if viewer_kind == "student":
        if target_kind in ("student", "faculty"):
            return BASIC
        if target_kind == "alumni":
            return None
    elif viewer_kind == "faculty":
        if target_kind == "student":
            return DETAILED if in_course else BASIC
        if target_kind in ("faculty", "alumni"):
            return LIMITED
    return None
