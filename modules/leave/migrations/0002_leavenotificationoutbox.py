from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leave", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="LeaveNotificationOutbox",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recipient_user_id", models.IntegerField(db_index=True)),
                ("topic", models.CharField(max_length=50)),
                ("dedupe_key", models.CharField(max_length=180, unique=True)),
                ("subject", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"), ("failed", "Failed")], db_index=True, default="pending", max_length=12)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, max_length=300)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "leave_notification_outbox", "ordering": ["created_at"]},
        ),
    ]
