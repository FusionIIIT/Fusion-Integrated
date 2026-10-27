from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leave", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="resumptionrecord",
            name="state",
            field=models.CharField(default="resumption_review_pending", max_length=64),
        ),
    ]
