from modules.badms.models import AuditEvent


def send_backup_failure_alert(backup_record) -> AuditEvent:
    return AuditEvent.objects.create(
        event_type="backup_failure_alert_sent",
        actor_user_id=backup_record.triggered_by_user_id or 0,
        actor_role="system",
        target_model="BackupRecord",
        target_id=backup_record.id,
        details={
            "recipient_role": "SysAdmin",
            "dataset_name": backup_record.dataset_name,
            "error_message": backup_record.error_message,
        },
    )


def send_backup_failure_escalation(backup_record) -> AuditEvent:
    return AuditEvent.objects.create(
        event_type="backup_failure_escalated",
        actor_user_id=backup_record.triggered_by_user_id or 0,
        actor_role="system",
        target_model="BackupRecord",
        target_id=backup_record.id,
        details={
            "recipient_role": "Director of IT",
            "consecutive_failures": backup_record.consecutive_failure_count,
            "dataset_name": backup_record.dataset_name,
            "severity": "CRITICAL",
        },
    )
