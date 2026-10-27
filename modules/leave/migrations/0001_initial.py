from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('category', models.CharField(choices=[('CL', 'Casual Leave'), ('RH', 'Restricted Holiday'), ('SCL', 'Special Casual Leave'), ('EL', 'Earned Leave'), ('COL', 'Commuted Leave'), ('VL', 'Vacation Leave')], max_length=8)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('half_day', models.BooleanField(default=False)),
                ('purpose', models.TextField(blank=True)),
                ('station_leave', models.BooleanField(default=False)),
                ('station_details', models.CharField(blank=True, max_length=300)),
                ('substitute_user_id', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('awaiting_substitute', 'Awaiting Substitute'), ('unit_head_queue', 'Unit Head Queue'), ('establishment', 'Establishment'), ('final_decision', 'Final Decision'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'), ('cancelled', 'Cancelled')], default='draft', max_length=24)),
            ],
            options={
                'db_table': 'leave_request',
                'indexes': [models.Index(fields=['user_id', 'status'], name='leave_user_idx'), models.Index(fields=['status'], name='leave_status_idx')],
            },
        ),
        migrations.CreateModel(
            name='LeaveTransition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_status', models.CharField(max_length=24)),
                ('to_status', models.CharField(max_length=24)),
                ('actor_user_id', models.IntegerField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, max_length=300)),
                ('at', models.DateTimeField(auto_now_add=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transitions', to='leave.leaverequest')),
            ],
            options={
                'db_table': 'leave_transition',
                'indexes': [models.Index(fields=['request', 'at'], name='leave_tr_idx')],
            },
        ),
    ]
