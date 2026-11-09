from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("mms", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="menuentry",
            constraint=models.UniqueConstraint(
                fields=("week", "day", "meal"),
                name="mms_menu_week_day_meal_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="menuentry",
            constraint=models.CheckConstraint(
                condition=Q(day__gte=0, day__lte=6),
                name="mms_menu_entry_day_valid",
            ),
        ),
    ]
