# Hand-authored (Django/manage.py could not run in this environment — see
# UNRESOLVED.md). Mirrors modules/elm/models.py field-for-field.

from django.db import migrations, models


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
                ('applicant_user_id', models.IntegerField(db_index=True)),
                ('category', models.CharField(choices=[('CL', 'Casual Leave'), ('RH', 'Restricted Holiday'), ('SCL', 'Special Casual Leave'), ('EL', 'Earned Leave'), ('COL', 'Commuted Leave'), ('VL', 'Vacation Leave')], max_length=3)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('half_day', models.CharField(choices=[('none', 'Full day'), ('first_half', 'First half'), ('second_half', 'Second half')], default='none', max_length=16)),
                ('station_leave', models.BooleanField(default=False)),
                ('station_leave_details', models.CharField(blank=True, max_length=255)),
                ('reason', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('unit_head_recommended', 'Unit Head: Recommended'), ('unit_head_not_recommended', 'Unit Head: Not Recommended'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'), ('cancelled', 'Cancelled')], db_index=True, default='pending', max_length=32)),
                ('unit_head_user_id', models.IntegerField()),
                ('unit_head_decided_at', models.DateTimeField(blank=True, null=True)),
                ('unit_head_remarks', models.TextField(blank=True)),
                ('substitute_user_id', models.IntegerField(blank=True, null=True)),
                ('substitute_consent', models.CharField(choices=[('not_required', 'Not required'), ('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='not_required', max_length=16)),
                ('withdrawn_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'elm_leave_request',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='leaverequest',
            index=models.Index(fields=['applicant_user_id', 'status'], name='elm_leave_r_applica_557027_idx'),
        ),
        migrations.AddIndex(
            model_name='leaverequest',
            index=models.Index(fields=['unit_head_user_id', 'status'], name='elm_leave_r_unit_he_f1638f_idx'),
        ),
    ]
