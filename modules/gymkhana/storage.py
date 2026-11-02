from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class GymkhanaFileStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(
            location=settings.GYMKHANA_UPLOAD_ROOT,
            file_permissions_mode=0o600,
            directory_permissions_mode=0o700,
        )

    def deconstruct(self):
        return "modules.gymkhana.storage.GymkhanaFileStorage", (), {}
