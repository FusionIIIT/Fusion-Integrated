import logging

from django.db import transaction
from django.db.models import Q

from ..models import ArchiveLog, AuthUser, GlobalsExtrainfo, GlobalsFaculty, Student

logger = logging.getLogger(__name__)

ACTIVE_STATUS = "PRESENT"
STATUS_FOR_ACTION = {"archive": "ARCHIVED", "alumni": "ALUMNI"}
ARCHIVED_STATUSES = {"ARCHIVED", "ALUMNI", "LEFT"}


class ServiceError(Exception):
    def __init__(self, payload, status=400):
        super().__init__(payload.get("message", "Service error"))
        self.payload = payload
        self.status = status


def _is_archived(user, extra):
    return (not user.is_active) or (extra.user_status in ARCHIVED_STATUSES)


def _designations(user):
    return sorted({hd.designation.name for hd in user.holds_designations.all()})


def _serialize_student(student):
    extra = student.id
    user = extra.user
    batch = student.batch_id
    return {
        "username": user.username,
        "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "email": user.email,
        "programme": student.programme,
        "discipline": batch.discipline.name if batch and batch.discipline else (extra.department.name if extra.department else ""),
        "batch": student.batch,
        "category": student.category,
        "gender": extra.sex,
        "curr_semester_no": student.curr_semester_no,
        "user_status": extra.user_status,
        "is_active": user.is_active,
        "archived": _is_archived(user, extra),
    }


def _serialize_faculty(faculty):
    extra = faculty.id
    user = extra.user
    return {
        "username": user.username,
        "full_name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "email": user.email,
        "department": extra.department.name if extra.department else "",
        "designation": ", ".join(_designations(user)),
        "gender": extra.sex,
        "user_status": extra.user_status,
        "is_active": user.is_active,
        "archived": _is_archived(user, extra),
    }


def _status_filter(archived):
    archived_q = Q(id__user__is_active=False) | Q(id__user_status__in=ARCHIVED_STATUSES)
    return archived_q if archived else ~archived_q


def list_people(user_type, archived=False, filters=None):
    filters = filters or {}
    archived = bool(archived)

    if user_type == "faculty":
        qs = (
            GlobalsFaculty.objects.select_related("id", "id__user", "id__department")
            .prefetch_related("id__user__holds_designations__designation")
            .filter(_status_filter(archived))
        )
        if filters.get("department"):
            qs = qs.filter(id__department__name__iexact=filters["department"])
        if filters.get("gender"):
            qs = qs.filter(id__sex__iexact=filters["gender"])
        if filters.get("designation"):
            qs = qs.filter(
                id__user__holds_designations__designation__name__iexact=filters["designation"]
            ).distinct()
        rows = [_serialize_faculty(f) for f in qs]
    else:
        qs = (
            Student.objects.select_related("id", "id__user", "id__department", "batch_id", "batch_id__discipline")
            .filter(_status_filter(archived))
        )
        if filters.get("programme"):
            qs = qs.filter(programme__iexact=filters["programme"])
        if filters.get("batch"):
            qs = qs.filter(batch=filters["batch"])
        if filters.get("discipline"):
            qs = qs.filter(batch_id__discipline__name__iexact=filters["discipline"])
        if filters.get("category"):
            qs = qs.filter(category__iexact=filters["category"])
        if filters.get("gender"):
            qs = qs.filter(id__sex__iexact=filters["gender"])
        rows = [_serialize_student(s) for s in qs]

    return {"success": True, "results": rows, "count": len(rows)}


def _apply(usernames, user_type, action, new_status, active, operator):
    if not usernames:
        raise ServiceError({"success": False, "message": "No users selected."})

    done, failed = [], []
    with transaction.atomic():
        for uname in usernames:
            user = AuthUser.objects.filter(username__iexact=uname).first()
            extra = GlobalsExtrainfo.objects.filter(user=user).first() if user else None
            if not user or not extra:
                failed.append(uname)
                continue
            previous = extra.user_status
            extra.user_status = new_status
            extra.save(update_fields=["user_status"])
            user.is_active = active
            user.save(update_fields=["is_active"])
            ArchiveLog.objects.create(
                username=user.username,
                user_type=user_type,
                action=action,
                previous_status=previous,
                new_status=new_status,
                performed_by=operator or "",
            )
            done.append(user.username)
    return done, failed


def archive_users(usernames, user_type, action, operator=""):
    if action not in STATUS_FOR_ACTION:
        raise ServiceError({"success": False, "message": "Invalid action. Use 'archive' or 'alumni'."})
    if user_type not in ("student", "faculty"):
        raise ServiceError({"success": False, "message": "Invalid user type."})

    new_status = STATUS_FOR_ACTION[action]
    done, failed = _apply(usernames, user_type, action, new_status, active=False, operator=operator)
    verb = "moved to alumni" if action == "alumni" else "archived"
    return {
        "success": True,
        "processed": done,
        "failed": failed,
        "message": f"{len(done)} {user_type}(s) {verb} and deactivated." + (f" {len(failed)} not found." if failed else ""),
    }


def restore_users(usernames, user_type, operator=""):
    if user_type not in ("student", "faculty"):
        raise ServiceError({"success": False, "message": "Invalid user type."})

    done, failed = _apply(usernames, user_type, "restore", ACTIVE_STATUS, active=True, operator=operator)
    return {
        "success": True,
        "processed": done,
        "failed": failed,
        "message": f"{len(done)} {user_type}(s) restored and reactivated." + (f" {len(failed)} not found." if failed else ""),
    }
