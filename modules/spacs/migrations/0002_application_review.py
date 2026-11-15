import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spacs", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApplicationReview",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("reviewer_user_id", models.IntegerField()),
                ("findings", models.JSONField(blank=True, default=dict)),
                ("at", models.DateTimeField(auto_now_add=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="spacs.application",
                    ),
                ),
            ],
            options={
                "db_table": "spacs_application_review",
                "ordering": ["at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="applicationreview",
            index=models.Index(
                fields=["application", "at"],
                name="spacs_review_application_idx",
            ),
        ),
        migrations.AddField(
            model_name="notificationoutbox",
            name="subject",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="notificationoutbox",
            name="body",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="notificationoutbox",
            name="attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificationoutbox",
            name="last_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="notificationoutbox",
            name="claimed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationoutbox",
            name="read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="notificationoutbox",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("sending", "Sending"),
                    ("sent", "Sent"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=12,
            ),
        ),
    ]
