from collections.abc import Sequence

from modules.fts.models import File


def get_files_by_ids(file_ids: Sequence[int]) -> list[dict]:
    if not file_ids:
        return []
    files = File.objects.filter(id__in=list(file_ids))
    return [
        {
            "id": file_obj.id,
            "title": file_obj.title,
            "status": file_obj.status,
            "creator_id": file_obj.creator_id,
            "current_holder_id": file_obj.current_holder_id,
        }
        for file_obj in files
    ]