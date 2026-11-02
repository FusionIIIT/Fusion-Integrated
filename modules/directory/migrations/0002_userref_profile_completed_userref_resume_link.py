from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("directory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userref",
            name="profile_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userref",
            name="resume_link",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
