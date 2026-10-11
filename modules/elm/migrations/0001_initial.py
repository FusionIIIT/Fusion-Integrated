# Initial schema for Employee Leave Management.
import django.db.models.deletion
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="LeavePolicy", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("category", models.CharField(max_length=12, unique=True)), ("annual_entitlement", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
            ("carry_forward_limit", models.DecimalField(decimal_places=2, default=0, max_digits=6)), ("applies_to", models.JSONField(blank=True, default=list)),
            ("requires_substitute", models.BooleanField(default=False)), ("counts_closed_days", models.BooleanField(default=False)), ("is_active", models.BooleanField(default=True)),
        ], options={"db_table": "elm_leave_policy", "ordering": ["category"]}),
        migrations.CreateModel(name="LeaveBalance", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(max_length=12)), ("leave_year", models.PositiveSmallIntegerField(db_index=True)),
            ("opening", models.DecimalField(decimal_places=2, default=0, max_digits=7)), ("credited", models.DecimalField(decimal_places=2, default=0, max_digits=7)),
            ("consumed", models.DecimalField(decimal_places=2, default=0, max_digits=7)), ("adjusted", models.DecimalField(decimal_places=2, default=0, max_digits=7)),
        ], options={"db_table": "elm_leave_balance", "indexes": [models.Index(fields=["user_id", "leave_year"], name="elm_balance_user_year_idx")], "constraints": [models.UniqueConstraint(fields=("user_id", "category", "leave_year"), name="elm_balance_user_cat_year_uniq")]}),
        migrations.CreateModel(name="LeaveRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("VL", "VL"), ("COL", "COL")], max_length=12)),
            ("start_date", models.DateField()), ("end_date", models.DateField()), ("duration_days", models.DecimalField(decimal_places=2, max_digits=6)), ("half_day", models.BooleanField(default=False)),
            ("half_day_period", models.CharField(blank=True, max_length=8)), ("station_leave_required", models.BooleanField(default=False)), ("station_leave_from", models.DateTimeField(blank=True, null=True)),
            ("station_leave_until", models.DateTimeField(blank=True, null=True)), ("substitute_user_id", models.IntegerField(blank=True, null=True)),
            ("substitute_consent", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined"), ("not_required", "Not required")], default="not_required", max_length=10)),
            ("reason", models.TextField(blank=True)), ("status", models.CharField(choices=[("draft", "Draft"), ("awaiting_substitute", "Awaiting Substitute"), ("pending_unit_head", "Pending Unit Head"), ("pending_authority", "Pending Authority"), ("pending_establishment", "Pending Establishment"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"), ("cancelled", "Cancelled")], db_index=True, default="pending_unit_head", max_length=32)),
            ("current_approver_user_id", models.IntegerField(blank=True, db_index=True, null=True)), ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)), ("decided_at", models.DateTimeField(blank=True, null=True)),
            ("related_request_id", models.IntegerField(blank=True, db_index=True, null=True)), ("source", models.CharField(choices=[("portal", "Portal"), ("offline", "Offline")], default="portal", max_length=16)), ("external_reference", models.CharField(blank=True, max_length=100)),
        ], options={"db_table": "elm_leave_request", "ordering": ["-created_at"], "indexes": [models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"), models.Index(fields=["start_date", "end_date"], name="elm_req_dates_idx")]}),
        migrations.CreateModel(name="LeaveCalendarDay", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("date", models.DateField(unique=True)), ("title", models.CharField(max_length=120)), ("day_type", models.CharField(choices=[("holiday", "Holiday"), ("restricted", "Restricted Holiday"), ("working", "Working Day")], max_length=12)), ("is_published", models.BooleanField(default=False)),
        ], options={"db_table": "elm_calendar_day", "ordering": ["date"]}),
        migrations.CreateModel(name="ApprovalTask", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("stage", models.CharField(max_length=24)), ("approver_user_id", models.IntegerField(db_index=True)), ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("superseded", "Superseded"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=12)),
            ("decision_note", models.TextField(blank=True)), ("acted_at", models.DateTimeField(blank=True, null=True)), ("due_at", models.DateTimeField(blank=True, null=True)),
            ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="elm.leaverequest")),
        ], options={"db_table": "elm_approval_task", "ordering": ["created_at"], "indexes": [models.Index(fields=["approver_user_id", "status"], name="elm_task_approver_status_idx")]}),
        migrations.CreateModel(name="ResumptionRecord", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("reported_on", models.DateField()), ("remarks", models.TextField(blank=True)), ("status", models.CharField(choices=[("pending", "Pending"), ("normal", "Normal"), ("early", "Early"), ("late", "Late")], default="pending", max_length=12)),
            ("verified_by_user_id", models.IntegerField(blank=True, null=True)), ("verified_at", models.DateTimeField(blank=True, null=True)), ("request", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="resumption", to="elm.leaverequest")),
        ], options={"db_table": "elm_resumption_record"}),
    ]
