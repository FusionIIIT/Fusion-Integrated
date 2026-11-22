"""Scoping and visibility chokepoint for File Tracking System (BR-FTS-009)."""

from django.db.models import Q
from django.http import Http404

from modules.filetracking.models import FileMovement, TrackedFile


def is_user_associated_with_file(file: TrackedFile, user_id: int) -> bool:
    """Check whether a user is associated with a file (BR-FTS-009)."""
    if file.created_by_user_id == user_id:
        return True
    if file.current_holder_user_id == user_id:
        return True
    return FileMovement.objects.filter(
        Q(file=file) & (Q(sender_user_id=user_id) | Q(receiver_user_id=user_id))
    ).exists()


def get_associated_file_or_404(file_id: int, user_id: int) -> TrackedFile:
    """Return file if user is associated; yield 404 never 403 to prevent probing."""
    try:
        file = TrackedFile.objects.prefetch_related("movements", "attachments").get(id=file_id)
    except TrackedFile.DoesNotExist:
        raise Http404("File not found.") from None

    if not is_user_associated_with_file(file, user_id):
        raise Http404("File not found.")

    return file
