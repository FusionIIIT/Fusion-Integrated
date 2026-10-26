from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LeaveRequest",
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
                ("user_id", models.IntegerField(db_index=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("cl", "Casual Leave"),
                            ("rh", "Restricted Holiday"),
                            ("scl", "Special Casual Leave"),
                            ("el", "Earned Leave"),
                            ("vl", "Faculty Vacation Leave"),
                            ("col", "Commuted Leave"),
                        ],
                        max_length=10,
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("reason", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=10,
                    ),
                ),
                ("substitute_id", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Leave Request",
                "verbose_name_plural": "Leave Requests",
            },
        ),
    ]
