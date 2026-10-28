# Align the database field definitions with the current model and ELM baseline.
from django.db import migrations, models


LEAVE_CHOICES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="leaveapplication",
            name="leave_category",
            field=models.CharField(choices=LEAVE_CHOICES, max_length=3),
        ),
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("canceled", "Canceled"),
                    ("extended", "Extended"),
                ], default="pending", max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="leavecategory",
            name="name",
            field=models.CharField(choices=LEAVE_CHOICES, max_length=3, unique=True),
        ),
    ]
