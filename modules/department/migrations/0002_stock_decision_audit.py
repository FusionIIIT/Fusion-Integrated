from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('department', '0001_initial_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockrequest',
            name='decided_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='stockrequest',
            name='decided_by_id',
            field=models.PositiveIntegerField(null=True),
        ),
    ]
