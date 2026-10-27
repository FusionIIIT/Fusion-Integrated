from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("leave", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("approved", "Approved"),
                         ("withdrawn", "Withdrawn")],
                default="pending", max_length=12,
            ),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(
                condition=Q(("cl_half__in", ["full", "first", "second"])),
                name="leave_request_valid_half_day",
            ),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(
                condition=Q(("station_leave", False)) | ~Q(("station_leave_details", "")),
                name="leave_request_station_details_required",
            ),
        ),
    ]
