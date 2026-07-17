"""
Signals for the orders app.

order_created        — fired explicitly from OrderListCreateView after creation.
order_status_changed — detected via pre_save comparison of old vs new status.

Background threads are used so HTTP responses are not blocked by Telegram API calls.
"""
import logging
import threading

from django.db import models
from django.db.models.signals import Signal, pre_save, post_save
from django.dispatch import receiver

from .models import Order

logger = logging.getLogger(__name__)

# Custom signal fired explicitly in views.py after a new order is created
order_created = Signal()


# ─── Track pre-save status for change detection ───────────────────────────────

@receiver(pre_save, sender=Order)
def capture_old_status(sender, instance, **kwargs):
    """Store the current DB status on the instance before saving."""
    if instance.pk:
        try:
            instance._old_status = Order.objects.values_list('status', flat=True).get(pk=instance.pk)
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# ─── post_save: detect status change ─────────────────────────────────────────

@receiver(post_save, sender=Order)
def handle_order_post_save(sender, instance, created, **kwargs):
    if created:
        return  # handled by the explicit order_created signal
    old = getattr(instance, '_old_status', None)
    if old is not None and old != instance.status:
        logger.debug('Order #%s status changed %s → %s', instance.pk, old, instance.status)
        _fire_in_thread(_notify_status_change, instance.pk, instance.status)


# ─── order_created listener ───────────────────────────────────────────────────

@receiver(order_created, sender=Order)
def handle_order_created(sender, order, **kwargs):
    """Dispatch Telegram notifications asynchronously."""
    _fire_in_thread(_notify_new_order, order.pk)


# ─── Thread helpers ───────────────────────────────────────────────────────────

def _fire_in_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()


def _notify_new_order(order_pk: int):
    try:
        import asyncio
        from bot.notifications import notify_new_order
        asyncio.run(notify_new_order(order_pk))
    except Exception as exc:
        logger.exception('order_created notification failed for order #%s: %s', order_pk, exc)


def _notify_status_change(order_pk: int, new_status: str):
    try:
        import asyncio
        from bot.notifications import notify_status_change
        asyncio.run(notify_status_change(order_pk, new_status))
    except Exception as exc:
        logger.exception(
            'status_change notification failed for order #%s (→%s): %s',
            order_pk, new_status, exc,
        )
