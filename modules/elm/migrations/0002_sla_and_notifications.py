"""SLA configuration, workflow tasks, notifications and the SLA event log.

Closes the gap for BR-EL-032, BR-EL-033, BR-EL-035 and BR-EL-038
(CFR-EL-029..032, EL-UC-018, EL-UC-021), none of which had any schema in the
Phase-1 generated module.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SLAConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("task_kind", models.CharField(max_length=48, unique=True)),
                ("reminder_hours", models.DecimalField(decimal_places=2, max_digits=7)),
                ("escalation_hours", models.DecimalField(decimal_places=2, max_digits=7)),
                ("escalation_role", models.CharField(blank=True, max_length=64)),
                ("escalation_recipient_id", models.IntegerField(blank=True, null=True)),
                ("escalation_changes_routing", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_by_id", models.IntegerField(blank=True, null=True)),
            ],
            options={
                "db_table": "elm_sla_configuration",
                "ordering": ["task_kind"],
            },
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recipient_id", models.IntegerField(db_index=True)),
                ("kind", models.CharField(max_length=32)),
                ("subject", models.CharField(max_length=256)),
                ("body", models.TextField()),
                ("link", models.CharField(blank=True, max_length=256)),
                ("task_kind", models.CharField(blank=True, max_length=48)),
                ("task_id", models.IntegerField(blank=True, null=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "elm_notification",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SLAEventLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("task_id", models.IntegerField(db_index=True)),
                ("task_kind", models.CharField(max_length=48)),
                ("action", models.CharField(max_length=16)),
                ("reason", models.CharField(max_length=48)),
                ("recipient_id", models.IntegerField(blank=True, null=True)),
                ("escalation_role", models.CharField(blank=True, max_length=64)),
                ("changes_routing", models.BooleanField(default=False)),
                ("hours_elapsed", models.DecimalField(decimal_places=2, default=0, max_digits=9)),
                ("evaluated_at", models.DateTimeField()),
            ],
            options={
                "db_table": "elm_sla_event_log",
                "ordering": ["-evaluated_at"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("subject_type", models.CharField(default="APPLICATION", max_length=32)),
                ("subject_id", models.IntegerField(blank=True, null=True)),
                ("task_kind", models.CharField(max_length=48)),
                ("assignee_id", models.IntegerField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("OPEN", "Open"), ("CLOSED", "Closed")],
                        default="OPEN",
                        max_length=16,
                    ),
                ),
                ("opened_at", models.DateTimeField()),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("closed_by_id", models.IntegerField(blank=True, null=True)),
                ("closed_reason", models.CharField(blank=True, max_length=64)),
                ("reminded_at", models.DateTimeField(blank=True, null=True)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("escalated_to_id", models.IntegerField(blank=True, null=True)),
                (
                    "application",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workflow_tasks",
                        to="elm.leaveapplication",
                    ),
                ),
            ],
            options={
                "db_table": "elm_workflow_task",
                "ordering": ["opened_at"],
            },
        ),
        migrations.AddIndex(
            model_name="workflowtask",
            index=models.Index(fields=["status", "task_kind"], name="elm_task_status_kind_idx"),
        ),
    ]
