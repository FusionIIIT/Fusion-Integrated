from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='LeaveBalance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('leave_type', models.ForeignKey(on_delete=models.CASCADE, to='elm.leavetype')),
                ('balance', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='LeaveApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('leave_type', models.ForeignKey(on_delete=models.CASCADE, to='elm.leavetype')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='LeaveSubstitute',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('leave_application', models.ForeignKey(on_delete=models.CASCADE, to='elm.leaveapplication')),
                ('substitute_user_id', models.IntegerField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='LeaveApproval',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('leave_application', models.ForeignKey(on_delete=models.CASCADE, to='elm.leaveapplication')),
                ('approver_user_id', models.IntegerField()),
                ('approved', models.BooleanField()),
            ],
        ),
    ]
