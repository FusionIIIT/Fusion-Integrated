"""Private, repository-external storage for IAA evidence files."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateEvidenceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.IAA_UPLOAD_ROOT, base_url=None,
                         file_permissions_mode=0o600,
                         directory_permissions_mode=0o700)
