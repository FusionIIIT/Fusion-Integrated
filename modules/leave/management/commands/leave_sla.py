from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.services.sla import (
    DEFAULT_STAGE_SLA_CONFIGS,
    StageSlaConfig,
    process_sla_events,
)


class Command(BaseCommand):
    help = "Evaluate SLA thresholds for pending leave requests and issue reminders or escalations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--request-id",
            type=int,
            dest="request_id",
            default=None,
            help="Optional single leave request ID to evaluate.",
        )
        parser.add_argument(
            "--reminder-hours",
            type=float,
            dest="reminder_hours",
            default=None,
            help="Override reminder threshold hours across all evaluated stages.",
        )
        parser.add_argument(
            "--escalation-hours",
            type=float,
            dest="escalation_hours",
            default=None,
            help="Override escalation threshold hours across all evaluated stages.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Evaluate and report events without recording transitions or routing changes.",
        )

    def handle(self, *args, **options):
        request_id = options.get("request_id")
        rem_h = options.get("reminder_hours")
        esc_h = options.get("escalation_hours")
        dry_run = options.get("dry_run", False)

        stage_configs = None
        if rem_h is not None or esc_h is not None:
            stage_configs = {}
            for stage, cfg in DEFAULT_STAGE_SLA_CONFIGS.items():
                rem = rem_h if rem_h is not None else cfg.reminder_threshold_hours
                esc = esc_h if esc_h is not None else cfg.escalation_threshold_hours
                stage_configs[stage] = StageSlaConfig(
                    reminder_threshold_hours=rem,
                    escalation_threshold_hours=esc,
                    responsible_role=cfg.responsible_role,
                    escalation_role=cfg.escalation_role,
                    auto_escalate_routing=cfg.auto_escalate_routing,
                )

        request_ids = [request_id] if request_id else None

        self.stdout.write("Starting SLA threshold evaluation...")
        report = process_sla_events(
            now=timezone.now(),
            stage_configs=stage_configs,
            request_ids=request_ids,
            dry_run=dry_run,
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No database changes were committed."))

        self.stdout.write(f"  Inspected requests: {report.inspected_requests}")
        self.stdout.write(f"  Reminders issued:   {report.reminders_sent}")
        self.stdout.write(f"  Escalations issued: {report.escalations_sent}")
        self.stdout.write(f"  Skipped requests:   {report.skipped_requests}")

        if report.notification_failures > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"  Notification delivery failures: {report.notification_failures}"
                )
            )

        if report.exceptions:
            self.stdout.write(self.style.ERROR(f"  Errors encountered: {len(report.exceptions)}"))
            for exc in report.exceptions:
                self.stdout.write(self.style.ERROR(f"    - {exc}"))

        self.stdout.write(self.style.SUCCESS("SLA processing finished successfully."))
