from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # No dependencies for this initial migration
    ]

    operations = [
        migrations.CreateModel(
            name='HolidayCalendar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('description', models.CharField(max_length=255, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='VacationPeriod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('description', models.CharField(max_length=255, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='LeavePolicyConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_name', models.CharField(max_length=100)),
                ('max_days_allowed', models.IntegerField()),
                ('carry_over_days', models.IntegerField()),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='LeaveNotificationOutbox',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=20)),
                ('leave_type', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='LeaveApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=20)),
                ('leave_type', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(max_length=50)),
                ('reason', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='LeaveBalance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=20)),
                ('leave_type', models.CharField(max_length=100)),
                ('balance_days', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='LeaveLedgerEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=20)),
                ('leave_type', models.CharField(max_length=100)),
                ('transaction_date', models.DateField()),
                ('days_transacted', models.IntegerField()),
                ('balance_before', models.IntegerField()),
                ('balance_after', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='SubstituteRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=20)),
                ('substitute_id', models.CharField(max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='LeaveActionHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leave_id', models.IntegerField()),
                ('action_date', models.DateTimeField(auto_now_add=True)),
                ('action_type', models.CharField(max_length=50)),
                ('details', models.TextField(blank=True)),
            ],
        ),
    ]