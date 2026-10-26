from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverequest',
            name='is_station_leave',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='station_address',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='station_contact',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='substitute_id',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='rejection_reason',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='leaverequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('withdrawn', 'Withdrawn'),
                    ('cancelled', 'Cancelled'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
