import modules.elm.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("PENDING_SUBSTITUTE", "Pending Substitute Acceptance"),
                    ("APPLICANT_ACTION_REQUIRED", "Applicant Action Required"),
                    ("PENDING_UNIT_HEAD", "Pending Unit Head Recommendation"),
                    ("PENDING_AUTHORITY", "Pending Sanctioning Authority"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                    ("WITHDRAWN", "Withdrawn by Applicant"),
                    ("CANCELLED", "Cancelled"),
                ],
                db_index=True,
                default="DRAFT",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="leavebalance",
            name="year",
            field=models.PositiveSmallIntegerField(
                default=modules.elm.models.current_leave_year,
            ),
        ),
    ]
