# Initial schema for the Employee Leave Management baseline.
import django.db.models.deletion
from django.db import migrations, models


def seed_categories(apps, schema_editor):
    Category = apps.get_model("leave", "LeaveCategory")
    for code, label in (("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
                        ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
                        ("COL", "Commuted Leave"), ("VL", "Vacation Leave")):
        Category.objects.get_or_create(code=code, defaults={"label": label, "description": ""})
    Policy = apps.get_model("leave", "LeavePolicy")
    Policy.objects.get_or_create(policy_key="current")


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="EmployeeProfile",
            fields=[
                ("user_id", models.PositiveBigIntegerField(primary_key=True, serialize=False)),
                ("kind", models.CharField(choices=[("faculty", "Faculty"), ("staff", "Staff")], max_length=8)),
                ("designation", models.CharField(max_length=120)),
                ("unit_code", models.CharField(db_index=True, max_length=64)),
                ("unit_head_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("is_director", models.BooleanField(default=False)),
                ("active", models.BooleanField(default=True)),
                ("synced_at", models.DateTimeField()),
            ], options={"db_table": "leave_employee_profile"}),
        migrations.CreateModel(
            name="LeaveCategory",
            fields=[("code", models.CharField(max_length=3, primary_key=True, serialize=False)),
                    ("label", models.CharField(max_length=64)), ("description", models.TextField(blank=True))],
            options={"db_table": "leave_category", "ordering": ["code"]}),
        migrations.CreateModel(
            name="LeavePolicy",
            fields=[
                ("policy_key", models.CharField(default="current", editable=False, max_length=16, primary_key=True, serialize=False)),
                ("cl_days", models.DecimalField(decimal_places=2, default=8, max_digits=6)),
                ("rh_days", models.DecimalField(decimal_places=2, default=2, max_digits=6)),
                ("scl_days", models.DecimalField(decimal_places=2, default=15, max_digits=6)),
                ("faculty_vl_days", models.DecimalField(decimal_places=2, default=60, max_digits=6)),
                ("nonfaculty_el_days", models.DecimalField(decimal_places=2, default=30, max_digits=6)),
                ("col_days", models.DecimalField(decimal_places=2, default=20, max_digits=6)),
                ("col_medical_evidence_required", models.BooleanField(default=False)),
                ("year_end_month", models.PositiveSmallIntegerField(default=12)),
                ("year_end_day", models.PositiveSmallIntegerField(default=31)),
                ("updated_by_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ], options={"db_table": "leave_policy"}),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_id", models.PositiveBigIntegerField(db_index=True)), ("year", models.PositiveSmallIntegerField()),
                ("entitlement", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("carried_over", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("available", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="balances", to="leave.leavecategory")),
            ], options={"db_table": "leave_balance", "constraints": [models.UniqueConstraint(fields=("employee_id", "category", "year"), name="leave_balance_employee_category_year_uniq")], "indexes": [models.Index(fields=["employee_id", "year"], name="leave_balance_employee_year_idx")]}),
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField()), ("revision", models.PositiveSmallIntegerField(default=1)),
                ("holidays", models.JSONField(default=list)),
                ("state", models.CharField(choices=[("draft", "Draft"), ("published", "Published"), ("superseded", "Superseded")], default="draft", max_length=12)),
                ("published_by_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ], options={"db_table": "leave_holiday_calendar", "constraints": [models.UniqueConstraint(fields=("year", "revision"), name="leave_calendar_year_revision_uniq")], "indexes": [models.Index(fields=["year", "state"], name="leave_calendar_year_state_idx")]}),
        migrations.CreateModel(
            name="LeaveSLAConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(max_length=64, unique=True)), ("reminder_after_hours", models.PositiveIntegerField(default=24)),
                ("escalate_after_hours", models.PositiveIntegerField(default=72)), ("escalation_role", models.CharField(blank=True, max_length=64)),
                ("escalation_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("updated_by_user_id", models.PositiveBigIntegerField(blank=True, null=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ], options={"db_table": "leave_sla_configuration"}),
        migrations.CreateModel(
            name="VacationPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(max_length=120, unique=True)), ("label", models.CharField(max_length=120)),
                ("start_date", models.DateField()), ("end_date", models.DateField()), ("academic_year", models.CharField(db_index=True, max_length=16)),
                ("synced_at", models.DateTimeField()),
            ], options={"db_table": "leave_vacation_period", "constraints": [models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="leave_vacation_valid_date_range")]}),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_id", models.PositiveBigIntegerField(db_index=True)), ("request_type", models.CharField(choices=[("new", "New leave"), ("cancellation", "Cancellation"), ("extension", "Extension"), ("resumption", "Resumption"), ("offline", "Offline sanctioned entry")], default="new", max_length=16)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("awaiting_substitute", "Awaiting substitute"), ("applicant_action", "Applicant action required"), ("pending_unit_head", "Pending Unit Head"), ("pending_establishment", "Pending Establishment"), ("pending_authority", "Pending authority"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"), ("cancelled", "Cancelled"), ("completed", "Completed")], db_index=True, default="draft", max_length=32)),
                ("start_date", models.DateField()), ("end_date", models.DateField()), ("duration_days", models.DecimalField(decimal_places=2, max_digits=7)),
                ("cl_portion", models.CharField(choices=[("full", "Full day"), ("first_half", "First half"), ("second_half", "Second half")], default="full", max_length=16)),
                ("reason", models.TextField()), ("station_leave", models.BooleanField(default=False)),
                ("station_destination", models.CharField(blank=True, max_length=240)), ("station_departure_at", models.DateTimeField(blank=True, null=True)),
                ("station_return_at", models.DateTimeField(blank=True, null=True)), ("medical_evidence_ref", models.CharField(blank=True, max_length=500)),
                ("substitute_user_id", models.PositiveBigIntegerField(blank=True, null=True)), ("actual_resume_date", models.DateField(blank=True, null=True)),
                ("offline_sanction_ref", models.CharField(blank=True, max_length=240)), ("offline_evidence_ref", models.CharField(blank=True, max_length=500)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)), ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="leave.leavecategory")),
                ("parent_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="follow_ups", to="leave.leaverequest")),
            ], options={"db_table": "leave_request", "ordering": ["-created_at", "-id"], "indexes": [models.Index(fields=["employee_id", "status"], name="leave_request_employee_status_idx"), models.Index(fields=["start_date", "end_date", "status"], name="leave_request_period_status_idx")], "constraints": [models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="leave_request_valid_date_range")]}),
        migrations.CreateModel(
            name="LeaveAccountEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_id", models.PositiveBigIntegerField(db_index=True)), ("year", models.PositiveSmallIntegerField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8)),
                ("kind", models.CharField(choices=[("entitlement", "Entitlement"), ("carry_forward", "Carry forward"), ("leave_used", "Leave used"), ("cancellation_reversal", "Cancellation reversal"), ("vl_conversion", "VL to EL conversion"), ("resumption_adjustment", "Resumption adjustment"), ("offline_adjustment", "Offline adjustment"), ("year_end_lapse", "Year-end lapse")], max_length=32)),
                ("source_key", models.CharField(max_length=120, unique=True)), ("actor_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("explanation", models.CharField(blank=True, max_length=240)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entries", to="leave.leavecategory")),
                ("request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="account_entries", to="leave.leaverequest")),
            ], options={"db_table": "leave_account_entry", "ordering": ["created_at", "id"], "indexes": [models.Index(fields=["employee_id", "category", "year"], name="leave_entry_account_idx")]}),
        migrations.CreateModel(
            name="LeaveAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=48)), ("from_status", models.CharField(blank=True, max_length=32)),
                ("to_status", models.CharField(blank=True, max_length=32)), ("actor_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)), ("details", models.JSONField(blank=True, default=dict)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="leave.leaverequest")),
            ], options={"db_table": "leave_audit_event", "ordering": ["occurred_at", "id"]}),
        migrations.CreateModel(
            name="LeaveRouteConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_kind", models.CharField(choices=[("faculty", "Faculty"), ("staff", "Staff")], max_length=8)),
                ("designation", models.CharField(blank=True, max_length=120)), ("unit_code", models.CharField(blank=True, max_length=64)),
                ("final_authority_role", models.CharField(max_length=64)), ("final_authority_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("establishment_role", models.CharField(blank=True, max_length=64)), ("establishment_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("requires_substitute", models.BooleanField(default=False)), ("active", models.BooleanField(default=True)),
                ("updated_by_user_id", models.PositiveBigIntegerField(blank=True, null=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="routes", to="leave.leavecategory")),
            ], options={"db_table": "leave_route_configuration", "indexes": [models.Index(fields=["category", "employee_kind", "active"], name="leave_route_lookup_idx")]}),
        migrations.CreateModel(
            name="WorkflowTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveSmallIntegerField()), ("role", models.CharField(max_length=64)),
                ("decision_kind", models.CharField(choices=[("final", "Final decision"), ("recommendation", "Recommendation"), ("forward", "Forward")], max_length=20)),
                ("assigned_user_id", models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ("state", models.CharField(choices=[("queued", "Queued"), ("pending", "Pending"), ("completed", "Completed"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=12)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)), ("reminder_sent_at", models.DateTimeField(blank=True, null=True)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tasks", to="leave.leaverequest")),
            ], options={"db_table": "leave_workflow_task", "ordering": ["sequence", "id"], "constraints": [models.UniqueConstraint(fields=("request", "sequence"), name="leave_workflow_request_sequence_uniq")], "indexes": [models.Index(fields=["state", "due_at"], name="leave_task_state_due_idx")]}),
        migrations.CreateModel(
            name="LeaveSanction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_user_id", models.PositiveBigIntegerField()), ("decision", models.CharField(choices=[("recommended", "Recommended"), ("not_recommended", "Not recommended"), ("approved", "Approved"), ("rejected", "Rejected"), ("forwarded", "Forwarded")], max_length=20)),
                ("notes", models.TextField(blank=True)), ("decided_at", models.DateTimeField(auto_now_add=True)),
                ("task", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sanction", to="leave.workflowtask")),
            ], options={"db_table": "leave_sanction", "ordering": ["decided_at"]}),
        migrations.CreateModel(
            name="SubstituteResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("substitute_user_id", models.PositiveBigIntegerField()), ("decision", models.CharField(choices=[("accepted", "Accepted"), ("declined", "Declined")], max_length=12)),
                ("responded_at", models.DateTimeField(auto_now_add=True)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="substitute_responses", to="leave.leaverequest")),
            ], options={"db_table": "leave_substitute_response", "ordering": ["-responded_at"]}),
        migrations.CreateModel(
            name="LeaveNotificationOutbox",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dedupe_key", models.CharField(max_length=160, unique=True)), ("recipient_user_id", models.PositiveBigIntegerField(db_index=True)),
                ("subject", models.CharField(max_length=200)), ("body", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("state", models.CharField(choices=[("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"), ("failed", "Failed")], db_index=True, default="pending", max_length=12)),
                ("attempts", models.PositiveSmallIntegerField(default=0)), ("last_error", models.CharField(blank=True, max_length=300)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ], options={"db_table": "leave_notification_outbox", "indexes": [models.Index(fields=["state", "created_at"], name="leave_notify_state_created_idx")]}),
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
