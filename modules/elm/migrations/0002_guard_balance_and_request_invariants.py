import decimal

from django.db import migrations, models
from django.db.models import Q

import modules.elm.models


class Migration(migrations.Migration):
    dependencies = [("elm", "0001_initial")]

    operations = [
        migrations.AlterUniqueTogether(
            name="leavebalance",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="leavebalance",
            name="year",
            field=models.PositiveSmallIntegerField(default=modules.elm.models.current_leave_year),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(
                fields=("user_id", "leave_type", "year"),
                name="elm_balance_user_type_year_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.CheckConstraint(
                condition=Q(credited__gte=0) & Q(availed__gte=0) & Q(pending__gte=0),
                name="elm_balance_values_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.CheckConstraint(
                condition=Q(availed__lte=models.F("credited") - models.F("pending")),
                name="elm_balance_usage_within_credit",
            ),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(
                condition=Q(duration_days__gt=0),
                name="elm_leave_duration_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="leaverequest",
            constraint=models.CheckConstraint(
                condition=(
                    Q(is_half_day=False)
                    | (Q(duration_days=decimal.Decimal("0.5")) & Q(start_date=models.F("end_date")))
                ),
                name="elm_half_day_single_day_half_duration",
            ),
        ),
    ]
