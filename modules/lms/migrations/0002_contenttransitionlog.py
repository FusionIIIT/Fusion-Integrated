import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentTransitionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_user_id', models.IntegerField(null=True)),
                ('actor_role', models.CharField(max_length=8)),
                ('event', models.CharField(max_length=8)),
                ('old_state', models.CharField(max_length=10)),
                ('new_state', models.CharField(max_length=10)),
                ('old_release_at', models.DateTimeField(null=True)),
                ('new_release_at', models.DateTimeField(null=True)),
                ('changed_at', models.DateTimeField()),
                ('assignment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='lms.assignment')),
                ('material', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='lms.material')),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('assignment__isnull', True), ('material__isnull', False)), models.Q(('assignment__isnull', False), ('material__isnull', True)), _connector='OR'), name='lms_transition_one_subject')],
            },
        ),
    ]
