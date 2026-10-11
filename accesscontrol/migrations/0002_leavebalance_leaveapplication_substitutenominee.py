from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accesscontrol', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveBalance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, max_digits=10)),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to='fusion_auth.User')),
                ('leave_type', models.ForeignKey(on_delete=models.CASCADE, to='accesscontrol.LeaveType')),
            ],
            options={
                'db_table': 'accesscontrol_leave_balance',
                'unique_together': {('user', 'leave_type')},
                'ordering': ['user', 'leave_type'],
            },
        ),
        migrations.CreateModel(
            name='LeaveApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=16)),
                ('reason', models.TextField()),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to='fusion_auth.User')),
                ('leave_type', models.ForeignKey(on_delete=models.CASCADE, to='accesscontrol.LeaveType')),
            ],
            options={
                'db_table': 'accesscontrol_leave_application',
                'ordering': ['user', 'start_date'],
            },
        ),
        migrations.CreateModel(
            name='SubstituteNominee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=16)),
                ('leave_application', models.ForeignKey(on_delete=models.CASCADE, to='accesscontrol.LeaveApplication')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to='fusion_auth.User')),
            ],
            options={
                'db_table': 'accesscontrol_substitute_nominee',
                'unique_together': {('leave_application', 'user')},
                'ordering': ['leave_application', 'user'],
            },
        ),
    ]
