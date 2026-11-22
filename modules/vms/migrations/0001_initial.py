# Migration for VMS initial models

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AccessPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version', models.PositiveIntegerField(unique=True)),
                ('visiting_hours_start', models.TimeField(default='08:00')),
                ('visiting_hours_end', models.TimeField(default='20:00')),
                ('max_duration_hours', models.PositiveIntegerField(default=12)),
                ('is_published', models.BooleanField(db_index=True, default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('policy_notes', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-version'],
            },
        ),
        migrations.CreateModel(
            name='HostPreAuthorization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('host_id', models.PositiveIntegerField(db_index=True)),
                ('visitor_email', models.EmailField(db_index=True, max_length=254)),
                ('visitor_name', models.CharField(max_length=150)),
                ('valid_from', models.DateField(db_index=True)),
                ('valid_to', models.DateField(db_index=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Pass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pass_number', models.CharField(db_index=True, max_length=64, unique=True)),
                ('qr_token', models.CharField(db_index=True, max_length=128, unique=True)),
                ('pass_type', models.CharField(choices=[('PRE_REGISTERED', 'Pre-registered'), ('WALK_IN', 'Walk-in'), ('VIP', 'VIP'), ('CONTRACTOR', 'Contractor'), ('EVENT', 'Event Attendee')], default='PRE_REGISTERED', max_length=30)),
                ('valid_from', models.DateTimeField(db_index=True)),
                ('valid_to', models.DateTimeField(db_index=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('USED', 'Used'), ('EXPIRED', 'Expired'), ('REVOKED', 'Revoked')], db_index=True, default='ACTIVE', max_length=20)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BlacklistEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(db_index=True, max_length=150)),
                ('id_document_type', models.CharField(max_length=30)),
                ('id_document_number', models.CharField(db_index=True, max_length=100)),
                ('phone', models.CharField(blank=True, db_index=True, max_length=20)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('ACTIVE', 'Active Blacklist'), ('SAFE_LISTED', 'Temporarily Safe-Listed'), ('INACTIVE', 'Inactive')], db_index=True, default='ACTIVE', max_length=20)),
                ('safe_list_until', models.DateTimeField(blank=True, null=True)),
                ('safe_list_reason', models.TextField(blank=True)),
                ('safe_listed_by_id', models.PositiveIntegerField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['status', 'id_document_number'], name='vms_blackli_status_fba202_idx'), models.Index(fields=['status', 'phone'], name='vms_blackli_status_cea136_idx')],
            },
        ),
        migrations.CreateModel(
            name='GateCheckLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('gate_name', models.CharField(max_length=100)),
                ('checkpoint_type', models.CharField(choices=[('ENTRY', 'Entry Gate'), ('EXIT', 'Exit Gate'), ('ZONE_CHECK', 'Zone Checkpoint')], default='ENTRY', max_length=20)),
                ('action', models.CharField(choices=[('CHECK_IN', 'Check In'), ('CHECK_OUT', 'Check Out'), ('DENIED', 'Access Denied'), ('OVERRIDE', 'Manual Override')], max_length=20)),
                ('operator_id', models.PositiveIntegerField(blank=True, null=True)),
                ('is_override', models.BooleanField(default=False)),
                ('override_reason', models.TextField(blank=True)),
                ('is_offline_sync', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(db_index=True)),
                ('pass_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='check_logs', to='vms.pass')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='Visitor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=150)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('phone', models.CharField(db_index=True, max_length=20)),
                ('organization', models.CharField(blank=True, max_length=150)),
                ('id_document_type', models.CharField(choices=[('AADHAAR', 'Aadhaar Card'), ('PAN', 'PAN Card'), ('PASSPORT', 'Passport'), ('VOTER_ID', 'Voter ID'), ('DRIVING_LICENSE', 'Driving License'), ('INSTITUTE_ID', 'Institute ID'), ('OTHER', 'Other Government ID')], default='AADHAAR', max_length=30)),
                ('id_document_number', models.CharField(db_index=True, max_length=100)),
                ('is_vip', models.BooleanField(default=False)),
                ('vip_reason', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['email', 'phone'], name='vms_visitor_email_610be7_idx'), models.Index(fields=['id_document_type', 'id_document_number'], name='vms_visitor_id_docu_31152e_idx')],
            },
        ),
        migrations.CreateModel(
            name='VisitRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('host_id', models.PositiveIntegerField(db_index=True)),
                ('host_name', models.CharField(blank=True, max_length=150)),
                ('purpose', models.CharField(max_length=255)),
                ('scheduled_start', models.DateTimeField(db_index=True)),
                ('scheduled_end', models.DateTimeField(db_index=True)),
                ('actual_check_in', models.DateTimeField(blank=True, null=True)),
                ('actual_check_out', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING_APPROVAL', 'Pending Host Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('EXPIRED', 'Expired'), ('CANCELLED', 'Cancelled'), ('CHECKED_IN', 'Checked In'), ('CHECKED_OUT', 'Checked Out'), ('AUTO_CHECKED_OUT', 'Auto Checked Out'), ('TERMINATED_EARLY', 'Terminated Early')], db_index=True, default='PENDING_APPROVAL', max_length=32)),
                ('pass_type', models.CharField(choices=[('PRE_REGISTERED', 'Pre-registered'), ('WALK_IN', 'Walk-in'), ('VIP', 'VIP'), ('CONTRACTOR', 'Contractor'), ('EVENT', 'Event Attendee')], default='PRE_REGISTERED', max_length=30)),
                ('access_zones', models.JSONField(blank=True, default=list)),
                ('admin_notes', models.TextField(blank=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('is_urgent_exception', models.BooleanField(default=False)),
                ('extension_hours', models.PositiveIntegerField(default=0)),
                ('external_event_ref', models.CharField(blank=True, max_length=100)),
                ('visitor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='visit_requests', to='vms.visitor')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='pass',
            name='visit_request',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='digital_pass', to='vms.visitrequest'),
        ),
        migrations.CreateModel(
            name='ZoneElevation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('zone_name', models.CharField(max_length=100)),
                ('valid_from', models.DateTimeField(db_index=True)),
                ('valid_to', models.DateTimeField(db_index=True)),
                ('elevated_by_id', models.PositiveIntegerField()),
                ('reason', models.TextField()),
                ('pass_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='zone_elevations', to='vms.pass')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EmergencyMusterRoster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('muster_id', models.CharField(db_index=True, max_length=64)),
                ('assembly_point', models.CharField(max_length=100)),
                ('initiated_by_id', models.PositiveIntegerField()),
                ('initiated_at', models.DateTimeField(db_index=True)),
                ('check_in_time', models.DateTimeField()),
                ('accountability_status', models.CharField(choices=[('UNACCOUNTED', 'Unaccounted'), ('ACCOUNTED', 'Accounted')], db_index=True, default='UNACCOUNTED', max_length=20)),
                ('accounted_at', models.DateTimeField(blank=True, null=True)),
                ('accounted_by_id', models.PositiveIntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('pass_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='emergency_rosters', to='vms.pass')),
                ('visitor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='emergency_rosters', to='vms.visitor')),
            ],
            options={
                'ordering': ['-initiated_at', 'accountability_status'],
                'indexes': [models.Index(fields=['muster_id', 'accountability_status'], name='vms_emergen_muster__742914_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='visitrequest',
            index=models.Index(fields=['host_id', 'status'], name='vms_visitre_host_id_210a58_idx'),
        ),
        migrations.AddIndex(
            model_name='visitrequest',
            index=models.Index(fields=['scheduled_start', 'scheduled_end'], name='vms_visitre_schedul_8de7e3_idx'),
        ),
    ]
