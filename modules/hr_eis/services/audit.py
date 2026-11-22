from modules.hr_eis.models.audit import AuditLog, NotificationRecord

class AuditService:
    @staticmethod
    def log(entity_type, entity_id, actor, action, from_state="", to_state="", details=""):
        return AuditLog.objects.create(
            module="hr_eis",
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor=actor,
            action=action,
            from_state=from_state,
            to_state=to_state,
            details=details,
        )

    @staticmethod
    def notify(recipient, title, message, category="Event"):
        return NotificationRecord.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            category=category,
        )
