# Generated for the initial PHC module schema.
from django.db import migrations, models
import django.core.validators
import django.utils.timezone
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="DoctorSchedule",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("doctor_name", models.CharField(max_length=160)), ("specialisation", models.CharField(blank=True, max_length=120)), ("day_of_week", models.CharField(choices=[("MON", "Monday"), ("TUE", "Tuesday"), ("WED", "Wednesday"), ("THU", "Thursday"), ("FRI", "Friday"), ("SAT", "Saturday"), ("SUN", "Sunday")], max_length=3)), ("start_time", models.TimeField()), ("end_time", models.TimeField()), ("room", models.CharField(blank=True, max_length=80)), ("is_published", models.BooleanField(default=False)), ("created_by_user_id", models.IntegerField())],
            options={"db_table": "phc_doctor_schedule", "ordering": ["day_of_week", "start_time"], "indexes": [models.Index(fields=["is_published", "day_of_week"], name="phc_schedule_published_idx")]},
        ),
        migrations.CreateModel(
            name="ReimbursementConfig",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("submission_window_days", models.PositiveIntegerField(default=90, help_text="Days from expense date within which a claim must be submitted (0 = unlimited).")), ("updated_at", models.DateTimeField(auto_now=True))],
            options={"db_table": "phc_reimbursement_config"},
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("name", models.CharField(max_length=160, unique=True)), ("unit", models.CharField(blank=True, help_text="e.g. tablets, ml, boxes", max_length=40)), ("stock_quantity", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("reorder_threshold", models.DecimalField(decimal_places=2, default=0, help_text="Low-stock alert fires when stock < this (PHC-BR-07).", max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("description", models.TextField(blank=True))],
            options={"db_table": "phc_inventory_item", "indexes": [models.Index(fields=["name"], name="phc_inventory_name_idx")]},
        ),
        migrations.CreateModel(
            name="AmbulanceLog",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("patient_name", models.CharField(max_length=160)), ("destination", models.CharField(max_length=255)), ("usage_at", models.DateTimeField()), ("notes", models.TextField(blank=True)), ("recorded_by_user_id", models.IntegerField())],
            options={"db_table": "phc_ambulance_log", "ordering": ["-usage_at"]},
        ),
        migrations.CreateModel(
            name="HealthAnnouncement",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("title", models.CharField(max_length=255)), ("body", models.TextField()), ("is_published", models.BooleanField(default=True)), ("published_by_user_id", models.IntegerField()), ("published_at", models.DateTimeField(auto_now_add=True))],
            options={"db_table": "phc_health_announcement", "ordering": ["-published_at"], "indexes": [models.Index(fields=["is_published", "published_at"], name="phc_announcement_published_idx")]},
        ),
        migrations.CreateModel(
            name="PhcNotification",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("recipient_user_id", models.IntegerField(db_index=True)), ("event_type", models.CharField(choices=[("claim_status_changed", "Claim status changed"), ("requisition_decided", "Requisition decided"), ("low_stock_alert", "Low-stock alert")], max_length=40)), ("subject", models.CharField(max_length=255)), ("body", models.TextField()), ("delivered", models.BooleanField(default=False)), ("delivered_at", models.DateTimeField(blank=True, null=True)), ("attempts", models.PositiveSmallIntegerField(default=0)), ("reference_id", models.IntegerField(blank=True, help_text="PK of the related object.", null=True)), ("reference_type", models.CharField(blank=True, max_length=40))],
            options={"db_table": "phc_notification", "indexes": [models.Index(fields=["delivered", "created_at"], name="phc_notif_pending_idx"), models.Index(fields=["recipient_user_id", "delivered"], name="phc_notif_recipient_idx")]},
        ),
        migrations.CreateModel(
            name="PatientRecordAudit",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("record_type", models.CharField(choices=[("visit", "Patient Visit"), ("prescription", "Prescription")], max_length=20)), ("record_id", models.BigIntegerField()), ("patient_user_id", models.IntegerField()), ("action", models.CharField(choices=[("create", "Create"), ("modify", "Modify"), ("delete", "Delete")], max_length=10)), ("actor_user_id", models.IntegerField(blank=True, null=True)), ("details", models.JSONField(blank=True, default=dict)), ("at", models.DateTimeField(auto_now_add=True))],
            options={"db_table": "phc_patient_record_audit", "indexes": [models.Index(fields=["patient_user_id", "at"], name="phc_patient_audit_idx"), models.Index(fields=["record_type", "record_id"], name="phc_patient_audit_record_idx")]},
        ),
        migrations.CreateModel(
            name="PatientVisit",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user_id", models.IntegerField(db_index=True)), ("visit_date", models.DateField()), ("chief_complaint", models.TextField()), ("diagnosis", models.TextField(blank=True)), ("notes", models.TextField(blank=True)), ("recorded_by_user_id", models.IntegerField())],
            options={"db_table": "phc_patient_visit", "indexes": [models.Index(fields=["user_id", "visit_date"], name="phc_visit_patient_date_idx")]},
        ),
        migrations.CreateModel(
            name="DoctorAttendance",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("date", models.DateField(default=django.utils.timezone.localdate)), ("status", models.CharField(choices=[("available", "Available"), ("departed", "Departed")], default="available", max_length=12)), ("marked_by_user_id", models.IntegerField()), ("schedule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="phc.doctorschedule"))],
            options={"db_table": "phc_doctor_attendance", "indexes": [models.Index(fields=["date"], name="phc_attendance_date_idx")], "constraints": [models.UniqueConstraint(fields=("schedule", "date"), name="phc_attendance_schedule_date_uniq")]},
        ),
        migrations.CreateModel(
            name="Prescription",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user_id", models.IntegerField(db_index=True)), ("medicine_name", models.CharField(max_length=160)), ("dosage", models.CharField(max_length=120)), ("duration_days", models.PositiveSmallIntegerField(blank=True, null=True)), ("instructions", models.TextField(blank=True)), ("prescribed_by_user_id", models.IntegerField()), ("expense_date", models.DateField(blank=True, help_text="Date of medical expense - used for reimbursement window (PHC-BR-06).", null=True)), ("visit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="prescriptions", to="phc.patientvisit"))],
            options={"db_table": "phc_prescription", "indexes": [models.Index(fields=["user_id", "visit"], name="phc_prescription_patient_idx")]},
        ),
        migrations.CreateModel(
            name="ReimbursementClaim",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("user_id", models.IntegerField(db_index=True)), ("amount_claimed", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator("0.01")])), ("description", models.TextField(blank=True)), ("status", models.CharField(choices=[("pending_phc_review", "Pending PHC Review"), ("pending_accounts_verification", "Pending Accounts Verification"), ("pending_sanction", "Pending Sanction"), ("approved_for_payment", "Approved for Payment"), ("reimbursed", "Reimbursed"), ("rejected", "Rejected")], default="pending_phc_review", max_length=36)), ("submitted_at", models.DateTimeField(auto_now_add=True)), ("prescription", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reimbursement_claims", to="phc.prescription"))],
            options={"db_table": "phc_reimbursement_claim", "indexes": [models.Index(fields=["user_id", "status"], name="phc_claim_patient_status_idx"), models.Index(fields=["status"], name="phc_claim_status_idx")]},
        ),
        migrations.CreateModel(
            name="ReimbursementAudit",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("from_status", models.CharField(max_length=36)), ("to_status", models.CharField(max_length=36)), ("actor_user_id", models.IntegerField(blank=True, null=True)), ("actor_role", models.CharField(blank=True, max_length=40)), ("notes", models.TextField(blank=True)), ("at", models.DateTimeField(auto_now_add=True)), ("claim", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_entries", to="phc.reimbursementclaim"))],
            options={"db_table": "phc_reimbursement_audit", "indexes": [models.Index(fields=["claim", "at"], name="phc_reimb_audit_idx")]},
        ),
        migrations.CreateModel(
            name="InventoryAudit",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("delta", models.DecimalField(decimal_places=2, help_text="Positive = add, negative = deduct.", max_digits=12)), ("quantity_before", models.DecimalField(decimal_places=2, max_digits=12)), ("quantity_after", models.DecimalField(decimal_places=2, max_digits=12)), ("actor_user_id", models.IntegerField()), ("notes", models.TextField(blank=True)), ("at", models.DateTimeField(auto_now_add=True)), ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_entries", to="phc.inventoryitem"))],
            options={"db_table": "phc_inventory_audit", "indexes": [models.Index(fields=["item", "at"], name="phc_inv_audit_idx")]},
        ),
        migrations.CreateModel(
            name="ProcurementRequisition",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("title", models.CharField(max_length=200)), ("justification", models.TextField(blank=True)), ("status", models.CharField(choices=[("pending_approval", "Pending Approval"), ("approved", "Approved"), ("rejected", "Rejected"), ("fulfilled", "Fulfilled")], default="pending_approval", max_length=20)), ("submitted_by_user_id", models.IntegerField()), ("decided_by_user_id", models.IntegerField(blank=True, null=True)), ("decision_notes", models.TextField(blank=True)), ("decided_at", models.DateTimeField(blank=True, null=True)), ("fulfilled_at", models.DateTimeField(blank=True, null=True))],
            options={"db_table": "phc_procurement_requisition", "indexes": [models.Index(fields=["status"], name="phc_req_status_idx"), models.Index(fields=["submitted_by_user_id"], name="phc_req_submitter_idx")]},
        ),
        migrations.CreateModel(
            name="RequisitionLineItem",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")), ("item_name", models.CharField(max_length=160)), ("quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator("0.01")])), ("unit", models.CharField(blank=True, max_length=40)), ("notes", models.TextField(blank=True)), ("requisition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="line_items", to="phc.procurementrequisition"))],
            options={"db_table": "phc_requisition_line_item"},
        ),
    ]
