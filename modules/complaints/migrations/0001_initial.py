import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Complaint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("complainant_user_id", models.IntegerField(db_index=True)),
                ("category", models.CharField(max_length=120)),
                ("description", models.TextField()),
                ("submitted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"db_table": "complaints_complaint", "ordering": ["-submitted_at"]},
        ),
        migrations.CreateModel(
            name="ComplaintAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("content_type", models.CharField(max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("storage_key", models.CharField(blank=True, max_length=500)),
                ("sha256", models.CharField(max_length=64)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="attachments", to="complaints.complaint")),
            ],
            options={"db_table": "complaints_attachment"},
        ),
        migrations.CreateModel(
            name="ComplaintNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recipient_user_id", models.IntegerField(db_index=True)),
                ("recipient_email", models.EmailField(blank=True, max_length=254)),
                ("topic", models.CharField(default="complaint.submitted", max_length=80)),
                ("status", models.CharField(default="pending", max_length=16)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, max_length=300)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications", to="complaints.complaint")),
            ],
            options={"db_table": "complaints_notification"},
        ),
    ]
