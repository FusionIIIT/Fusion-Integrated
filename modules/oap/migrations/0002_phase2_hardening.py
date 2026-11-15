from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oap', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OAPAuditTrail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('procedure_type', models.CharField(max_length=50)),
                ('record_id', models.IntegerField()),
                ('action', models.CharField(max_length=100)),
                ('actor_user_id', models.IntegerField()),
                ('actor_role', models.CharField(max_length=100)),
                ('previous_state', models.CharField(blank=True, max_length=50, null=True)),
                ('new_state', models.CharField(max_length=50)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='studentleave',
            name='chargeable_days',
            field=models.DecimalField(decimal_places=1, default=Decimal('1.0'), max_digits=5),
        ),
        migrations.AddField(
            model_name='studentleave',
            name='medical_certificate_attached',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='bonafiderequest',
            name='verification_hash',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='bonafiderequest',
            name='valid_until',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bonafiderequest',
            name='is_expired',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='noduesrequest',
            name='all_domains_cleared',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='noduesrequest',
            name='verification_hash',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='noduesauthorityclearance',
            name='fine_details',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='noduesauthorityclearance',
            name='receipt_reference',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='thesissupervisorassignment',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='taassignment',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='assistantshipclaim',
            name='attendance_percentage',
            field=models.DecimalField(decimal_places=2, default=Decimal('100.00'), max_digits=5),
        ),
        migrations.AddField(
            model_name='assistantshipclaim',
            name='pro_rata_stipend',
            field=models.DecimalField(decimal_places=2, default=Decimal('12400.00'), max_digits=10),
        ),
        migrations.AddField(
            model_name='assistantshipclaim',
            name='funding_source',
            field=models.CharField(default='INSTITUTE_MHRD', max_length=50),
        ),
        migrations.AddField(
            model_name='assistantshipclaim',
            name='thesis_supervisor_role_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='assistantshipclaim',
            name='ta_supervisor_role_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='graduateseminarrequest',
            name='evaluation_result',
            field=models.CharField(blank=True, choices=[('SATISFACTORY', 'Satisfactory'), ('UNSATISFACTORY', 'Unsatisfactory')], max_length=30, null=True),
        ),
    ]
