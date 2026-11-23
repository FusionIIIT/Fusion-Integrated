from django.db import transaction
from django.shortcuts import get_object_or_404

from core.files.writers import discard_upload, write_upload
from modules.lms.domain import rules
from modules.lms.models import Material, StoredFile
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules, faculty


@enforce_rules
def save_material(scope, data, *, workspace_id=None, pk=None):
    faculty(scope)
    stored = None
    try:
        with transaction.atomic():
            if pk is None:
                row = Material(
                    workspace=scoping.workspace(scope, workspace_id), author_user_id=scope.user_id
                )
            else:
                row = get_object_or_404(
                    scoping.materials(scope).select_for_update(of=("self",)), pk=pk
                )
            data = dict(data)
            upload = data.pop("file", None)
            section_id = data.pop("section_id", row.section_id)
            if section_id is not None:
                section = get_object_or_404(
                    scoping.sections(scope), pk=section_id, workspace_id=row.workspace_id
                )
                row.section = section
            else:
                row.section = None
            for field, value in data.items():
                setattr(row, field, value)
            if row.kind != "FILE":
                row.stored_file = None
            rules.payload(
                row.kind, row.text, row.url, bool(upload or row.stored_file_id), material=True
            )
            if upload:
                stored = write_upload(upload, profile="material", namespace="lms")
                row.stored_file = StoredFile.objects.create(
                    workspace_id=row.workspace_id,
                    owner_user_id=scope.user_id,
                    **stored,
                )
            row.save()
    except Exception:
        # Storage is outside the DB transaction. Remove only the newly staged bytes.
        if stored:
            discard_upload(stored["storage_key"])
        raise
    else:
        return row
