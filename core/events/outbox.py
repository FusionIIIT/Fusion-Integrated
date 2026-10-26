from .models import OutboxEvent


def emit(topic: str, payload: dict, *, dedupe_key: str) -> OutboxEvent:
    """Persist an event in the caller's transaction, idempotently."""
    event, _ = OutboxEvent.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={"topic": topic, "payload": payload},
    )
    return event
