from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leave", "0003_fractional_el_balances")]

    operations = [
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("substitute_pending", "Pending Substitute Consent"),
                    ("applicant_action_required", "Applicant Action Required"),
                    ("under_review", "Under Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                    ("cancel_requested", "Cancellation Requested"),
                    ("cancelled", "Cancelled"),
                    ("extension_requested", "Extension Requested"),
                    ("resumption_submitted", "Resumption Submitted"),
                    ("closed", "Closed"),
                ],
                default="substitute_pending",
                max_length=30,
            ),
        ),
    ]
