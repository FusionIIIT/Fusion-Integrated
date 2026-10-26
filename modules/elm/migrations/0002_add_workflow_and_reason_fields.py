# Generated for ELM Phase 2 schema updates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="leaveapplication",
            name="reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("AWAITING_SUBSTITUTE", "Awaiting Substitute Consent"),
                    ("AWAITING_APPROVAL", "Awaiting Approval"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                    ("WITHDRAWN", "Withdrawn"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="AWAITING_APPROVAL",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="substitutenomination",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending Consent"),
                    ("ACCEPTED", "Accepted"),
                    ("DECLINED", "Declined"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="substitutenomination",
            name="decline_reason",
            field=models.TextField(blank=True, default=""),
        ),
    ]
