import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="LeavePolicy", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=120)), ("version", models.PositiveIntegerField()),
            ("effective_from", models.DateField()), ("effective_to", models.DateField(blank=True, null=True)),
            ("published_at", models.DateTimeField(blank=True, null=True)), ("published_by_user_id", models.IntegerField(blank=True, null=True)),
            ("parameters", models.JSONField(default=dict)), ("hierarchy", models.JSONField(default=dict)),
        ], options={"db_table": "elm_leave_policy", "constraints": [models.UniqueConstraint(fields=("name", "version"), name="elm_policy_name_version_uniq")], "indexes": [models.Index(fields=["effective_from", "effective_to"], name="elm_policy_effective_idx")]}),
        migrations.CreateModel(name="CalendarVersion", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=120)), ("version", models.PositiveIntegerField()),
            ("effective_from", models.DateField()), ("effective_to", models.DateField(blank=True, null=True)),
            ("published_at", models.DateTimeField(blank=True, null=True)), ("published_by_user_id", models.IntegerField(blank=True, null=True)),
            ("holidays", models.JSONField(default=list)), ("restricted_holidays", models.JSONField(default=list)),
            ("vacation_periods", models.JSONField(default=list)),
        ], options={"db_table": "elm_calendar_version", "constraints": [models.UniqueConstraint(fields=("name", "version"), name="elm_calendar_name_version_uniq")], "indexes": [models.Index(fields=["effective_from", "effective_to"], name="elm_calendar_effective_idx")]}),
        migrations.CreateModel(name="LeaveRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user_id", models.IntegerField(db_index=True)),
            ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)),
            ("kind", models.CharField(choices=[("leave", "leave"), ("cancellation", "cancellation"), ("extension", "extension"), ("resumption", "resumption"), ("offline", "offline")], default="leave", max_length=16)),
            ("status", models.CharField(choices=[(x, x) for x in ["draft", "awaiting_substitute", "unit_head_review", "establishment_review", "authority_review", "approved", "rejected", "withdrawn", "cancellation_pending", "cancelled", "extension_pending", "resumption_pending", "closed"]], db_index=True, default="draft", max_length=32)),
            ("start_date", models.DateField()), ("end_date", models.DateField()), ("half_day", models.CharField(choices=[("none", "None"), ("first", "First half"), ("second", "Second half")], default="none", max_length=8)),
            ("chargeable_days", models.DecimalField(decimal_places=2, default=0, max_digits=7)), ("purpose", models.TextField()), ("station_leave", models.BooleanField(default=False)), ("station_leave_details", models.JSONField(blank=True, default=dict)),
            ("substitute_user_id", models.IntegerField(blank=True, null=True)), ("substitute_response", models.CharField(blank=True, choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], max_length=12)),
            ("medical_evidence_ref", models.CharField(blank=True, max_length=500)), ("policy_version_id", models.IntegerField(blank=True, null=True)), ("calendar_version_id", models.IntegerField(blank=True, null=True)),
            ("unit_head_user_id", models.IntegerField(blank=True, null=True)), ("current_approver_user_id", models.IntegerField(blank=True, null=True)), ("decision_reason", models.TextField(blank=True)),
            ("submitted_at", models.DateTimeField(blank=True, null=True)), ("decided_at", models.DateTimeField(blank=True, null=True)), ("actual_resumption_date", models.DateField(blank=True, null=True)), ("extra", models.JSONField(blank=True, default=dict)),
            ("parent_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="related_requests", to="elm.leaverequest")),
        ], options={"db_table": "elm_leave_request", "indexes": [models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"), models.Index(fields=["start_date", "end_date"], name="elm_req_dates_idx")], "constraints": [models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="elm_req_date_order")]}),
        migrations.CreateModel(name="YearEndRun", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("year", models.PositiveSmallIntegerField()), ("started_at", models.DateTimeField(auto_now_add=True)), ("completed_at", models.DateTimeField(blank=True, null=True)), ("status", models.CharField(choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="running", max_length=16)), ("summary", models.JSONField(blank=True, default=dict)), ("error", models.TextField(blank=True)),
        ], options={"db_table": "elm_year_end_run", "constraints": [models.UniqueConstraint(fields=("year",), name="elm_year_end_year_uniq")]}),
        migrations.CreateModel(name="WorkflowTask", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("task_type", models.CharField(max_length=32)), ("assigned_user_id", models.IntegerField(blank=True, null=True)), ("assigned_role", models.CharField(blank=True, max_length=100)), ("status", models.CharField(choices=[("open", "Open"), ("completed", "Completed"), ("cancelled", "Cancelled"), ("superseded", "Superseded")], default="open", max_length=16)), ("due_at", models.DateTimeField(blank=True, null=True)), ("completed_at", models.DateTimeField(blank=True, null=True)), ("escalated_at", models.DateTimeField(blank=True, null=True)), ("payload", models.JSONField(blank=True, default=dict)), ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="elm.leaverequest")),
        ], options={"db_table": "elm_workflow_task", "indexes": [models.Index(fields=["status", "due_at"], name="elm_task_due_idx"), models.Index(fields=["request", "status"], name="elm_task_req_status_idx")]}),
        migrations.CreateModel(name="LeaveLedgerEntry", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)), ("amount", models.DecimalField(decimal_places=2, max_digits=8)), ("entry_type", models.CharField(choices=[("credit", "Credit"), ("debit", "Debit"), ("restore", "Restore"), ("lapse", "Lapse"), ("conversion", "Conversion"), ("adjustment", "Adjustment")], max_length=24)), ("effective_date", models.DateField()), ("idempotency_key", models.CharField(max_length=180, unique=True)), ("actor_user_id", models.IntegerField(blank=True, null=True)), ("note", models.CharField(blank=True, max_length=300)), ("request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="elm.leaverequest")),
        ], options={"db_table": "elm_leave_ledger", "indexes": [models.Index(fields=["user_id", "category", "effective_date"], name="elm_ledger_user_cat_date_idx")] }),
        migrations.CreateModel(name="AuditEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("actor_user_id", models.IntegerField(blank=True, null=True)), ("event_type", models.CharField(max_length=80)), ("from_status", models.CharField(blank=True, max_length=32)), ("to_status", models.CharField(blank=True, max_length=32)), ("reason", models.TextField(blank=True)), ("payload", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)), ("request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="elm.leaverequest")),
        ], options={"db_table": "elm_audit_event", "indexes": [models.Index(fields=["request", "created_at"], name="elm_audit_req_created_idx")] }),
    ]
