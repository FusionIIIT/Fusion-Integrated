from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("iaa", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="dashboardnotification", name="recipient_user_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.CreateModel(
            name="NotificationReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_user_id", models.IntegerField(db_index=True)),
                ("read_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="receipts", to="iaa.dashboardnotification")),
            ],
            options={"db_table": "iaa_notification_receipt"},
        ),
        migrations.AddConstraint(
            model_name="notificationreceipt",
            constraint=models.UniqueConstraint(fields=("notification", "recipient_user_id"), name="iaa_notification_receipt_user_uniq"),
        ),
    ]
