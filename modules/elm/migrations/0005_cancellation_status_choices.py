from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0004_preserve_director_routing")]

    operations = [
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("awaiting_substitute", "Awaiting Substitute"),
                    ("awaiting_unit_head", "Awaiting Unit Head"),
                    ("awaiting_cancellation_unit_head", "Awaiting Cancellation Unit Head"),
                    ("awaiting_establishment", "Awaiting Establishment"),
                    ("awaiting_sanction", "Awaiting Sanction"),
                    ("awaiting_cancellation_sanction", "Awaiting Cancellation Sanction"),
                    ("awaiting_resumption_review", "Awaiting Resumption Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                    ("cancelled", "Cancelled"),
                    ("action_required", "Action Required"),
                ],
                db_index=True,
                default="awaiting_unit_head",
                max_length=36,
            ),
        ),
    ]
