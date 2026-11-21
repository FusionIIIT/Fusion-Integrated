from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from modules.fts.domain.commands import archive_file
from modules.fts.models import FtsAuditLog, FtsFile


def archive_file_service(actor_id: str, file_id: str) -> FtsFile:
    try:
        file = FtsFile.objects.get(id=file_id)
    except ObjectDoesNotExist as err:
        raise ValueError("File not found.") from err

    if str(file.owner_id) != actor_id:
        raise ValueError("Only the file owner can archive the file.")

    domain_command_result = archive_file(
        current_status=file.status,
        owner_id=str(file.owner_id),
        actor_id=actor_id
    )

    with transaction.atomic():
        file.status = domain_command_result['new_status']
        file.save()

        FtsAuditLog.objects.create(
            file_id=file.id,
            actor_id=actor_id,
            action='ARCHIVE',
            details={
                'file_id': str(file.id),
                'actor_id': actor_id
            }
        )

    return file
