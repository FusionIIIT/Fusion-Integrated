from django.conf import settings
from django.core.files.storage import FileSystemStorage

gymkhana_upload_storage = FileSystemStorage(
    location=settings.PLACEMENT_UPLOAD_ROOT,
    base_url=None,
)
