from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='EmployeeProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(db_index=True, max_length=64, unique=True)),
                ('employee_id', models.CharField(db_index=True, max_length=32, unique=True)),
                ('full_name', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('department', models.CharField(max_length=100)),
                ('designation', models.CharField(max_length=100)),
                ('employment_type', models.CharField(choices=[('Faculty', 'Faculty'), ('Staff', 'Staff'), ('Admin', 'Admin')], default='Faculty', max_length=30)),
                ('date_of_joining', models.DateField()),
                ('date_of_birth', models.DateField()),
                ('retirement_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('Active', 'Active'), ('On_Leave', 'On_Leave'), ('Retired', 'Retired'), ('Suspended', 'Suspended')], default='Active', max_length=30)),
                ('is_hod', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AppraisalCycle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.CharField(max_length=20, unique=True)),
                ('is_open', models.BooleanField(default=True)),
                ('submission_deadline', models.DateField()),
                ('description', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('module', models.CharField(db_index=True, default='hr_eis', max_length=30)),
                ('entity_type', models.CharField(db_index=True, max_length=50)),
                ('entity_id', models.CharField(db_index=True, max_length=50)),
                ('actor', models.CharField(max_length=100)),
                ('action', models.CharField(max_length=100)),
                ('from_state', models.CharField(blank=True, default='', max_length=50)),
                ('to_state', models.CharField(blank=True, default='', max_length=50)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('details', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='NotificationRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.CharField(db_index=True, max_length=100)),
                ('title', models.CharField(max_length=150)),
                ('message', models.TextField()),
                ('category', models.CharField(default='Event', max_length=50)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.TextField()),
                ('updated_by', models.CharField(max_length=100)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='CpdaClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claim_type', models.CharField(choices=[('Advance', 'Advance'), ('Reimbursement', 'Reimbursement')], default='Reimbursement', max_length=30)),
                ('financial_year', models.CharField(max_length=20)),
                ('purpose', models.CharField(max_length=255)),
                ('claimed_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('approved_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('status', models.CharField(choices=[('Submitted', 'Submitted'), ('Verified_HR', 'Verified_HR'), ('Approved_Authority', 'Approved_Authority'), ('Settled_Finance', 'Settled_Finance'), ('Rejected', 'Rejected')], db_index=True, default='Submitted', max_length=30)),
                ('hr_verification', models.CharField(choices=[('Pending', 'Pending'), ('Verified', 'Verified'), ('Flagged', 'Flagged')], default='Pending', max_length=20)),
                ('disbursement_ref', models.CharField(blank=True, default='', max_length=100)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('settled_at', models.DateTimeField(blank=True, null=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cpda_claims', to='hr_eis.employeeprofile')),
            ],
        ),
        migrations.CreateModel(
            name='LtcClaim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('claim_type', models.CharField(choices=[('Advance', 'Advance'), ('Reimbursement', 'Reimbursement')], default='Reimbursement', max_length=30)),
                ('block_year', models.CharField(max_length=20)),
                ('destination', models.CharField(max_length=150)),
                ('travel_mode', models.CharField(default='Air/Train', max_length=50)),
                ('departure_date', models.DateField()),
                ('return_date', models.DateField()),
                ('claimed_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('approved_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('status', models.CharField(choices=[('Submitted', 'Submitted'), ('Verified_HR', 'Verified_HR'), ('Approved_Authority', 'Approved_Authority'), ('Settled_Finance', 'Settled_Finance'), ('Rejected', 'Rejected')], db_index=True, default='Submitted', max_length=30)),
                ('hr_verification', models.CharField(choices=[('Pending', 'Pending'), ('Verified', 'Verified'), ('Flagged', 'Flagged')], default='Pending', max_length=20)),
                ('disbursement_ref', models.CharField(blank=True, default='', max_length=100)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('settled_at', models.DateTimeField(blank=True, null=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ltc_claims', to='hr_eis.employeeprofile')),
            ],
        ),
        migrations.CreateModel(
            name='LeaveRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leave_type', models.CharField(choices=[('Casual', 'Casual'), ('Restricted', 'Restricted'), ('Medical', 'Medical'), ('Earned', 'Earned'), ('Vacation', 'Vacation'), ('Sabbatical', 'Sabbatical')], max_length=50)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('days_requested', models.DecimalField(decimal_places=1, max_digits=5)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('Submitted', 'Submitted'), ('Recommended', 'Recommended'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Cancelled', 'Cancelled')], db_index=True, default='Submitted', max_length=30)),
                ('current_authority', models.CharField(default='HOD', max_length=50)),
                ('remarks', models.TextField(blank=True, default='')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_requests', to='hr_eis.employeeprofile')),
            ],
        ),
        migrations.CreateModel(
            name='LeaveBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leave_type', models.CharField(choices=[('Casual', 'Casual'), ('Restricted', 'Restricted'), ('Medical', 'Medical'), ('Earned', 'Earned'), ('Vacation', 'Vacation'), ('Sabbatical', 'Sabbatical')], max_length=50)),
                ('year', models.IntegerField(default=2026)),
                ('entitled_days', models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ('used_days', models.DecimalField(decimal_places=1, default=0.0, max_digits=5)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_balances', to='hr_eis.employeeprofile')),
            ],
            options={
                'unique_together': {('employee', 'leave_type', 'year')},
            },
        ),
        migrations.CreateModel(
            name='AppraisalRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('self_assessment', models.TextField()),
                ('reviewer_comments', models.TextField(blank=True, default='')),
                ('hod_remarks', models.TextField(blank=True, default='')),
                ('director_remarks', models.TextField(blank=True, default='')),
                ('overall_rating', models.CharField(blank=True, default='', max_length=50)),
                ('status', models.CharField(choices=[('Draft', 'Draft'), ('Submitted', 'Submitted'), ('Under_Review', 'Under_Review'), ('Finalized', 'Finalized'), ('Archived', 'Archived')], db_index=True, default='Draft', max_length=30)),
                ('is_immutable', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('finalized_at', models.DateTimeField(blank=True, null=True)),
                ('assigned_reviewer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_appraisals', to='hr_eis.employeeprofile')),
                ('cycle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='hr_eis.appraisalcycle')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appraisals', to='hr_eis.employeeprofile')),
            ],
            options={
                'unique_together': {('employee', 'cycle')},
            },
        ),
    ]
