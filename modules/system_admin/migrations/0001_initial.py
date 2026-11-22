"""Initial migrations for system_admin module."""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AdminSessionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('session_key', models.CharField(max_length=64, unique=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('terminated_at', models.DateTimeField(blank=True, null=True)),
                ('termination_reason', models.CharField(blank=True, max_length=64)),
            ],
            options={
                'db_table': 'system_admin_session_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ArchivedUserRecord',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(primary_key=True, serialize=False)),
                ('institute_id', models.CharField(db_index=True, max_length=32)),
                ('username', models.CharField(db_index=True, max_length=64)),
                ('email', models.EmailField(max_length=254)),
                ('user_type', models.CharField(max_length=16)),
                ('reason', models.TextField()),
                ('retention_option', models.CharField(choices=[('standard_7yr', 'Standard 7 Years'), ('permanent_audit', 'Permanent Audit Record')], default='standard_7yr', max_length=32)),
                ('archived_by', models.IntegerField()),
                ('archived_at', models.DateTimeField(db_index=True)),
                ('reversible_until', models.DateTimeField(db_index=True)),
                ('is_permanent', models.BooleanField(db_index=True, default=False)),
                ('snapshot', models.JSONField(default=dict)),
            ],
            options={
                'db_table': 'system_admin_archived_user',
                'ordering': ['-archived_at'],
            },
        ),
        migrations.CreateModel(
            name='FailedLoginLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=64)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('reason', models.CharField(blank=True, max_length=120)),
            ],
            options={
                'db_table': 'system_admin_failed_login_log',
                'ordering': ['-attempted_at'],
            },
        ),
        migrations.CreateModel(
            name='HistoricalDatasetArchive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(db_index=True, max_length=64)),
                ('description', models.TextField()),
                ('date_range_start', models.DateField()),
                ('date_range_end', models.DateField()),
                ('record_count', models.PositiveIntegerField(default=0)),
                ('backup_reference', models.CharField(max_length=255)),
                ('archived_by', models.IntegerField()),
                ('is_restored', models.BooleanField(default=False)),
                ('restored_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'system_admin_dataset_archive',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SystemAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_id', models.IntegerField(db_index=True)),
                ('action', models.CharField(db_index=True, max_length=80)),
                ('target_id', models.CharField(blank=True, db_index=True, max_length=64)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('result', models.CharField(choices=[('success', 'Success'), ('failure', 'Failure')], default='success', max_length=16)),
                ('context', models.JSONField(default=dict)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'system_admin_audit_log',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='SystemParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('key', models.CharField(db_index=True, max_length=64, unique=True)),
                ('label', models.CharField(max_length=120)),
                ('value', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('updated_by', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'system_admin_parameter',
                'ordering': ['key'],
            },
        ),
        migrations.CreateModel(
            name='PermanentPurgeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('dataset_identifier', models.CharField(db_index=True, max_length=128)),
                ('requested_by', models.IntegerField()),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('retention_verified', models.BooleanField(default=True)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending_it_head', 'Pending IT Head Authorization'), ('approved', 'Approved by IT Head'), ('rejected', 'Rejected by IT Head'), ('purged', 'Permanently Purged')], db_index=True, default='pending_it_head', max_length=32)),
                ('it_head_user_id', models.IntegerField(blank=True, null=True)),
                ('it_head_decided_at', models.DateTimeField(blank=True, null=True)),
                ('it_head_remarks', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'system_admin_purge_request',
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('status__in', ['pending_it_head', 'approved', 'rejected', 'purged'])), name='chk_sa_purge_status')],
            },
        ),
        migrations.CreateModel(
            name='RoleAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role_code', models.CharField(db_index=True, max_length=64)),
                ('role_name', models.CharField(blank=True, max_length=120)),
                ('user_id', models.IntegerField(db_index=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('active', 'Active'), ('expired', 'Expired'), ('revoked', 'Revoked')], db_index=True, default='active', max_length=24)),
                ('is_singular', models.BooleanField(default=False)),
                ('start_date', models.DateField(db_index=True)),
                ('end_date', models.DateField(blank=True, db_index=True, null=True)),
                ('scope', models.CharField(blank=True, max_length=80)),
                ('reason', models.TextField()),
                ('assigned_by', models.IntegerField()),
            ],
            options={
                'db_table': 'system_admin_role_assignment',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user_id', 'status'], name='idx_sa_user_role_status'), models.Index(fields=['role_code', 'status'], name='idx_sa_role_code_status')],
                'constraints': [models.CheckConstraint(condition=models.Q(('end_date__isnull', True), ('end_date__gte', models.F('start_date')), _connector='OR'), name='chk_sa_role_dates'), models.CheckConstraint(condition=models.Q(('status__in', ['scheduled', 'active', 'expired', 'revoked'])), name='chk_sa_role_status')],
            },
        ),
        migrations.CreateModel(
            name='UserAccount',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(primary_key=True, serialize=False)),
                ('institute_id', models.CharField(db_index=True, max_length=32, unique=True)),
                ('username', models.CharField(db_index=True, max_length=64, unique=True)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('user_type', models.CharField(choices=[('student', 'Student'), ('faculty', 'Faculty'), ('staff', 'Staff')], db_index=True, max_length=16)),
                ('name', models.CharField(blank=True, max_length=150)),
                ('contact_number', models.CharField(blank=True, max_length=32)),
                ('department', models.CharField(blank=True, max_length=80)),
                ('programme', models.CharField(blank=True, max_length=40)),
                ('discipline', models.CharField(blank=True, max_length=40)),
                ('batch_year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('deactivated', 'Deactivated'), ('archived', 'Archived')], db_index=True, default='active', max_length=24)),
                ('deactivated_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'system_admin_user_account',
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('user_type__in', ['student', 'faculty', 'staff'])), name='chk_sa_user_type'), models.CheckConstraint(condition=models.Q(('status__in', ['active', 'deactivated', 'archived'])), name='chk_sa_user_status')],
            },
        ),
    ]
