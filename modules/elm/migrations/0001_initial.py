from django.db import migrations, models
import django.db.models.deletion


LEAVE_TYPES = [
    ("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"), ("VL", "Vacation Leave"),
]


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="LeaveApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.PositiveBigIntegerField(db_index=True)),
                ("category", models.CharField(choices=LEAVE_TYPES, max_length=3)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("part_of_day", models.CharField(choices=[("full", "Full day"), ("first_half", "First half"), ("second_half", "Second half")], default="full", max_length=12)),
                ("reason", models.TextField()),
                ("station_leave", models.BooleanField(default=False)),
                ("station_destination", models.CharField(blank=True, max_length=200)),
                ("substitute_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn")], default="pending", max_length=16)),
                ("decision_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.PositiveBigIntegerField(db_index=True)),
                ("year", models.PositiveSmallIntegerField()),
                ("category", models.CharField(choices=LEAVE_TYPES, max_length=3)),
                ("entitled_days", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("used_days", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
            ],
            options={"ordering": ["year", "category"], "unique_together": (("user_id", "year", "category"),)},
        ),
        migrations.CreateModel(
            name="LeaveAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_user_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("action", models.CharField(max_length=24)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="elm.leaveapplication")),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
