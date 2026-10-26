from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("elm", "0002_guard_balance_and_request_invariants")]

    operations = [
        migrations.AddField(
            model_name="leaverequest",
            name="applicant_role",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="unit_head_recommendation",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("PENDING_SUBSTITUTE", "Pending Substitute Acceptance"),
                    ("PENDING_UNIT_HEAD", "Pending Unit Head Recommendation"),
                    ("PENDING_AUTHORITY", "Pending Sanctioning Authority"),
                    ("APPLICANT_ACTION_REQUIRED", "Applicant Action Required"),
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
    ]
