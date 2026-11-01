from django.db import transaction
from modules.mess.models import Feedback, Announcement
from modules.mess.services._audit import record_transition, queue_notification

@transaction.atomic
def submit_feedback(user_id, text):
    if not text.strip():
        raise ValueError("Feedback text cannot be blank")
    feedback = Feedback(user_id=user_id, text=text)
    feedback.save()
    return feedback

@transaction.atomic
def publish_announcement(author_user_id, author_role, title, body):
    if author_role not in ['CARETAKER', 'WARDEN']:
        raise ValueError("Invalid author role. Must be CARETAKER or WARDEN")
    if not title.strip() or not body.strip():
        raise ValueError("Title and body cannot be blank")
    announcement = Announcement(author_user_id=author_user_id, author_role=author_role, title=title, body=body)
    announcement.save()
    queue_notification('ANNOUNCEMENT_PUBLISHED', 0, {'announcement_id': announcement.id})
    return announcement
