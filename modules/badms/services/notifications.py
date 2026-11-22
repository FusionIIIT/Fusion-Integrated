from modules.badms.models import NotificationOutbox


def enqueue(recipients, *, subject: str, body: str) -> None:
    for recipient in {value.strip() for value in recipients if value and value.strip()}:
        NotificationOutbox.objects.create(recipient=recipient, subject=subject, body=body)
