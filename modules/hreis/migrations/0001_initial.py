import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_key', models.CharField(max_length=120, unique=True)),
                ('actor_user_id', models.IntegerField(blank=True, null=True)),
                ('acting_designation', models.CharField(blank=True, max_length=150)),
                ('subject_user_id', models.IntegerField(blank=True, null=True)),
                ('action', models.CharField(max_length=100)),
                ('resource_kind', models.CharField(max_length=70)),
                ('resource_id', models.IntegerField()),
                ('data', models.JSONField(default=dict)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'hreis_audit',
                'indexes': [models.Index(fields=['resource_kind', 'resource_id', 'recorded_at'], name='hr_audit_resource_idx'), models.Index(fields=['subject_user_id', '-recorded_at'], name='hr_audit_subject_idx')],
            },
        ),
        migrations.CreateModel(
            name='EmployeeServiceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('appointment_details', models.JSONField(default=dict)),
                ('department', models.CharField(max_length=120)),
                ('designation_snapshot', models.CharField(max_length=150)),
                ('service_history', models.JSONField(default=list)),
                ('retirement_status', models.CharField(blank=True, max_length=100)),
                ('revision', models.PositiveIntegerField(default=0)),
            ],
            options={
                'db_table': 'hreis_service_record',
                'indexes': [models.Index(fields=['department', 'user_id'], name='hr_service_dept_idx')],
                'constraints': [models.UniqueConstraint(fields=('user_id',), name='hr_service_user_unique')],
            },
        ),
        migrations.CreateModel(
            name='HRPolicyVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('family', models.CharField(max_length=40)),
                ('version', models.PositiveIntegerField()),
                ('effective_from', models.DateTimeField()),
                ('effective_until', models.DateTimeField(blank=True, null=True)),
                ('parameters', models.JSONField()),
                ('approved_by_user_id', models.IntegerField()),
                ('approved_designation', models.CharField(max_length=150)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'hreis_policy_version',
                'indexes': [models.Index(fields=['family', '-effective_from'], name='hr_policy_effective_idx')],
                'constraints': [models.UniqueConstraint(fields=('family', 'version'), name='hr_policy_family_version_unique'), models.CheckConstraint(condition=models.Q(('effective_until__isnull', True), ('effective_until__gt', models.F('effective_from')), _connector='OR'), name='hr_policy_valid_interval')],
            },
        ),
        migrations.CreateModel(
            name='HRRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('family', models.CharField(choices=[('leave', 'Leave'), ('appraisal', 'Appraisal'), ('ltc', 'LTC'), ('cpda', 'CPDA')], max_length=12)),
                ('subtype', models.CharField(blank=True, max_length=40)),
                ('state', models.CharField(max_length=48)),
                ('payload', models.JSONField(default=dict)),
                ('route_step', models.PositiveSmallIntegerField(default=0)),
                ('version', models.PositiveIntegerField(default=0)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('policy_version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='requests', to='hreis.hrpolicyversion')),
            ],
            options={
                'db_table': 'hreis_request',
            },
        ),
        migrations.CreateModel(
            name='ClaimDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claim_type', models.CharField(choices=[('ltc', 'LTC'), ('cpda', 'CPDA')], max_length=4)),
                ('subtype', models.CharField(choices=[('advance', 'Advance'), ('reimbursement', 'Reimbursement')], max_length=16)),
                ('prescribed_form_reference', models.CharField(blank=True, max_length=250)),
                ('purpose', models.TextField(blank=True)),
                ('amount', models.DecimalField(blank=True, decimal_places=6, max_digits=20, null=True)),
                ('hr_verified_by_user_id', models.IntegerField(blank=True, null=True)),
                ('financial_verified_by_user_id', models.IntegerField(blank=True, null=True)),
                ('financial_processing_details', models.JSONField(default=dict)),
                ('request', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='claim', to='hreis.hrrequest')),
            ],
            options={
                'db_table': 'hreis_claim',
            },
        ),
        migrations.CreateModel(
            name='ApprovalRouteStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField()),
                ('designation', models.CharField(max_length=150)),
                ('policy_version_label', models.CharField(max_length=80)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='authority_steps', to='hreis.hrrequest')),
            ],
            options={
                'db_table': 'hreis_approval_step',
                'ordering': ['position'],
            },
        ),
        migrations.CreateModel(
            name='AppraisalDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_key', models.CharField(max_length=80)),
                ('reviewer_user_ids', models.JSONField(default=list)),
                ('submitted_form', models.JSONField(default=dict)),
                ('archive_reference', models.CharField(blank=True, max_length=300)),
                ('finalized_at', models.DateTimeField(blank=True, null=True)),
                ('request', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='appraisal', to='hreis.hrrequest')),
            ],
            options={
                'db_table': 'hreis_appraisal',
            },
        ),
        migrations.CreateModel(
            name='HRRequestTransition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(max_length=48)),
                ('event', models.CharField(max_length=48)),
                ('target', models.CharField(max_length=48)),
                ('actor_user_id', models.IntegerField()),
                ('acting_designation', models.CharField(max_length=150)),
                ('specification', models.CharField(max_length=24)),
                ('step_before', models.PositiveSmallIntegerField()),
                ('step_after', models.PositiveSmallIntegerField()),
                ('idempotency_key', models.CharField(max_length=120, unique=True)),
                ('reason', models.TextField(blank=True)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transitions', to='hreis.hrrequest')),
            ],
            options={
                'db_table': 'hreis_request_transition',
            },
        ),
        migrations.CreateModel(
            name='LeaveLedgerEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('leave_type', models.CharField(max_length=40)),
                ('quantity', models.DecimalField(decimal_places=4, max_digits=18)),
                ('event_key', models.CharField(max_length=120, unique=True)),
                ('actor_user_id', models.IntegerField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('policy_version', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='leave_entries', to='hreis.hrpolicyversion')),
                ('request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='leave_entries', to='hreis.hrrequest')),
                ('reversing', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='reversals', to='hreis.leaveledgerentry')),
            ],
            options={
                'db_table': 'hreis_leave_ledger',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_user_id', models.IntegerField()),
                ('event_key', models.CharField(max_length=120, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='notifications', to='hreis.hrrequest')),
            ],
            options={
                'db_table': 'hreis_notification',
            },
        ),
        migrations.CreateModel(
            name='OutboxEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_key', models.CharField(max_length=120, unique=True)),
                ('event_type', models.CharField(max_length=80)),
                ('payload', models.JSONField(default=dict)),
                ('queued_at', models.DateTimeField(auto_now_add=True)),
                ('dispatched_at', models.DateTimeField(blank=True, null=True)),
                ('attempts', models.PositiveIntegerField(default=0)),
            ],
            options={
                'db_table': 'hreis_outbox',
                'indexes': [models.Index(fields=['dispatched_at', 'queued_at'], name='hr_outbox_pending_idx')],
            },
        ),
        migrations.CreateModel(
            name='ServiceRecordRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('revision_number', models.PositiveIntegerField()),
                ('snapshot', models.JSONField()),
                ('actor_user_id', models.IntegerField()),
                ('actor_designation', models.CharField(max_length=150)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revisions', to='hreis.employeeservicerecord')),
            ],
            options={
                'db_table': 'hreis_service_revision',
            },
        ),
        migrations.CreateModel(
            name='ClaimDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_kind', models.CharField(max_length=80)),
                ('secure_object_reference', models.CharField(max_length=300)),
                ('integrity_digest', models.CharField(max_length=128)),
                ('uploaded_by_user_id', models.IntegerField()),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('claim', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documents', to='hreis.claimdetail')),
            ],
            options={
                'db_table': 'hreis_claim_document',
                'indexes': [models.Index(fields=['claim', 'recorded_at'], name='hr_claim_document_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='hrrequest',
            index=models.Index(fields=['user_id', '-created_at'], name='hr_request_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='hrrequest',
            index=models.Index(fields=['family', 'state', '-created_at'], name='hr_request_queue_idx'),
        ),
        migrations.AddConstraint(
            model_name='hrrequest',
            constraint=models.CheckConstraint(condition=models.Q(('family__in', ['leave', 'appraisal', 'ltc', 'cpda'])), name='hr_request_family_valid'),
        ),
        migrations.AddConstraint(
            model_name='claimdetail',
            constraint=models.CheckConstraint(condition=models.Q(('amount__isnull', True), ('amount__gt', 0), _connector='OR'), name='hr_claim_amount_positive'),
        ),
        migrations.AddIndex(
            model_name='approvalroutestep',
            index=models.Index(fields=['designation', 'request'], name='hr_approval_assigned_idx'),
        ),
        migrations.AddConstraint(
            model_name='approvalroutestep',
            constraint=models.UniqueConstraint(fields=('request', 'position'), name='hr_approval_step_unique'),
        ),
        migrations.AddIndex(
            model_name='appraisaldetail',
            index=models.Index(fields=['period_key'], name='hr_appraisal_period_idx'),
        ),
        migrations.AddIndex(
            model_name='hrrequesttransition',
            index=models.Index(fields=['request', 'recorded_at'], name='hr_transition_history_idx'),
        ),
        migrations.AddIndex(
            model_name='leaveledgerentry',
            index=models.Index(fields=['user_id', 'leave_type', 'recorded_at'], name='hr_leave_balance_idx'),
        ),
        migrations.AddConstraint(
            model_name='leaveledgerentry',
            constraint=models.CheckConstraint(condition=models.Q(('quantity', 0), _negated=True), name='hr_ledger_nonzero'),
        ),
        migrations.AddConstraint(
            model_name='leaveledgerentry',
            constraint=models.UniqueConstraint(condition=models.Q(('reversing__isnull', False)), fields=('reversing',), name='hr_ledger_one_reversal'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient_user_id', '-created_at'], name='hr_notification_recipient_idx'),
        ),
        migrations.AddIndex(
            model_name='servicerecordrevision',
            index=models.Index(fields=['record', 'recorded_at'], name='hr_revision_history_idx'),
        ),
        migrations.AddConstraint(
            model_name='servicerecordrevision',
            constraint=models.UniqueConstraint(fields=('record', 'revision_number'), name='hr_revision_unique'),
        ),
    ]
