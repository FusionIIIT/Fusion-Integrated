from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('department', '0002_stock_decision_audit'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='oversight_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='feedback',
            name='oversight_by_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name='feedback',
            name='oversight_notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
