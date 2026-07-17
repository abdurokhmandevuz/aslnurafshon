"""
Bot notification helpers.

notify_new_order(order_pk)   — sends message to customer + admin group
notify_status_change(order_pk, new_status) — sends status update to customer

Duplicate-prevention: tracks sent (order_pk, status) pairs in a simple
in-memory set. For multi-worker deploys use a DB/cache-backed approach,
but for a single Railway service this is sufficient.
"""
import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Sent-notification tracker (simple in-memory dedup) ──────────────────────
_notified: set[tuple] = set()


def _already_sent(order_pk: int, event: str) -> bool:
    key = (order_pk, event)
    if key in _notified:
        return True
    _notified.add(key)
    return False


# ─── Django setup helper ───────────────────────────────────────────────────────

def _ensure_django():
    """Setup Django if not already configured (when called from bot process)."""
    import django
    if not django.conf.settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
        django.setup()


# ─── Main notification functions ─────────────────────────────────────────────

async def notify_new_order(order_pk: int):
    """
    Send:
      1. Customer confirmation message
      2. Admin group message with inline action buttons
    """
    if _already_sent(order_pk, 'new'):
        return

    try:
        _ensure_django()
        from apps.orders.models import Order
        order = Order.objects.select_related('user', 'address').prefetch_related('items').get(pk=order_pk)
    except Exception as exc:
        logger.error('notify_new_order: cannot load order #%s: %s', order_pk, exc)
        return

    bot = _get_bot()
    if bot is None:
        return

    try:
        # 1. Customer notification
        await bot.send_message(
            chat_id=order.user.telegram_id,
            text=_customer_new_order_text(order),
            parse_mode='HTML',
        )
    except Exception as exc:
        logger.warning('Cannot notify customer (order #%s): %s', order_pk, exc)

    try:
        # 2. Admin group notification
        from django.conf import settings
        admin_group = settings.ADMIN_GROUP_ID
        if admin_group:
            from bot.keyboards import order_admin_keyboard
            await bot.send_message(
                chat_id=admin_group,
                text=_admin_new_order_text(order),
                parse_mode='HTML',
                reply_markup=order_admin_keyboard(order_pk),
            )
    except Exception as exc:
        logger.warning('Cannot notify admin group (order #%s): %s', order_pk, exc)

    await bot.session.close()


async def notify_status_change(order_pk: int, new_status: str):
    """Send order status update to the customer."""
    if _already_sent(order_pk, new_status):
        return

    try:
        _ensure_django()
        from apps.orders.models import Order
        order = Order.objects.select_related('user').get(pk=order_pk)
    except Exception as exc:
        logger.error('notify_status_change: cannot load order #%s: %s', order_pk, exc)
        return

    bot = _get_bot()
    if bot is None:
        return

    status_emoji = {
        'yangi': '🆕',
        'tayyorlanmoqda': '👨‍🍳',
        'yolda': '🚴',
        'yetkazildi': '✅',
        'bekor_qilindi': '❌',
    }
    label = dict(order.Status.choices).get(new_status, new_status)
    emoji = status_emoji.get(new_status, 'ℹ️')

    try:
        await bot.send_message(
            chat_id=order.user.telegram_id,
            text=(
                f"{emoji} <b>Buyurtma #{order_pk} holati o'zgardi</b>\n\n"
                f'Yangi holat: <b>{label}</b>'
            ),
            parse_mode='HTML',
        )
    except Exception as exc:
        logger.warning('Cannot send status update (order #%s): %s', order_pk, exc)

    await bot.session.close()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_bot():
    """Create a one-shot Bot instance for sending messages."""
    try:
        from aiogram import Bot
        from django.conf import settings
        token = settings.BOT_TOKEN
        if not token:
            logger.error('BOT_TOKEN is not set')
            return None
        return Bot(token=token)
    except Exception as exc:
        logger.error('Cannot create bot: %s', exc)
        return None


def _customer_new_order_text(order) -> str:
    items_text = '\n'.join(
        f"  • {item.product_name_snapshot} {item.variant_weight_snapshot} × {item.quantity} = {item.line_total:,} so'm"
        for item in order.items.all()
    )
    delivery_label = dict(order.DeliveryType.choices).get(order.delivery_type, order.delivery_type)
    payment_label = dict(order.PaymentMethod.choices).get(order.payment_method, order.payment_method)

    return (
        f'✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n'
        f'📦 Buyurtma: <b>#{order.pk}</b>\n'
        f'🚚 Yetkazish: {delivery_label}\n'
        f"💳 To'lov: {payment_label}\n\n"
        f'<b>Tarkib:</b>\n{items_text}\n\n'
        f"Mahsulotlar: <b>{order.subtotal:,} so'm</b>\n"
        f"Yetkazish: <b>{order.delivery_fee:,} so'm</b>\n"
        f"<b>Jami: {order.total:,} so'm</b>\n\n"
        f"Tez orada siz bilan bog'lanamiz! ☕"
    )


def _admin_new_order_text(order) -> str:
    items_text = '\n'.join(
        f'  • {item.product_name_snapshot} {item.variant_weight_snapshot} × {item.quantity}'
        for item in order.items.all()
    )
    delivery_label = dict(order.DeliveryType.choices).get(order.delivery_type, order.delivery_type)
    payment_label = dict(order.PaymentMethod.choices).get(order.payment_method, order.payment_method)

    address_text = ''
    if order.address:
        address_text = f'\n📍 Manzil: {order.address.address_text}'

    comment_text = f'\n💬 Izoh: {order.comment}' if order.comment else ''

    return (
        f'🆕 <b>YANGI BUYURTMA #{order.pk}</b>\n\n'
        f'👤 Mijoz: <b>{order.user.full_name}</b> (@{order.user.username or "—"})\n'
        f'📱 Telegram ID: <code>{order.user.telegram_id}</code>\n\n'
        f'<b>Mahsulotlar:</b>\n{items_text}\n\n'
        f'🚚 Yetkazish: {delivery_label}{address_text}\n'
        f"💳 To'lov: {payment_label}\n"
        f"💰 Jami: <b>{order.total:,} so'm</b>"
        f'{comment_text}'
    )
