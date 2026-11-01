from modules.lms.models import Material, Submission


def materials(workspace, role):
    rows = workspace.materials.order_by("section", "id")
    return rows if role == "faculty" else rows.filter(state="published")


def assignments(workspace, role):
    rows = workspace.assignments.order_by("due_at")
    if role == "observer":
        return rows.none()
    return rows if role == "faculty" else rows.filter(state="published")


def submissions(workspace, role, user_id):
    rows = (
        Submission.objects.filter(assignment__workspace=workspace)
        .select_related("assignment")
        .order_by("-id")
    )
    if role == "observer":
        return rows.none()
    return rows.filter(student_id=user_id) if role == "student" else rows


def scheduled_materials(now):
    return Material.objects.filter(state="scheduled", release_at__lte=now)
