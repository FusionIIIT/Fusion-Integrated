# Generated manually for VHMS compliance fixes (AFR-VH-009, AFR-VH-101, AFR-VH-105, BR-VH-045..050)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vh', '0002_booking_assigned_caretaker_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='expected_check_in_time',
            field=models.TimeField(blank=True, help_text='Expected arrival time (AFR-VH-009)', null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='expected_check_out_time',
            field=models.TimeField(blank=True, help_text='Expected departure time (AFR-VH-009)', null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, help_text='Caretaker review timestamp (AFR-VH-101)', null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='approved_at',
            field=models.DateTimeField(blank=True, help_text='In-Charge approval/rejection timestamp (AFR-VH-101)', null=True),
        ),
        migrations.AddField(
            model_name='inventoryreplenishment',
            name='reviewed_by_user_id',
            field=models.IntegerField(blank=True, help_text='In-Charge approver ID (AFR-VH-105)', null=True),
        ),
        migrations.AddField(
            model_name='inventoryreplenishment',
            name='decision_timestamp',
            field=models.DateTimeField(blank=True, help_text='Replenishment approval timestamp (AFR-VH-105)', null=True),
        ),
        migrations.AddConstraint(
            model_name='vhmsuserrole',
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=('role_type',),
                name='unique_active_role_per_type',
            ),
        ),
    ]
