"""Recoverable Finance validation issues."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("iaa", "0002_supporting_documents")]
    operations = [
        migrations.CreateModel(
            name="IaaProcessingIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("record_type", models.CharField(choices=[("expense", "Expense/voucher"), ("ta", "Travel claim")], max_length=12)),
                ("record_id", models.PositiveBigIntegerField(db_index=True)),
                ("operation", models.CharField(max_length=60)),
                ("reason", models.CharField(max_length=300)),
                ("status", models.CharField(choices=[("open", "Open"), ("resolved", "Resolved")], db_index=True, default="open", max_length=12)),
                ("reported_by_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("resolved_by_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "iaa_processing_issue"},
        ),
        migrations.AddIndex(
            model_name="iaaprocessingissue",
            index=models.Index(fields=["status", "created_at"], name="iaa_issue_status_idx"),
        ),
    ]
