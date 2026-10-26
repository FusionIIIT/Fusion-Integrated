"""Add half-day and calculated duration fields to ELM applications."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="leaveapplication",
            name="start_half",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="end_half",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="requested_days",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]
