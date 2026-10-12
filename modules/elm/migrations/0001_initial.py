from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_user_profile_fields'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='EmployeeLeave',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(on_delete=models.CASCADE, to='auth.User')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='LeaveRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('employee', models.ForeignKey(on_delete=models.CASCADE, to='modules.elm.EmployeeLeave')),
                ('leave_type', models.ForeignKey(on_delete=models.CASCADE, to='modules.elm.LeaveType')),
                ('request_date', models.DateField(auto_now_add=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to='auth.User')),
            ],
        ),
        migrations.CreateModel(
            name='LeaveApproval',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('leave_request', models.ForeignKey(on_delete=models.CASCADE, to='modules.elm.LeaveRequest')),
                ('approved_by', models.ForeignKey(on_delete=models.CASCADE, to='auth.User')),
                ('approval_date', models.DateField(auto_now_add=True)),
            ],
        ),
    ]