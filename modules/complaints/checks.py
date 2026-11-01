from pathlib import Path

from django.conf import settings
from django.core.checks import Error


def check_configuration(app_configs, **kwargs):
    errors = []
    root = Path(settings.COMPLAINT_ATTACHMENT_ROOT).expanduser().resolve()
    base = Path(settings.BASE_DIR).resolve()
    if root == base or base in root.parents:
        errors.append(Error(
            "Complaint attachment storage is inside the project tree.",
            hint="Set COMPLAINT_ATTACHMENT_ROOT to a private directory outside the repository.",
            id="fusion.complaints.E001",
        ))
    max_bytes = settings.COMPLAINT_ATTACHMENT_MAX_BYTES
    if max_bytes is not None and max_bytes < 1:
        errors.append(Error(
            "COMPLAINT_ATTACHMENT_MAX_BYTES must be a positive integer.",
            id="fusion.complaints.E002",
        ))
    max_count = settings.COMPLAINT_ATTACHMENT_MAX_COUNT
    if max_count is not None and max_count < 0:
        errors.append(Error(
            "COMPLAINT_ATTACHMENT_MAX_COUNT cannot be negative.",
            id="fusion.complaints.E003",
        ))
    if settings.COMPLAINT_NOTIFICATION_MAX_ATTEMPTS < 1:
        errors.append(Error(
            "COMPLAINT_NOTIFICATION_MAX_ATTEMPTS must be positive.",
            id="fusion.complaints.E004",
        ))
    return errors
