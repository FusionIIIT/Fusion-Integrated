from django.apps import AppConfig


class PurchaseStoresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.purchase_stores"
    label = "purchase_stores"
    verbose_name = "Purchase and Stores Management"
