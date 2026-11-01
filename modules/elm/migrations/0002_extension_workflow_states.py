from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("awaiting_substitute", "Awaiting Substitute Response"),
                    ("substitute_declined", "Substitute Declined"),
                    ("awaiting_unit_head", "Awaiting Unit Head Review"),
                    ("awaiting_director_self_sanction", "Awaiting Director Self-Sanction"),
                    ("awaiting_establishment", "Awaiting Establishment Verification"),
                    ("awaiting_final_sanction", "Awaiting Final Sanction Decision"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                    ("cancellation_pending_unit_head", "Cancellation Pending - Unit Head Review"),
                    ("cancellation_pending_establishment", "Cancellation Pending - Establishment"),
                    ("cancellation_pending_final", "Cancellation Pending - Final Decision"),
                    ("cancelled", "Cancelled"),
                    ("extension_pending_substitute", "Extension Pending - Substitute"),
                    ("extension_applicant_action_required", "Extension Applicant Action Required"),
                    ("extension_pending_unit_head", "Extension Pending - Unit Head"),
                    ("extension_pending_establishment", "Extension Pending - Establishment"),
                    ("extension_pending_final", "Extension Pending - Final Decision"),
                    ("extended", "Extended"),
                    ("resumption_pending", "Resumption Review Pending"),
                    ("resumed", "Resumed"),
                ],
                db_index=True,
                default="draft",
                max_length=40,
            ),
        ),
    ]
