import pytest
from django.db import transaction

from core.events.models import OutboxEvent
from core.events.outbox import emit


@pytest.mark.django_db
def test_emit_persists_event():
    event = emit(
        "leave.request.created", {"leave_request_id": 17}, dedupe_key="leave_request.created:17"
    )

    assert OutboxEvent.objects.get(pk=event.pk).payload == {"leave_request_id": 17}


@pytest.mark.django_db
def test_emit_is_idempotent_for_duplicate_key():
    first = emit(
        "leave.request.created", {"leave_request_id": 17}, dedupe_key="leave_request.created:17"
    )
    second = emit(
        "leave.request.created", {"leave_request_id": 17}, dedupe_key="leave_request.created:17"
    )

    assert second.pk == first.pk
    assert OutboxEvent.objects.count() == 1


@pytest.mark.django_db
def test_emit_rolls_back_with_callers_transaction():
    with pytest.raises(RuntimeError), transaction.atomic():
        emit(
            "leave.request.created", {"leave_request_id": 17}, dedupe_key="leave_request.created:17"
        )
        raise RuntimeError("rollback")

    assert OutboxEvent.objects.count() == 0
