import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FinancialRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('kind', models.CharField(choices=[('expense', 'Expense / voucher'), ('ta', 'Travel allowance')], max_length=8)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('query_raised', 'Query Raised'), ('query_responded', 'Query Responded'), ('finance_validated', 'Finance Validated'), ('verified', 'Verified'), ('approval_pending', 'Approval Pending'), ('escalated', 'Escalated'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('recorded', 'Recorded')], max_length=24)),
                ('department', models.CharField(blank=True, max_length=128)),
                ('request_type', models.CharField(blank=True, max_length=64)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('description', models.TextField(blank=True)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('purpose', models.TextField(blank=True)),
                ('trip_start', models.DateField(blank=True, null=True)),
                ('trip_end', models.DateField(blank=True, null=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('route_levels', models.JSONField(blank=True, default=list)),
                ('escalation_designation', models.CharField(blank=True, max_length=64)),
                ('current_level', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('processing_reference', models.CharField(blank=True, max_length=128)),
                ('processing_note', models.TextField(blank=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('processed_by', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='AuditObservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('respondent_user_id', models.IntegerField()),
                ('title', models.CharField(max_length=200)),
                ('detail', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('responded', 'Responded'), ('closed', 'Closed')], default='open', max_length=10)),
                ('cycle', models.PositiveSmallIntegerField(default=1)),
                ('raised_by', models.IntegerField()),
                ('raised_role', models.CharField(max_length=64)),
                ('record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='observations', to='iaa.financialrecord')),
            ],
        ),
        migrations.CreateModel(
            name='ApprovalStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('level', models.PositiveSmallIntegerField()),
                ('designation', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('escalated', 'Escalated'), ('rerouted', 'Rerouted')], default='pending', max_length=12)),
                ('assigned_at', models.DateTimeField()),
                ('via_escalation', models.BooleanField(default=False)),
                ('decided_by', models.IntegerField(blank=True, null=True)),
                ('decided_role', models.CharField(blank=True, max_length=64)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='steps', to='iaa.financialrecord')),
            ],
            options={
                'ordering': ['assigned_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Anomaly',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(choices=[('budget', 'Budget'), ('policy', 'Policy'), ('financial', 'Financial')], max_length=16)),
                ('source', models.CharField(choices=[('manual', 'Manual'), ('automatic', 'Automatic')], max_length=10)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('escalated', 'Escalated'), ('resolved', 'Resolved')], default='open', max_length=10)),
                ('resolver_chain', models.JSONField(default=list)),
                ('resolver_level', models.PositiveSmallIntegerField(default=0)),
                ('assigned_role', models.CharField(max_length=64)),
                ('raised_by', models.IntegerField(blank=True, null=True)),
                ('raised_role', models.CharField(max_length=64)),
                ('resolved_by', models.IntegerField(blank=True, null=True)),
                ('resolved_role', models.CharField(blank=True, max_length=64)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('resolution', models.TextField(blank=True)),
                ('record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='anomalies', to='iaa.financialrecord')),
            ],
        ),
        migrations.CreateModel(
            name='FinancialYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=16, unique=True)),
                ('starts_on', models.DateField()),
                ('ends_on', models.DateField()),
            ],
            options={
                'ordering': ['-starts_on'],
                'indexes': [models.Index(fields=['starts_on', 'ends_on'], name='iaa_fy_span_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('ends_on__gt', models.F('starts_on'))), name='iaa_fy_ends_after_start')],
            },
        ),
        migrations.AddField(
            model_name='financialrecord',
            name='financial_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='records', to='iaa.financialyear'),
        ),
        migrations.CreateModel(
            name='BudgetEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=128)),
                ('kind', models.CharField(choices=[('allocation', 'Allocation'), ('adjustment', 'Adjustment'), ('commitment', 'Commitment')], max_length=16)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_by', models.IntegerField(null=True)),
                ('created_role', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='budget_entries', to='iaa.financialrecord')),
                ('financial_year', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='budget_entries', to='iaa.financialyear')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_user_id', models.IntegerField(blank=True, null=True)),
                ('recipient_role', models.CharField(blank=True, max_length=64)),
                ('kind', models.CharField(max_length=32)),
                ('message', models.CharField(max_length=300)),
                ('entity', models.CharField(max_length=16)),
                ('entity_id', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['recipient_user_id', '-created_at'], name='iaa_notify_user_idx'), models.Index(fields=['recipient_role', '-created_at'], name='iaa_notify_role_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('recipient_user_id__isnull', False), ('recipient_role', '')), models.Q(('recipient_user_id__isnull', True), models.Q(('recipient_role', ''), _negated=True)), _connector='OR'), name='iaa_notification_one_recipient')],
            },
        ),
        migrations.CreateModel(
            name='ObservationResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cycle', models.PositiveSmallIntegerField()),
                ('corrective_action', models.TextField()),
                ('evidence_link', models.URLField(blank=True, max_length=500)),
                ('responded_by', models.IntegerField()),
                ('verdict', models.CharField(choices=[('pending', 'Pending'), ('satisfactory', 'Satisfactory'), ('unsatisfactory', 'Unsatisfactory')], default='pending', max_length=16)),
                ('reviewed_by', models.IntegerField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_remarks', models.TextField(blank=True)),
                ('observation', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='responses', to='iaa.auditobservation')),
            ],
            options={
                'ordering': ['cycle'],
            },
        ),
        migrations.CreateModel(
            name='PolicyVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from', models.DateTimeField()),
                ('approval_timeout_hours', models.PositiveIntegerField()),
                ('ta_high_value_threshold', models.DecimalField(decimal_places=2, max_digits=14)),
                ('budget_check_required', models.BooleanField(default=True)),
                ('request_types', models.JSONField(default=list)),
                ('required_documents', models.JSONField(default=dict)),
                ('routes', models.JSONField(default=list)),
                ('anomaly_resolvers', models.JSONField(default=dict)),
                ('created_by', models.IntegerField()),
                ('created_role', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-effective_from', '-id'],
                'indexes': [models.Index(fields=['-effective_from'], name='iaa_policy_effective_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('approval_timeout_hours__gt', 0)), name='iaa_policy_timeout_positive'), models.CheckConstraint(condition=models.Q(('ta_high_value_threshold__gte', 0)), name='iaa_policy_threshold_nonneg')],
            },
        ),
        migrations.CreateModel(
            name='SupportingDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('link', models.URLField(max_length=500)),
                ('added_by', models.IntegerField()),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documents', to='iaa.financialrecord')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='TrailEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity', models.CharField(choices=[('record', 'Record'), ('anomaly', 'Anomaly'), ('observation', 'Observation'), ('configuration', 'Configuration')], max_length=16)),
                ('entity_id', models.IntegerField()),
                ('action', models.CharField(max_length=32)),
                ('from_status', models.CharField(blank=True, max_length=24)),
                ('to_status', models.CharField(blank=True, max_length=24)),
                ('actor_user_id', models.IntegerField(blank=True, null=True)),
                ('actor_role', models.CharField(max_length=64)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['created_at', 'id'],
                'indexes': [models.Index(fields=['entity', 'entity_id', 'created_at'], name='iaa_trail_entity_idx')],
            },
        ),
        migrations.CreateModel(
            name='ClarificationQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.TextField()),
                ('raised_by', models.IntegerField()),
                ('raised_role', models.CharField(max_length=64)),
                ('response', models.TextField(blank=True)),
                ('responded_by', models.IntegerField(blank=True, null=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='queries', to='iaa.financialrecord')),
            ],
            options={
                'ordering': ['created_at'],
                'indexes': [models.Index(fields=['record', 'created_at'], name='iaa_query_record_idx')],
                'constraints': [models.UniqueConstraint(condition=models.Q(('responded_at__isnull', True)), fields=('record',), name='iaa_query_one_open_per_record')],
            },
        ),
        migrations.AddIndex(
            model_name='auditobservation',
            index=models.Index(fields=['respondent_user_id', 'status'], name='iaa_obs_respondent_idx'),
        ),
        migrations.AddIndex(
            model_name='auditobservation',
            index=models.Index(fields=['status', '-created_at'], name='iaa_obs_status_idx'),
        ),
        migrations.AddConstraint(
            model_name='auditobservation',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ('open', 'responded', 'closed'))), name='iaa_observation_status_known'),
        ),
        migrations.AddIndex(
            model_name='approvalstep',
            index=models.Index(fields=['designation', 'status'], name='iaa_step_queue_idx'),
        ),
        migrations.AddIndex(
            model_name='approvalstep',
            index=models.Index(fields=['status', 'assigned_at'], name='iaa_step_overdue_idx'),
        ),
        migrations.AddConstraint(
            model_name='approvalstep',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('record',), name='iaa_step_one_pending_per_record'),
        ),
        migrations.AddConstraint(
            model_name='approvalstep',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('status__in', ['approved', 'rejected']), _negated=True), models.Q(('remarks', ''), _negated=True), _connector='OR'), name='iaa_step_decision_has_remarks'),
        ),
        migrations.AddIndex(
            model_name='anomaly',
            index=models.Index(fields=['status', '-created_at'], name='iaa_anomaly_status_idx'),
        ),
        migrations.AddIndex(
            model_name='anomaly',
            index=models.Index(fields=['record', 'status'], name='iaa_anomaly_record_idx'),
        ),
        migrations.AddIndex(
            model_name='anomaly',
            index=models.Index(fields=['assigned_role', 'status'], name='iaa_anomaly_assigned_idx'),
        ),
        migrations.AddConstraint(
            model_name='anomaly',
            constraint=models.UniqueConstraint(condition=models.Q(('source', 'automatic'), models.Q(('status', 'resolved'), _negated=True)), fields=('record', 'category'), name='iaa_anomaly_one_live_automatic'),
        ),
        migrations.AddConstraint(
            model_name='anomaly',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ('open', 'escalated', 'resolved'))), name='iaa_anomaly_status_known'),
        ),
        migrations.AddIndex(
            model_name='financialrecord',
            index=models.Index(fields=['user_id', '-created_at'], name='iaa_record_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='financialrecord',
            index=models.Index(fields=['status', '-created_at'], name='iaa_record_status_idx'),
        ),
        migrations.AddIndex(
            model_name='financialrecord',
            index=models.Index(fields=['department', 'status'], name='iaa_record_dept_idx'),
        ),
        migrations.AddConstraint(
            model_name='financialrecord',
            constraint=models.CheckConstraint(condition=models.Q(('amount__isnull', True), ('amount__gt', 0), _connector='OR'), name='iaa_record_amount_positive'),
        ),
        migrations.AddConstraint(
            model_name='financialrecord',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'ta'), _negated=True), models.Q(('trip_end__isnull', False), ('trip_start__isnull', False)), _connector='OR'), name='iaa_record_ta_has_trip_dates'),
        ),
        migrations.AddConstraint(
            model_name='financialrecord',
            constraint=models.CheckConstraint(condition=models.Q(('trip_start__isnull', True), ('trip_end__isnull', True), ('trip_end__gte', models.F('trip_start')), _connector='OR'), name='iaa_record_trip_ordered'),
        ),
        migrations.AddConstraint(
            model_name='financialrecord',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ('draft', 'submitted', 'query_raised', 'query_responded', 'finance_validated', 'verified', 'approval_pending', 'escalated', 'approved', 'rejected', 'recorded'))), name='iaa_record_status_known'),
        ),
        migrations.AddIndex(
            model_name='budgetentry',
            index=models.Index(fields=['financial_year', 'department'], name='iaa_budget_dept_idx'),
        ),
        migrations.AddConstraint(
            model_name='budgetentry',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'commitment'), _negated=True), ('amount__lt', 0), _connector='OR'), name='iaa_budget_commitment_negative'),
        ),
        migrations.AddConstraint(
            model_name='budgetentry',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'allocation'), _negated=True), ('amount__gt', 0), _connector='OR'), name='iaa_budget_allocation_positive'),
        ),
        migrations.AddConstraint(
            model_name='budgetentry',
            constraint=models.UniqueConstraint(condition=models.Q(('kind', 'commitment')), fields=('record',), name='iaa_budget_one_commitment_per_record'),
        ),
        migrations.AddConstraint(
            model_name='observationresponse',
            constraint=models.UniqueConstraint(fields=('observation', 'cycle'), name='iaa_obs_response_one_per_cycle'),
        ),
        migrations.AddIndex(
            model_name='supportingdocument',
            index=models.Index(fields=['record', 'created_at'], name='iaa_doc_record_idx'),
        ),
    ]
