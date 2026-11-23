import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AuditRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_user_id', models.IntegerField()),
                ('resource_type', models.CharField(max_length=40)),
                ('resource_id', models.BigIntegerField()),
                ('action', models.CharField(max_length=40)),
                ('details', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'phc_audit_record',
            },
        ),
        migrations.CreateModel(
            name='AmbulanceLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('used_at', models.DateTimeField()),
                ('patient_name', models.CharField(max_length=160)),
                ('destination', models.CharField(max_length=300)),
                ('recorded_by_user_id', models.IntegerField()),
            ],
            options={
                'db_table': 'phc_ambulance_log',
                'indexes': [models.Index(fields=['-used_at'], name='phc_ambulance_recent_idx')],
            },
        ),
        migrations.CreateModel(
            name='DoctorSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor_name', models.CharField(max_length=160)),
                ('specialization', models.CharField(blank=True, max_length=120)),
                ('is_published', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('created_by_user_id', models.IntegerField()),
            ],
            options={
                'db_table': 'phc_doctor_schedule',
                'indexes': [models.Index(fields=['is_published', 'doctor_name'], name='phc_schedule_published_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('is_published', False), ('published_at__isnull', False), _connector='OR'), name='phc_schedule_published_has_time')],
            },
        ),
        migrations.CreateModel(
            name='HealthAdvisory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=180)),
                ('body', models.TextField()),
                ('published_at', models.DateTimeField()),
                ('published_by_user_id', models.IntegerField()),
            ],
            options={
                'db_table': 'phc_health_advisory',
                'indexes': [models.Index(fields=['-published_at'], name='phc_advisory_recent_idx')],
            },
        ),
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=160, unique=True)),
                ('unit', models.CharField(max_length=40)),
                ('stock_level', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('reorder_threshold', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ],
            options={
                'db_table': 'phc_inventory_item',
                'ordering': ('name',),
                'constraints': [models.CheckConstraint(condition=models.Q(('stock_level__gte', 0)), name='phc_stock_nonnegative'), models.CheckConstraint(condition=models.Q(('reorder_threshold__gte', 0)), name='phc_threshold_nonnegative')],
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_user_id', models.IntegerField()),
                ('kind', models.CharField(max_length=40)),
                ('message', models.CharField(max_length=300)),
                ('resource_type', models.CharField(max_length=40)),
                ('resource_id', models.BigIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'phc_notification',
                'indexes': [models.Index(fields=['recipient_user_id', '-created_at'], name='phc_notification_inbox_idx')],
            },
        ),
        migrations.CreateModel(
            name='PatientVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient_user_id', models.IntegerField()),
                ('visit_date', models.DateField()),
                ('complaint', models.TextField()),
                ('diagnosis', models.TextField(blank=True)),
                ('recorded_by_user_id', models.IntegerField()),
            ],
            options={
                'db_table': 'phc_patient_visit',
                'indexes': [models.Index(fields=['patient_user_id', '-visit_date'], name='phc_visit_patient_idx'), models.Index(fields=['visit_date'], name='phc_visit_date_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('patient_user_id', models.F('recorded_by_user_id')), _negated=True), name='phc_visit_not_self_recorded')],
            },
        ),
        migrations.CreateModel(
            name='Prescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('medicine', models.CharField(max_length=160)),
                ('dosage', models.CharField(max_length=120)),
                ('duration_days', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('instructions', models.TextField(blank=True)),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='prescriptions', to='phc.patientvisit')),
            ],
            options={
                'db_table': 'phc_prescription',
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='ReimbursementClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('expense_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('status', models.CharField(choices=[('pending_phc_review', 'Pending PHC review'), ('pending_accounts_verification', 'Pending Accounts verification'), ('pending_sanction', 'Pending sanction'), ('approved_for_payment', 'Approved for payment'), ('rejected', 'Rejected'), ('reimbursed', 'Reimbursed')], default='pending_phc_review', max_length=40)),
                ('submitted_at', models.DateTimeField()),
                ('prescription', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='claims', to='phc.prescription')),
            ],
            options={
                'db_table': 'phc_reimbursement_claim',
            },
        ),
        migrations.CreateModel(
            name='ClaimAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_user_id', models.IntegerField()),
                ('event', models.CharField(max_length=20)),
                ('from_status', models.CharField(blank=True, max_length=40)),
                ('to_status', models.CharField(max_length=40)),
                ('note', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('claim', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='actions', to='phc.reimbursementclaim')),
            ],
            options={
                'db_table': 'phc_claim_action',
                'ordering': ('created_at', 'id'),
            },
        ),
        migrations.CreateModel(
            name='ReimbursementPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from', models.DateField(unique=True)),
                ('window_days', models.PositiveIntegerField()),
                ('includes_last_day', models.BooleanField()),
                ('created_by_user_id', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'phc_reimbursement_policy',
                'constraints': [models.CheckConstraint(condition=models.Q(('window_days__gt', 0)), name='phc_policy_window_positive')],
            },
        ),
        migrations.CreateModel(
            name='Requisition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('originator_user_id', models.IntegerField()),
                ('purpose', models.CharField(max_length=500)),
                ('status', models.CharField(choices=[('pending_approval', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('fulfilled', 'Fulfilled')], default='pending_approval', max_length=24)),
                ('decided_by_user_id', models.IntegerField(blank=True, null=True)),
                ('decision_note', models.CharField(blank=True, max_length=500)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('fulfilled_by_user_id', models.IntegerField(blank=True, null=True)),
                ('fulfilled_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'phc_requisition',
                'constraints': [models.CheckConstraint(condition=models.Q(('status', 'pending_approval'), ('decided_at__isnull', False), _connector='OR'), name='phc_requisition_decided_has_time'), models.CheckConstraint(condition=models.Q(models.Q(('status', 'fulfilled'), _negated=True), ('fulfilled_at__isnull', False), _connector='OR'), name='phc_requisition_fulfilled_has_time')],
            },
        ),
        migrations.CreateModel(
            name='RequisitionLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=12)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='requisition_lines', to='phc.inventoryitem')),
                ('requisition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='phc.requisition')),
            ],
            options={
                'db_table': 'phc_requisition_line',
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='ScheduleSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.PositiveSmallIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slots', to='phc.doctorschedule')),
            ],
            options={
                'db_table': 'phc_schedule_slot',
                'ordering': ('day_of_week', 'start_time'),
            },
        ),
        migrations.CreateModel(
            name='StockAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delta', models.DecimalField(decimal_places=2, max_digits=12)),
                ('level_after', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reason', models.CharField(blank=True, max_length=300)),
                ('adjusted_by_user_id', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='adjustments', to='phc.inventoryitem')),
            ],
            options={
                'db_table': 'phc_stock_adjustment',
            },
        ),
        migrations.CreateModel(
            name='LowStockAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.DecimalField(decimal_places=2, max_digits=12)),
                ('threshold', models.DecimalField(decimal_places=2, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='alerts', to='phc.inventoryitem')),
                ('adjustment', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='alert', to='phc.stockadjustment')),
            ],
            options={
                'db_table': 'phc_low_stock_alert',
            },
        ),
        migrations.CreateModel(
            name='DoctorAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('attendance_date', models.DateField()),
                ('status', models.CharField(choices=[('available', 'Available'), ('departed', 'Departed')], max_length=12)),
                ('updated_by_user_id', models.IntegerField()),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance', to='phc.doctorschedule')),
            ],
            options={
                'db_table': 'phc_doctor_attendance',
                'indexes': [models.Index(fields=['attendance_date', 'schedule'], name='phc_attendance_day_idx')],
                'constraints': [models.UniqueConstraint(fields=('schedule', 'attendance_date'), name='phc_attendance_once_per_day')],
            },
        ),
        migrations.AddIndex(
            model_name='reimbursementclaim',
            index=models.Index(fields=['user_id', '-submitted_at'], name='phc_claim_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='reimbursementclaim',
            index=models.Index(fields=['status', '-submitted_at'], name='phc_claim_queue_idx'),
        ),
        migrations.AddConstraint(
            model_name='reimbursementclaim',
            constraint=models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='phc_claim_amount_positive'),
        ),
        migrations.AddIndex(
            model_name='claimaction',
            index=models.Index(fields=['claim', 'created_at'], name='phc_claim_action_idx'),
        ),
        migrations.AddConstraint(
            model_name='requisitionline',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gt', 0)), name='phc_line_quantity_positive'),
        ),
        migrations.AddConstraint(
            model_name='requisitionline',
            constraint=models.UniqueConstraint(fields=('requisition', 'item'), name='phc_line_item_once'),
        ),
        migrations.AddConstraint(
            model_name='scheduleslot',
            constraint=models.CheckConstraint(condition=models.Q(('end_time__gt', models.F('start_time'))), name='phc_slot_end_after_start'),
        ),
        migrations.AddConstraint(
            model_name='scheduleslot',
            constraint=models.CheckConstraint(condition=models.Q(('day_of_week__lte', 6)), name='phc_slot_day_in_week'),
        ),
        migrations.AddConstraint(
            model_name='scheduleslot',
            constraint=models.UniqueConstraint(fields=('schedule', 'day_of_week', 'start_time'), name='phc_slot_unique_start'),
        ),
        migrations.AddIndex(
            model_name='stockadjustment',
            index=models.Index(fields=['created_at'], name='phc_adjustment_time_idx'),
        ),
        migrations.AddConstraint(
            model_name='stockadjustment',
            constraint=models.CheckConstraint(condition=models.Q(('delta', 0), _negated=True), name='phc_adjustment_nonzero'),
        ),
        migrations.AddIndex(
            model_name='lowstockalert',
            index=models.Index(fields=['-created_at'], name='phc_alert_recent_idx'),
        ),
        migrations.AddConstraint(
            model_name='lowstockalert',
            constraint=models.CheckConstraint(condition=models.Q(('level__lt', models.F('threshold'))), name='phc_alert_only_below_threshold'),
        ),
    ]
