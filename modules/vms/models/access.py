"""VMS Gate Access Logs and Security Alerts."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.vms.models.visits import Visit


class GateLog(TimeStampedModel):
    ACTIONS = [
        ("check_in", "Check in"),
        ("check_out", "Check out"),
        ("zone_transit", "Zone transit"),
    ]

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="gate_logs")
    action = models.CharField(max_length=32, choices=ACTIONS)
    gate_name = models.CharField(max_length=64, default="Main Gate")
    reader_machine_id = models.CharField(max_length=64, blank=True)
    logged_by = models.IntegerField(null=True, blank=True)
    is_offline_sync = models.BooleanField(default=False)

    class Meta:
        db_table = "vms_gate_log"
        indexes = [
            models.Index(fields=["visit", "created_at"], name="vms_gl_vis_created_idx"),
        ]

    def __str__(self) -> str:
        return f"GateLog {self.action} for {self.visit.pass_number} at {self.gate_name}"


class GateAlert(TimeStampedModel):
    SEVERITY_CHOICES = [
        ("info", "Information"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    alert_type = models.CharField(max_length=64)
    severity = models.CharField(max_length=32, choices=SEVERITY_CHOICES, default="warning")
    message = models.CharField(max_length=255)
    visit_id = models.IntegerField(null=True, blank=True)
    visitor_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, default="open")
    resolved_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_gate_alert"
        indexes = [
            models.Index(fields=["status", "severity"], name="vms_ga_stat_sev_idx"),
        ]

    def __str__(self) -> str:
        return f"GateAlert [{self.severity.upper()}]: {self.message}"
