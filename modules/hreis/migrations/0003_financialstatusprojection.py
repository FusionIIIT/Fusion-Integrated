import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hreis', '0002_immutable_records'),
    ]

    operations = [
        migrations.CreateModel(
            name='FinancialStatusProjection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_key', models.CharField(max_length=180, unique=True)),
                ('source_system', models.CharField(choices=[('finance', 'Finance'), ('payroll', 'Payroll')], max_length=16)),
                ('external_status_reference', models.CharField(max_length=250)),
                ('financial_review_reference', models.CharField(max_length=250)),
                ('payment_status', models.CharField(choices=[('processing', 'Processing'), ('payment_pending', 'Payment pending'), ('paid', 'Paid'), ('failed', 'Failed')], max_length=20)),
                ('attested_by_user_id', models.IntegerField()),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('claim', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='status_history', to='hreis.claimdetail')),
            ],
            options={
                'db_table': 'hreis_financial_status',
                'indexes': [models.Index(fields=['claim', 'recorded_at'], name='hr_finance_history_idx')],
            },
        ),
    ]
