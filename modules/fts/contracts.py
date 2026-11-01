from modules.fts.selectors.file_selectors import get_file_by_id


def get_file_detail_contract(file_id: int):
    """Cross-module contract providing read-only access to file metadata."""
    file_obj = get_file_by_id(file_id)
    if not file_obj:
        return None
    return {
        "id": file_obj.id,
        "title": file_obj.title,
        "status": file_obj.status,
        "creator_id": file_obj.creator_id,
        "current_holder_id": file_obj.current_holder_id,
    }