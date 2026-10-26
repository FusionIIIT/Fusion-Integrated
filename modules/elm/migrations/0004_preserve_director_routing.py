from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0003_offline_evidence_unique")]

    operations = [
        migrations.AddField(
            model_name="leaveapplication",
            name="director_case",
            field=models.BooleanField(default=False),
        ),
    ]
