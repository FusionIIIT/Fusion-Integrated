from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leave", "0002_leavenotificationoutbox")]
    operations = [
        migrations.AlterField(
            model_name="leavebalance", name="el_balance",
            field=models.DecimalField(decimal_places=2, default=Decimal("30.00"), max_digits=6),
        ),
        migrations.AlterField(
            model_name="leaveledgerentry", name="change_amount",
            field=models.DecimalField(decimal_places=2, max_digits=6),
        ),
        migrations.AlterField(
            model_name="leaveledgerentry", name="balance_after",
            field=models.DecimalField(decimal_places=2, max_digits=6),
        ),
    ]
