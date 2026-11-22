from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PmsPrivateStorage(FileSystemStorage):
    """Private local storage; PMS files are never served by a public static path."""

    def __init__(self):
        super().__init__(
            location=settings.PMS_UPLOAD_ROOT,
            base_url=None,
            file_permissions_mode=0o600,
            directory_permissions_mode=0o700,
        )
