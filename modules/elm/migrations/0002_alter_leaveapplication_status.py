from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaveapplication",
            name="original_application_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("AWAITING_SUB", "Awaiting substitute"),
                    ("ACTION_REQUIRED", "Action required"),
                    ("PENDING", "Pending"),
                    ("RECOMMENDED", "Under higher sanction"),
                    ("APPROVED", "Approved"),
                    ("AWAITING_CANCEL", "Awaiting cancellation"),
                    ("AWAITING_RESUMPTION", "Awaiting resumption review"),
                    ("REJECTED", "Rejected"),
                    ("WITHDRAWN", "Withdrawn"),
                    ("CANCELLED", "Cancelled"),
                    ("COMPLETED", "Completed"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
