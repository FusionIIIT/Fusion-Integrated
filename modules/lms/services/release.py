from django.db import transaction
from django.utils import timezone
from modules.lms.domain.constants import ContentStatus, ScheduleStatus
from modules.lms.models import Assignment, CourseMaterial, ScheduledRelease


def create_scheduled_release(
    scheduled_date,
    material: CourseMaterial = None,
    assignment: Assignment = None,
) -> ScheduledRelease:
    return ScheduledRelease.objects.create(
        scheduled_date=scheduled_date,
        material=material,
        assignment=assignment,
        status=ScheduleStatus.PENDING,
    )


def process_due_scheduled_releases(batch_size: int = 50) -> int:
    now = timezone.now()
    due_ids = list(
        ScheduledRelease.objects.filter(
            status=ScheduleStatus.PENDING,
            scheduled_date__lte=now,
        ).values_list("id", flat=True)[:batch_size]
    )
    processed_count = 0

    for pk in due_ids:
        with transaction.atomic():
            item = (
                ScheduledRelease.objects.select_for_update(skip_locked=True)
                .filter(id=pk, status=ScheduleStatus.PENDING)
                .first()
            )
            if not item:
                continue
            item.status = ScheduleStatus.PROCESSING
            item.save(update_fields=["status", "updated_at"])
            try:
                if item.material:
                    item.material.status = ContentStatus.PUBLISHED
                    item.material.save(update_fields=["status", "updated_at"])
                elif item.assignment:
                    item.assignment.status = ContentStatus.PUBLISHED
                    item.assignment.save(update_fields=["status", "updated_at"])
                item.status = ScheduleStatus.COMPLETED
                item.processed_at = timezone.now()
                item.save(update_fields=["status", "processed_at", "updated_at"])
                processed_count += 1
            except Exception as e:
                item.status = ScheduleStatus.FAILED
                item.error_message = str(e)
                item.save(update_fields=["status", "error_message", "updated_at"])

    return processed_count
