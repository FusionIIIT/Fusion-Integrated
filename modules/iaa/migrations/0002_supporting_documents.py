"""Validated Drive document references owned by IAA users."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("iaa", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="IaaSupportingDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.PositiveBigIntegerField(db_index=True)),
                ("kind", models.CharField(choices=[("expense", "Expense/voucher"), ("ta", "Travel claim"), ("observation", "Corrective evidence")], max_length=16)),
                ("title", models.CharField(max_length=160)),
                ("drive_url", models.URLField(max_length=500)),
                ("drive_file_id", models.CharField(max_length=200)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"db_table": "iaa_supporting_document"},
        ),
        migrations.AddConstraint(
            model_name="iaasupportingdocument",
            constraint=models.UniqueConstraint(fields=("user_id", "drive_file_id", "kind"), name="iaa_doc_user_file_kind_uniq"),
        ),
    ]
