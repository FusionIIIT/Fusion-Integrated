from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("elm", "0002_seed_default_leave_policies")]

    operations = [
        migrations.AddConstraint(
            model_name="leaveapplication",
            constraint=models.UniqueConstraint(
                fields=("evidence_reference",),
                condition=Q(("request_type", "offline")),
                name="elm_offline_evidence_uniq",
            ),
        ),
    ]
