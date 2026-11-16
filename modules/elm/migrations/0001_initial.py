# Eligible by: Django 5.2.16 initial migration for ELM module

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=16, unique=True)),
                ('label', models.CharField(max_length=80)),
                ('entitlement_days', models.PositiveSmallIntegerField(
                    help_text="Default annual entitlement per employee",
                    default=0)),
                ('carry_forward', models.BooleanField(
                    default=False,
                    help_text="Whether unused days carry to the next year")),
                ('continuous_counting', models.BooleanField(
                    default=True,
                    help_text="Whether intervening weekends/holidays count as leave days")),
            ],
            options={
                'db_table': 'elm_leave_category',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='EmployeeLeaveBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('leave_category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='balances',
                    to='elm.leavecategory')),
                ('remaining_days', models.DecimalField(
                    max_digits=5, decimal_places=2,
                    help_text="Days still available (may be fractional)")),
                ('used_days', models.DecimalField(
                    max_digits=5, decimal_places=2,
                    help_text="Days consumed so far this year")),
            ],
            options={
                'db_table': 'elm_employee_leave_balance',
                'unique_together': [['user_id', 'leave_category']],
                'ordering': ['user_id', 'leave_category'],
            },
        ),
        migrations.CreateModel(
            name='LeaveApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('status', models.CharField(
                    max_length=32,
                    choices=[
                        ('submitted', 'Submitted'),
                        ('unit_head_review', 'Unit Head Review'),
                        ('recommended', 'Recommended'),
                        ('not_recommended', 'Not Recommended'),
                        ('establishment_review', 'Establishment Review'),
                        ('sanctioned', 'Sanctioned'),
                        ('rejected', 'Rejected'),
                        ('withdrawn', 'Withdrawn'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='submitted')),
                ('leave_category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='applications',
                    to='elm.leavecategory')),
                ('requested_start', models.DateField()),
                ('requested_end', models.DateField()),
                ('halftype', models.CharField(
                    max_length=8, blank=True)),
                ('purpose', models.TextField()),
                ('station_leave', models.BooleanField(
                    default=False,
                    help_text="Whether employee will be outside Jabalpur")),
                ('substitute_nominated', models.IntegerField(
                    null=True, blank=True,
                    help_text="user_id of nominated substitute, if applicable")),
                ('substitute_accepted', models.BooleanField(
                    default=False,
                    help_text="Whether the nominated substitute has accepted")),
            ],
            options={
                'db_table': 'elm_leave_application',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LeaveApplicationTransition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_status', models.CharField(max_length=32)),
                ('to_status', models.CharField(max_length=32)),
                ('actor_user_id', models.IntegerField(blank=True, null=True)),
                ('actor_label', models.CharField(max_length=80, blank=True)),
                ('reason', models.CharField(max_length=300, blank=True)),
                ('at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transitions',
                    to='elm.leaveapplication')),
            ],
            options={
                'db_table': 'elm_leave_application_transition',
                'indexes': [
                    models.Index(fields=['application', 'at'], name='transition_app_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='SubstituteNomination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('substitute_user_id', models.IntegerField()),
                ('nominated_by_user_id', models.IntegerField()),
                ('accepted', models.BooleanField(default=False)),
                ('accepted_at', models.DateTimeField(null=True, blank=True)),
                ('reason', models.CharField(max_length=300, blank=True)),
                ('application', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='substitute_nominations',
                    to='elm.leaveapplication')),
            ],
            options={
                'db_table': 'elm_substitute_nomination',
                'unique_together': [['application', 'substitute_user_id']],
            },
        ),
    ]