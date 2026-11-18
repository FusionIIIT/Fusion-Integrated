import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PsmStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(base_url=None)

    @property
    def location(self):
        return str(
            Path(
                getattr(
                    settings,
                    "PSM_UPLOAD_ROOT",
                    Path.home() / ".local/share/fusion-integrated/psm-uploads",
                )
            ).resolve()
        )

    @property
    def base_location(self):
        return self.location


def attachment_path(instance, filename):
    return str(uuid.uuid4())
