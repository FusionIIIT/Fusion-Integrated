from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                    ("withdrawn", "Withdrawn"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="half_day_period",
            field=models.CharField(
                choices=[("none", "Full Day"), ("first_half", "First Half"), ("second_half", "Second Half")],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="substitute_user_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="substitute_status",
            field=models.CharField(
                choices=[
                    ("none", "Not Required"),
                    ("pending", "Pending Consent"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="recommendation",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("recommended", "Recommended"),
                    ("not_recommended", "Not Recommended"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="recommended_by_user_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["substitute_user_id", "substitute_status"], name="leave_req_sub_idx"),
        ),
    ]
