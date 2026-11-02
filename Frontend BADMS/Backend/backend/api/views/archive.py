import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes

from ..permissions import Privileged
from ..services import archive as service
from ..services.archive import ServiceError

logger = logging.getLogger(__name__)

_STUDENT_FILTERS = ("programme", "batch", "discipline", "category", "gender")
_FACULTY_FILTERS = ("department", "designation", "gender")


def _run(fn, *args):
    try:
        return JsonResponse(fn(*args))
    except ServiceError as exc:
        return JsonResponse(exc.payload, status=exc.status)
    except Exception:
        logger.exception("Unhandled error in archive service")
        return JsonResponse({"success": False, "message": "An unexpected error occurred."}, status=500)


@api_view(["GET"])
def list_people(request):
    user_type = request.GET.get("type", "student")
    archived = request.GET.get("status") == "archived"
    keys = _FACULTY_FILTERS if user_type == "faculty" else _STUDENT_FILTERS
    filters = {k: request.GET.get(k) for k in keys if request.GET.get(k)}
    return _run(service.list_people, user_type, archived, filters)


@api_view(["POST"])
@permission_classes(Privileged)
def archive_people(request):
    return _run(
        service.archive_users,
        request.data.get("usernames") or [],
        request.data.get("type", "student"),
        request.data.get("action", "archive"),
        getattr(request.user, "username", ""),
    )


@api_view(["POST"])
@permission_classes(Privileged)
def restore_people(request):
    return _run(
        service.restore_users,
        request.data.get("usernames") or [],
        request.data.get("type", "student"),
        getattr(request.user, "username", ""),
    )
