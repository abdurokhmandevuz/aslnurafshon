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
        from django.conf import settings
        if order.payment_method == 'click' and getattr(settings, 'CLICK_PROVIDER_TOKEN', None):
            from aiogram.types import LabeledPrice
            prices = [LabeledPrice(label='Buyurtma summasi', amount=int(order.total * 100))]
            if order.delivery_fee > 0:
                prices.append(LabeledPrice(label='Yetkazib berish', amount=int(order.delivery_fee * 100)))
                
            await bot.send_invoice(
                chat_id=order.user.telegram_id,
                title=f"Buyurtma #{order.id}",
                description="Asl Nurafshon do'konidan xarid",
                payload=f"order_{order.id}",
                provider_token=settings.CLICK_PROVIDER_TOKEN,
                currency="UZS",
                prices=prices,
                start_parameter="pay-order",
            )
        else:
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
            if order.payment_proof:
                from aiogram.types import FSInputFile
                try:
                    await bot.send_photo(
                        chat_id=admin_group,
                        photo=FSInputFile(order.payment_proof.path),
                        caption=_admin_new_order_text(order) + "\n\n📸 <b>To'lov cheki biriktirildi!</b>",
                        parse_mode='HTML',
                        reply_markup=order_admin_keyboard(order_pk),
                    )
                except Exception as photo_err:
                    logger.warning("Could not send photo to admin group: %s", photo_err)
                    await bot.send_message(
                        chat_id=admin_group,
                        text=_admin_new_order_text(order),
                        parse_mode='HTML',
                        reply_markup=order_admin_keyboard(order_pk),
                    )
            else:
                await bot.send_message(
                    chat_id=admin_group,
                    text=_admin_new_order_text(order),
                    parse_mode='HTML',
                    reply_markup=order_admin_keyboard(order_pk),
                )
    except Exception as exc:
        logger.warning('Cannot notify admin group (order #%s): %s', order_pk, exc)

    try:
        from bot.keyboards import order_admin_keyboard
        await _send_admin_direct_messages(
            bot,
            _admin_new_order_text(order),
            reply_markup=order_admin_keyboard(order_pk),
        )
    except Exception as exc:
        logger.warning('Cannot notify admin private chats (order #%s): %s', order_pk, exc)

    try:
        # 3. Notify all active couriers
        from apps.accounts.models import Courier
        couriers = Courier.objects.filter(is_active=True)
        for courier in couriers:
            try:
                await bot.send_message(
                    chat_id=courier.telegram_id,
                    text=f"🚚 <b>YANGI BUYURTMA KELDI! #{order.pk}</b>\n\n" + _admin_new_order_text(order),
                    parse_mode='HTML',
                )
            except Exception as exc:
                logger.warning('Cannot notify courier %s (id: %s): %s', courier.full_name, courier.telegram_id, exc)
    except Exception as exc:
        logger.error('Error fetching/notifying couriers for order #%s: %s', order_pk, exc)

    await bot.session.close()


async def notify_status_change(order_pk: int, new_status: str):
    """Send order status update to the customer."""
    if _already_sent(order_pk, new_status):
        return

    try:
        _ensure_django()
        from apps.orders.models import Order
        order = Order.objects.select_related('user', 'address').prefetch_related('items').get(pk=order_pk)
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
        
        # If order is delivered, generate and send PDF receipt
        if new_status == 'yetkazildi':

            try:
                from apps.orders.utils import generate_receipt_pdf
                from aiogram.types import FSInputFile
                pdf_path = generate_receipt_pdf(order)
                await bot.send_document(
                    chat_id=order.user.telegram_id,
                    document=FSInputFile(pdf_path, filename=f"chek_order_{order.id}.pdf"),
                    caption=f"🧾 Buyurtma #{order_pk} uchun chek."
                )
            except Exception as pdf_exc:
                logger.error('Cannot send PDF receipt for order #%s: %s', order_pk, pdf_exc)
    except Exception as exc:
        logger.warning('Cannot send status update (order #%s): %s', order_pk, exc)

    await bot.session.close()


async def notify_low_stock(variant_id: int):
    """Notify admin group when a product variant's stock falls to 5 or less."""
    if _already_sent(variant_id, 'low_stock'):
        return

    try:
        _ensure_django()
        from apps.catalog.models import ProductVariant
        variant = ProductVariant.objects.select_related('product').get(pk=variant_id)
    except Exception as exc:
        logger.error('notify_low_stock: cannot load variant #%s: %s', variant_id, exc)
        return

    bot = _get_bot()
    if bot is None:
        return

    try:
        from django.conf import settings
        admin_group = settings.ADMIN_GROUP_ID
        if admin_group:
            text = (
                f"⚠️ <b>Ombor ogohlantirishi</b>\n\n"
                f"Mahsulot: <b>{variant.product.name} ({variant.label})</b>\n"
                f"Qoldi: <b>{variant.stock_qty} ta</b>"
            )
            await bot.send_message(
                chat_id=admin_group,
                text=text,
                parse_mode='HTML',
            )
    except Exception as exc:
        logger.warning('Cannot send low stock alert: %s', exc)

    try:
        text = (
            f"<b>Ombor ogohlantirishi</b>\n\n"
            f"Mahsulot: <b>{variant.product.name} ({variant.label})</b>\n"
            f"Qoldi: <b>{variant.stock_qty} ta</b>"
        )
        await _send_admin_direct_messages(bot, text)
    except Exception as exc:
        logger.warning('Cannot notify admin private chats about low stock: %s', exc)

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


async def _send_admin_direct_messages(bot, text: str, reply_markup=None):
    """Send critical notices to every configured admin private chat."""
    from django.conf import settings

    for telegram_id in settings.ADMIN_TELEGRAM_IDS:
        if telegram_id == settings.ADMIN_GROUP_ID:
            continue
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode='HTML',
                reply_markup=reply_markup,
            )
        except Exception as exc:
            logger.warning('Cannot notify admin %s: %s', telegram_id, exc)


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


async def notify_corporate_inquiry(inquiry_id: int):
    """Send corporate/wholesale inquiry alert to admin group."""
    try:
        _ensure_django()
        from apps.orders.models import CorporateInquiry
        inquiry = CorporateInquiry.objects.get(pk=inquiry_id)
    except Exception as exc:
        logger.error('notify_corporate_inquiry: cannot load inquiry #%s: %s', inquiry_id, exc)
        return

    bot = _get_bot()
    if bot is None:
        return

    try:
        from django.conf import settings
        admin_group = settings.ADMIN_GROUP_ID
        if admin_group:
            text = (
                f"🏢 <b>KORPORATIV / ULGURJI SO'ROV #{inquiry.id}</b>\n\n"
                f"🏢 Kompaniya: <b>{inquiry.company_name}</b>\n"
                f"👤 Mas'ul shaxs: <b>{inquiry.contact_person}</b>\n"
                f"📱 Telefon: <code>{inquiry.phone}</code>\n"
                f"📦 Taxminiy hajm: <b>{inquiry.estimated_quantity:,} ta</b>\n"
                f"💬 Izoh/Savollar:\n<i>{inquiry.comment or '—'}</i>"
            )
            await bot.send_message(
                chat_id=admin_group,
                text=text,
                parse_mode='HTML',
            )
    except Exception as exc:
        logger.error('Cannot notify admin group of corporate inquiry #%s: %s', inquiry_id, exc)

    try:
        text = (
            f"<b>KORPORATIV / ULGURJI SO'ROV #{inquiry.id}</b>\n\n"
            f"Kompaniya: <b>{inquiry.company_name}</b>\n"
            f"Mas'ul shaxs: <b>{inquiry.contact_person}</b>\n"
            f"Telefon: <code>{inquiry.phone}</code>\n"
            f"Taxminiy hajm: <b>{inquiry.estimated_quantity:,} ta</b>\n"
            f"Izoh: <i>{inquiry.comment or '-'}</i>"
        )
        await _send_admin_direct_messages(bot, text)
    except Exception as exc:
        logger.warning('Cannot notify admin private chats about corporate inquiry: %s', exc)

    await bot.session.close()


# ─── Broadcast Helpers for Deals & Combos ─────────────────────────────────────

async def broadcast_daily_deal_to_all_users(deal_id: int):
    """Broadcast DailyDeal to all Telegram users."""
    try:
        import os
        _ensure_django()
        from apps.catalog.models import DailyDeal
        from apps.accounts.models import TelegramUser
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

        deal = DailyDeal.objects.select_related('variant', 'variant__product').get(pk=deal_id)
        bot = _get_bot()
        if bot is None:
            return

        users = list(TelegramUser.objects.values_list('telegram_id', flat=True))
        v = deal.variant
        deal_price = deal.deal_price
        fee = deal.delivery_fee
        discount = deal.discount_percent

        caption = (
            f"🔥 <b>KUNLIK MAXSUS TAKLIF!</b> 🔥\n\n"
            f"☕ <b>{v.product.name}</b> ({v.label})\n"
            f"<s>{v.price:,} UZS</s> ➡️ <b>{deal_price:,} UZS</b> (-{discount}%)\n"
            f"🚚 Dastavka: <b>{'Bepul 🎉' if fee == 0 else f'{fee:,} UZS'}</b>\n\n"
            f"⚡️ Shoshiling, mahsulotlar soni cheklangan!"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛒 Savatga qo'shish (Xarid)", callback_data=f"add_deal:{deal.id}")
        ]])

        for u_id in users:
            try:
                if deal.image and os.path.exists(deal.image.path):
                    await bot.send_photo(u_id, FSInputFile(deal.image.path), caption=caption, parse_mode='HTML', reply_markup=markup)
                else:
                    await bot.send_message(u_id, caption, parse_mode='HTML', reply_markup=markup)
            except Exception:
                pass

        await bot.session.close()
    except Exception as exc:
        logger.error('broadcast_daily_deal error: %s', exc)


async def broadcast_bundle_to_all_users(bundle_id: int):
    """Broadcast ProductBundle (Combo) to all Telegram users."""
    try:
        import os
        _ensure_django()
        from apps.catalog.models import ProductBundle
        from apps.accounts.models import TelegramUser
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

        bundle = ProductBundle.objects.prefetch_related('items__variant__product').get(pk=bundle_id)
        bot = _get_bot()
        if bot is None:
            return

        users = list(TelegramUser.objects.values_list('telegram_id', flat=True))
        caption = (
            f"🎁 <b>KOMBO TO'PLAM!</b> 🎁\n\n"
            f"📦 <b>{bundle.name}</b>\n"
            f"<s>{bundle.original_price:,} UZS</s> ➡️ <b>{bundle.price:,} UZS</b> (-{bundle.discount_percent}%)\n\n"
            f"<i>{bundle.description or ''}</i>\n\n"
            f"⚡️ Tejamkor va qulay to'plam!"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛒 Savatga qo'shish (Xarid)", callback_data=f"add_bundle:{bundle.id}")
        ]])

        for u_id in users:
            try:
                if bundle.image and os.path.exists(bundle.image.path):
                    await bot.send_photo(u_id, FSInputFile(bundle.image.path), caption=caption, parse_mode='HTML', reply_markup=markup)
                else:
                    await bot.send_message(u_id, caption, parse_mode='HTML', reply_markup=markup)
            except Exception:
                pass

        await bot.session.close()
    except Exception as exc:
        logger.error('broadcast_bundle error: %s', exc)


def notify_broadcast_async(target_id: int, target_type: str = 'deal'):
    """Helper to run broadcast async task in a separate thread from sync Django code."""
    import threading, asyncio
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if target_type == 'deal':
            loop.run_until_complete(broadcast_daily_deal_to_all_users(target_id))
        elif target_type == 'bundle':
            loop.run_until_complete(broadcast_bundle_to_all_users(target_id))
        loop.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
