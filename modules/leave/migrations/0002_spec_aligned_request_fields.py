from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leave", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="leaverequest",
            name="leave_type",
            field=models.CharField(max_length=3, choices=[
                ("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
                ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
                ("COL", "Commuted Leave"), ("VL", "Vacation Leave"),
            ]),
        ),
        migrations.AddField(
            model_name="leaverequest", name="cl_period",
            field=models.CharField(max_length=12, default="full", choices=[
                ("full", "Full day"), ("first_half", "First half"),
                ("second_half", "Second half"),
            ]),
        ),
        migrations.AddField(
            model_name="leaverequest", name="station_leave",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaverequest", name="station_leave_details",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="leaverequest", name="status",
            field=models.CharField(max_length=12, default="pending", choices=[
                ("pending", "Pending"), ("approved", "Approved"),
                ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
                ("cancelled", "Cancelled"),
            ]),
        ),
    ]
