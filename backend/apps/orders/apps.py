"""AppConfig for orders — connects signals on ready()."""
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = 'Buyurtmalar'

    def ready(self):
        import apps.orders.signals  # noqa: F401 — register signal receivers
