# Initial ELM schema. Institute identities are integer IAM references, not FKs.
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="LeaveAccountLock", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.IntegerField(unique=True)),
        ], options={"db_table": "elm_leave_account_lock"}),
        migrations.CreateModel(name="LeavePolicy", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("key", models.CharField(default="current", max_length=32, unique=True)), ("params", models.JSONField(blank=True, default=dict)),
            ("hierarchy", models.JSONField(blank=True, default=dict)), ("updated_by_user_id", models.IntegerField(blank=True, null=True)),
        ], options={"db_table": "elm_leave_policy"}),
        migrations.CreateModel(name="CalendarVersion", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=120)), ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published")], default="draft", max_length=16)),
            ("effective_from", models.DateField()), ("published_at", models.DateTimeField(blank=True, null=True)), ("published_by_user_id", models.IntegerField(blank=True, null=True)),
        ], options={"db_table": "elm_calendar_version", "ordering": ["-effective_from", "-id"]}),
        migrations.CreateModel(name="LeaveRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)),
            ("kind", models.CharField(choices=[("leave", "Leave"), ("extension", "Extension")], default="leave", max_length=12)),
            ("start_date", models.DateField()), ("end_date", models.DateField()), ("half", models.CharField(blank=True, choices=[("first", "First half"), ("second", "Second half")], max_length=8)),
            ("days", models.DecimalField(decimal_places=2, max_digits=7)), ("purpose", models.TextField(blank=True)), ("station_leave", models.BooleanField(default=False)),
            ("station_leave_from", models.DateField(blank=True, null=True)), ("station_leave_to", models.DateField(blank=True, null=True)), ("station_leave_address", models.CharField(blank=True, max_length=300)),
            ("substitute_user_id", models.IntegerField(blank=True, null=True)), ("substitute_status", models.CharField(choices=[("not_required", "Not required"), ("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="not_required", max_length=16)),
            ("status", models.CharField(choices=[("awaiting_substitute", "Awaiting Substitute"), ("substitute_declined", "Substitute Declined"), ("awaiting_unit_head", "Awaiting Unit Head"), ("awaiting_establishment", "Awaiting Establishment"), ("awaiting_sanction", "Awaiting Sanction"), ("awaiting_director", "Awaiting Director"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"), ("cancellation_pending", "Cancellation Pending"), ("cancelled", "Cancelled"), ("resumption_pending", "Resumption Pending"), ("resumption_reviewed_no_adjustment", "Resumption Reviewed No Adjustment"), ("resumption_reviewed_early", "Resumption Reviewed Early"), ("resumption_reviewed_late", "Resumption Reviewed Late")], db_index=True, default="awaiting_unit_head", max_length=40)),
            ("route", models.JSONField(blank=True, default=list)), ("stage", models.PositiveSmallIntegerField(default=0)), ("current_role", models.CharField(blank=True, max_length=80)),
            ("recommendation", models.CharField(blank=True, choices=[("recommended", "Recommended"), ("not_recommended", "Not recommended")], max_length=16)), ("decision_note", models.TextField(blank=True)),
            ("submitted_at", models.DateTimeField(blank=True, null=True)), ("decided_at", models.DateTimeField(blank=True, null=True)), ("cancellation_stage", models.PositiveSmallIntegerField(default=0)),
            ("cancellation_reason", models.TextField(blank=True)), ("cancellation_requested_at", models.DateTimeField(blank=True, null=True)), ("actual_return_date", models.DateField(blank=True, null=True)),
            ("resumption_kind", models.CharField(blank=True, choices=[("normal", "Normal"), ("early", "Early"), ("late", "Late")], max_length=12)), ("resumption_note", models.TextField(blank=True)),
            ("evidence", models.JSONField(blank=True, default=list)), ("policy_snapshot", models.JSONField(blank=True, default=dict)),
            ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="extensions", to="elm.leaverequest")),
        ], options={"db_table": "elm_leave_request"}),
        migrations.CreateModel(name="CalendarEntry", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("kind", models.CharField(choices=[("closed_holiday", "Closed holiday"), ("restricted_holiday", "Restricted holiday"), ("vacation", "Vacation")], max_length=24)), ("start_date", models.DateField()), ("end_date", models.DateField()), ("label", models.CharField(blank=True, max_length=160)),
            ("calendar", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="elm.calendarversion")),
        ], options={"db_table": "elm_calendar_entry"}),
        migrations.CreateModel(name="LeaveTransition", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("from_status", models.CharField(blank=True, max_length=40)), ("to_status", models.CharField(max_length=40)), ("event", models.CharField(max_length=48)), ("actor_user_id", models.IntegerField(blank=True, null=True)), ("actor_role", models.CharField(blank=True, max_length=80)), ("note", models.TextField(blank=True)), ("data", models.JSONField(blank=True, default=dict)),
            ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transitions", to="elm.leaverequest")),
        ], options={"db_table": "elm_leave_transition", "ordering": ["created_at", "id"]}),
        migrations.CreateModel(name="LedgerEntry", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)), ("delta", models.DecimalField(decimal_places=2, max_digits=9)),
            ("entry_type", models.CharField(choices=[("annual_credit", "annual_credit"), ("debit", "debit"), ("reversal", "reversal"), ("restore", "restore"), ("year_end_lapse", "year_end_lapse"), ("vl_conversion", "vl_conversion"), ("adjustment", "adjustment")], max_length=24)), ("year", models.PositiveSmallIntegerField(db_index=True)), ("reference", models.CharField(blank=True, max_length=120)), ("note", models.CharField(blank=True, max_length=300)),
            ("request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="elm.leaverequest")),
        ], options={"db_table": "elm_ledger_entry"}),
        migrations.CreateModel(name="OfflineLeaveRecord", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.IntegerField(db_index=True)), ("category", models.CharField(choices=[("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"), ("COL", "COL"), ("VL", "VL")], max_length=3)), ("start_date", models.DateField()), ("end_date", models.DateField()), ("days", models.DecimalField(decimal_places=2, max_digits=7)), ("sanction_reference", models.CharField(blank=True, max_length=120)), ("evidence", models.JSONField(blank=True, default=list)), ("recorded_by_user_id", models.IntegerField()), ("note", models.TextField(blank=True)),
            ("synced_request", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="offline_record", to="elm.leaverequest")),
        ], options={"db_table": "elm_offline_leave_record"}),
        migrations.CreateModel(name="YearEndRun", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("year", models.PositiveSmallIntegerField(unique=True)), ("status", models.CharField(choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="running", max_length=16)), ("report", models.JSONField(blank=True, default=dict)), ("started_at", models.DateTimeField(auto_now_add=True)), ("finished_at", models.DateTimeField(blank=True, null=True)),
        ], options={"db_table": "elm_year_end_run"}),
        migrations.CreateModel(name="Notification", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("recipient_user_id", models.IntegerField(blank=True, db_index=True, null=True)), ("recipient_role", models.CharField(blank=True, db_index=True, max_length=80)), ("topic", models.CharField(db_index=True, max_length=48)), ("title", models.CharField(max_length=200)), ("body", models.TextField()), ("payload", models.JSONField(blank=True, default=dict)), ("read_at", models.DateTimeField(blank=True, null=True)),
        ], options={"db_table": "elm_notification"}),
        migrations.CreateModel(name="SlaAction", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("stage", models.PositiveIntegerField()), ("action", models.CharField(choices=[("reminder", "Reminder"), ("escalation", "Escalation")], max_length=16)), ("fired_at", models.DateTimeField(auto_now_add=True)), ("target_role", models.CharField(blank=True, max_length=80)),
            ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sla_actions", to="elm.leaverequest")),
        ], options={"db_table": "elm_sla_action"}),
        migrations.AddConstraint(model_name="calendarentry", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="elm_calendar_entry_dates_valid")),
        migrations.AddConstraint(model_name="leaverequest", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="elm_request_dates_valid")),
        migrations.AddConstraint(model_name="leaverequest", constraint=models.CheckConstraint(condition=models.Q(("days__gt", 0)), name="elm_request_days_positive")),
        migrations.AddConstraint(model_name="ledgerentry", constraint=models.UniqueConstraint(condition=models.Q(("entry_type", "annual_credit")), fields=("user_id", "category", "year"), name="elm_ledger_credit_once")),
        migrations.AddConstraint(model_name="ledgerentry", constraint=models.UniqueConstraint(condition=models.Q(("entry_type__in", ["debit", "reversal", "restore"])), fields=("request", "entry_type"), name="elm_ledger_req_event_once")),
        migrations.AddConstraint(model_name="ledgerentry", constraint=models.UniqueConstraint(condition=models.Q(("reference__gt", "")), fields=("user_id", "category", "year", "entry_type", "reference"), name="elm_ledger_ref_once")),
        migrations.AddConstraint(model_name="offlineleaverecord", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="elm_offline_dates_valid")),
        migrations.AddConstraint(model_name="slaaction", constraint=models.UniqueConstraint(fields=("request", "stage", "action"), name="elm_sla_action_once_unique")),
        migrations.AddIndex(model_name="calendarversion", index=models.Index(fields=["status", "effective_from"], name="elm_calendar_effective_idx")),
        migrations.AddIndex(model_name="calendarentry", index=models.Index(fields=["calendar", "kind", "start_date"], name="elm_calendar_entry_lookup_idx")),
        migrations.AddIndex(model_name="leaverequest", index=models.Index(fields=["user_id", "status"], name="elm_request_user_status_idx")),
        migrations.AddIndex(model_name="leaverequest", index=models.Index(fields=["status", "current_role"], name="elm_request_queue_idx")),
        migrations.AddIndex(model_name="leaverequest", index=models.Index(fields=["start_date", "end_date"], name="elm_request_dates_idx")),
        migrations.AddIndex(model_name="leavetransition", index=models.Index(fields=["request", "created_at"], name="elm_transition_req_time_idx")),
        migrations.AddIndex(model_name="ledgerentry", index=models.Index(fields=["user_id", "category", "year"], name="elm_ledger_balance_idx")),
        migrations.AddIndex(model_name="notification", index=models.Index(fields=["recipient_user_id", "created_at"], name="elm_notification_user_idx")),
    ]
