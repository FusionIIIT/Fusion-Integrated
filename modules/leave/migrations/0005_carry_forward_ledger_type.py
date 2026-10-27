"""Add an explicit year-end carry-forward ledger event type."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leave", "0004_resumption_review_outcome")]

    operations = [
        migrations.AlterField(
            model_name="leaveledgerentry",
            name="entry_type",
            field=models.CharField(
                choices=[
                    ("credit", "Annual Credit"),
                    ("debit", "Leave Availment"),
                    ("reversal", "Cancellation Reversal"),
                    ("conversion", "VL to EL Conversion"),
                    ("carry_forward", "Year-End Carry-Forward"),
                    ("lapse", "Year-End Lapse"),
                    ("adjustment", "Resumption Adjustment"),
                ],
                max_length=20,
            ),
        ),
    ]
