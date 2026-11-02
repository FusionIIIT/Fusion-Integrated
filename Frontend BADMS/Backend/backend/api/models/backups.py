import uuid

from django.db import models


class BackupRecord(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    db_name = models.CharField(
        max_length=200, help_text="Name of the database that was backed up"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )
    size_bytes = models.BigIntegerField(
        default=0, help_text="Size of the backup file in bytes"
    )
    duration_ms = models.BigIntegerField(
        default=0, help_text="Duration of the backup in milliseconds"
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Path to the backup file on disk",
    )
    error_message = models.TextField(
        blank=True, default="", help_text="Error message if backup failed"
    )
    encrypted = models.BooleanField(
        default=False,
        help_text="Whether the dump file is encrypted at rest (Fernet)",
    )

    class Meta:
        managed = True
        db_table = "backup_records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Backup {self.id} - {self.db_name} ({self.status})"


class RestoreRecord(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    db_name = models.CharField(max_length=200)
    source_backup = models.ForeignKey(
        BackupRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restores",
        help_text="The backup this restore was created from",
    )
    source_backup_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Snapshot of the source backup timestamp (kept even if backup is deleted)",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress"
    )
    duration_ms = models.BigIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        managed = True
        db_table = "restore_records"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Restore {self.id} - {self.db_name} ({self.status})"


class BackupSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("custom", "Custom (cron)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    db_name = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=True)
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="daily"
    )
    # time of day fields
    hour = models.IntegerField(default=2, help_text="Hour (0-23) in UTC")
    minute = models.IntegerField(default=0, help_text="Minute (0-59)")
    # weekly
    day_of_week = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of week for weekly schedule (0=Mon, 6=Sun)",
    )
    # monthly
    day_of_month = models.IntegerField(
        null=True, blank=True, help_text="Day of month for monthly schedule (1-28)"
    )
    # custom cron expression (overrides above when frequency=custom)
    cron_expression = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Full cron expression: minute hour day month weekday",
    )
    # retention
    retain_last_n = models.IntegerField(
        default=7, help_text="Keep only the last N successful backups (0 = keep all)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "backup_schedules"

    def __str__(self):
        return f"BackupSchedule({self.db_name}, {self.frequency}, {self.hour:02d}:{self.minute:02d})"


class HealthCheck(models.Model):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    db_name = models.CharField(max_length=200)
    checked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")
    response_time_ms = models.IntegerField(
        default=0, help_text="DB ping response time in ms"
    )
    error_message = models.TextField(blank=True, default="")

    class Meta:
        managed = True
        db_table = "health_checks"
        ordering = ["-checked_at"]

    def __str__(self):
        return f"HealthCheck {self.db_name} @ {self.checked_at} ({self.status})"
