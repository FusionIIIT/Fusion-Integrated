"""Access scoping and association checks for FTS files."""
from __future__ import annotations

from django.db.models import Q

from core.api.exceptions import NotFoundError
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement


def get_file_for_user(file_id: int, user_id: int, *, is_admin: bool = False) -> File:
    """Retrieves a file if the user is associated with it or is an authorized admin."""
    try:
        file_obj = File.objects.get(id=file_id)
    except File.DoesNotExist as e:
        raise NotFoundError(f"File #{file_id} was not found.") from e

    if is_admin:
        return file_obj

    if is_user_associated(file_obj, user_id):
        return file_obj

    raise NotFoundError(f"File #{file_id} was not found.")


def is_user_associated(file_obj: File, user_id: int) -> bool:
    """Returns True if the user is owner, holder, or participated in file movements."""
    if file_obj.owner_user_id == user_id or file_obj.current_holder_user_id == user_id:
        return True

    return FileMovement.objects.filter(
        file=file_obj
    ).filter(
        Q(from_user_id=user_id) | Q(to_user_id=user_id)
    ).exists()
